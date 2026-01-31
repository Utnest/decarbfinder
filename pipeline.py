from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

import module1_demand
import module2_supplyGeneration as module2
import module3_storage as module3
import module_5_optimizer as module5


DEFAULT_START_YEAR = 2025
DEFAULT_END_YEAR = 2050
DEFAULT_RESERVE_MARGIN = 0.15


@dataclass(frozen=True)
class PipelineInputs:
    scenario_name: str
    population_multiplier: float = 1.0
    population_growth: float = 0.0
    electrification_uplift: float = 0.0
    reserve_margin: float = DEFAULT_RESERVE_MARGIN
    start_year: int = DEFAULT_START_YEAR
    end_year: int = DEFAULT_END_YEAR
    energy_old: str = "Natural Gas"
    energy_new: str = "Solar"


@dataclass(frozen=True)
class PipelineResults:
    projections: pd.DataFrame
    supply_by_source: pd.DataFrame
    supply_totals: pd.DataFrame
    storage_results: pd.DataFrame
    optimizer_results: pd.DataFrame
    metadata: Dict[str, float | int | str]


def _energy_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _build_sources_with_preferences(energy_old: str, energy_new: str) -> List[module2.GenerationSource]:
    sources = module2.build_default_sources()
    sources_by_name = {source.name: source for source in sources}

    old_map = {
        "natural_gas": "natural_gas",
        "coal": "natural_gas",
        "fossil_fuels": "natural_gas",
    }
    new_map = {
        "solar": "solar",
        "wind": "wind",
        "hydro": "hydro",
    }

    old_key = old_map.get(_energy_key(energy_old))
    new_key = new_map.get(_energy_key(energy_new))

    if new_key == "hydro" and "hydro" not in sources_by_name:
        sources_by_name["hydro"] = module2.GenerationSource(
            name="hydro",
            capacity_mw=1500.0,
            capacity_factor=0.5,
            capex_per_mw=1600000.0,
            opex_per_mwh=9.0,
            emissions_t_per_mwh=0.005,
            lifetime_years=50,
        )

    if old_key in sources_by_name:
        old_source = sources_by_name[old_key]
        shift = 0.2 * old_source.capacity_mw
        sources_by_name[old_key] = module2.GenerationSource(
            name=old_source.name,
            capacity_mw=max(old_source.capacity_mw - shift, 0.0),
            capacity_factor=old_source.capacity_factor,
            capex_per_mw=old_source.capex_per_mw,
            opex_per_mwh=old_source.opex_per_mwh,
            emissions_t_per_mwh=old_source.emissions_t_per_mwh,
            lifetime_years=old_source.lifetime_years,
        )

        if new_key in sources_by_name:
            new_source = sources_by_name[new_key]
            sources_by_name[new_key] = module2.GenerationSource(
                name=new_source.name,
                capacity_mw=new_source.capacity_mw + shift,
                capacity_factor=new_source.capacity_factor,
                capex_per_mw=new_source.capex_per_mw,
                opex_per_mwh=new_source.opex_per_mwh,
                emissions_t_per_mwh=new_source.emissions_t_per_mwh,
                lifetime_years=new_source.lifetime_years,
            )

    ordered_names = [source.name for source in sources]
    if "hydro" in sources_by_name and "hydro" not in ordered_names:
        ordered_names.append("hydro")
    return [sources_by_name[name] for name in ordered_names if name in sources_by_name]


def _summaries_and_profiles(base_dir: Path) -> tuple[dict[int, module1_demand.DemandSummary], dict[int, list[float]]]:
    return module1_demand.load_demand_directory(base_dir)


def _build_projection_dataframe(
    projections: Dict[int, float], scenario_name: str
) -> pd.DataFrame:
    return (
        pd.DataFrame(
            {
                "year": list(projections.keys()),
                "scenario": [scenario_name] * len(projections),
                "annual_demand_mwh": list(projections.values()),
            }
        )
        .sort_values("year")
        .reset_index(drop=True)
    )


def run_pipeline(base_dir: str | Path, inputs: PipelineInputs) -> PipelineResults:
    base_dir = Path(base_dir)
    data_dir = base_dir / "data"
    summaries, _ = _summaries_and_profiles(base_dir)
    cagr = module1_demand.compute_cagr(summaries)
    latest_year = max(summaries)
    latest_summary = summaries[latest_year]

    projections = module1_demand.project_annual_demand(
        base_year=latest_year,
        base_total_mwh=latest_summary.total_mwh,
        start_year=max(inputs.start_year, latest_year),
        end_year=inputs.end_year,
        base_growth_rate=cagr,
        population_growth=inputs.population_growth,
        electrification_uplift=inputs.electrification_uplift,
        scenario_multiplier=inputs.population_multiplier,
    )

    projection_path = data_dir / "module2_demand_projections.csv"
    module1_demand.export_projections_csv(
        projections, projection_path, scenario_name=inputs.scenario_name
    )
    demand_df = _build_projection_dataframe(projections, inputs.scenario_name)

    sources = _build_sources_with_preferences(inputs.energy_old, inputs.energy_new)
    per_source_df, per_year_df = module2.simulate_supply_mix(
        demand_df, sources, reserve_margin=inputs.reserve_margin
    )
    supply_outputs_path = data_dir / "module2_supply_outputs.csv"
    per_source_df.to_csv(supply_outputs_path, index=False)
    supply_totals_path = data_dir / "module2_supply_totals.csv"
    per_year_df.to_csv(supply_totals_path, index=False)

    storage_results = module3.dispatch_storage(per_year_df, module3.default_storage_params())
    storage_results = module3.compute_reliability(
        storage_results, reserve_margin_target=inputs.reserve_margin
    )
    storage_output_path = data_dir / "module3_storage_outputs.csv"
    module3.save_outputs(
        storage_results[
            [
                "year",
                "scenario",
                "annual_demand_mwh",
                "energy_generated_mwh",
                "storage_delivered_mwh",
                "unmet_demand_mwh",
                "reserve_margin",
                "reliability_pass",
            ]
        ],
        storage_output_path,
    )

    optimizer_output_path = data_dir / "module5_optimizer_outputs.csv"
    optimizer_results = module5.run_optimizer(
        supply_totals_path,
        storage_output_path,
        optimizer_output_path,
        reliability=module5.ReliabilityConfig(
            mode="penalty",
            require_reliability_pass=False,
        ),
    )

    metadata = {
        "base_year": latest_year,
        "base_total_mwh": latest_summary.total_mwh,
        "cagr": cagr,
        "scenario_name": inputs.scenario_name,
    }

    return PipelineResults(
        projections=demand_df,
        supply_by_source=per_source_df,
        supply_totals=per_year_df,
        storage_results=storage_results,
        optimizer_results=optimizer_results,
        metadata=metadata,
    )
