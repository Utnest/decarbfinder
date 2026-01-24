from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd


@dataclass(frozen=True)
class GenerationSource:
    name: str
    capacity_mw: float
    capacity_factor: float
    capex_per_mw: float
    opex_per_mwh: float
    emissions_t_per_mwh: float
    lifetime_years: int


def build_default_sources() -> List[GenerationSource]:
    # Placeholder values; tune as project assumptions solidify.
    return [
        GenerationSource(
            name="natural_gas",
            capacity_mw=5000.0,
            capacity_factor=0.55,
            capex_per_mw=1100000.0,
            opex_per_mwh=45.0,
            emissions_t_per_mwh=0.45,
            lifetime_years=30,
        ),
        GenerationSource(
            name="solar",
            capacity_mw=3000.0,
            capacity_factor=0.22,
            capex_per_mw=900000.0,
            opex_per_mwh=12.0,
            emissions_t_per_mwh=0.02,
            lifetime_years=25,
        ),
        GenerationSource(
            name="wind",
            capacity_mw=3500.0,
            capacity_factor=0.35,
            capex_per_mw=1300000.0,
            opex_per_mwh=15.0,
            emissions_t_per_mwh=0.015,
            lifetime_years=25,
        ),
        GenerationSource(
            name="battery",
            capacity_mw=1000.0,
            capacity_factor=0.15,
            capex_per_mw=600000.0,
            opex_per_mwh=8.0,
            emissions_t_per_mwh=0.0,
            lifetime_years=15,
        ),
    ]


def load_demand_projections(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    df = pd.read_csv(path)
    expected = {"year", "scenario", "annual_demand_mwh"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {sorted(missing)}")
    return df


def compute_required_firm_capacity(
    demand_df: pd.DataFrame, reserve_margin: float
) -> Dict[int, float]:
    if reserve_margin < 0:
        raise ValueError("reserve_margin must be >= 0")
    required: Dict[int, float] = {}
    for _, row in demand_df.iterrows():
        annual_mwh = float(row["annual_demand_mwh"])
        year = int(row["year"])
        average_mw = annual_mwh / 8760.0
        required[year] = average_mw * (1.0 + reserve_margin)
    return required

def annual_energy_capacity(source: GenerationSource) -> float:
    return source.capacity_mw * source.capacity_factor * 8760.0

def annualized_capex(source: GenerationSource) -> float:
    return source.capex_per_mw * source.capacity_mw / source.lifetime_years


def total_annual_cost(
    source: GenerationSource, annual_energy_mwh: float | None = None
) -> float:
    if annual_energy_mwh is None:
        annual_energy_mwh = annual_energy_capacity(source)
    annualized_capex = source.capex_per_mw * source.capacity_mw / source.lifetime_years
    opex = source.opex_per_mwh * annual_energy_mwh
    return annualized_capex + opex


def _build_growth_weights(sources: Iterable[GenerationSource]) -> Dict[str, float]:
    capacities = {source.name: source.capacity_mw for source in sources}
    total_capacity = sum(capacities.values())
    if total_capacity <= 0:
        equal = 1.0 / max(len(capacities), 1)
        return {name: equal for name in capacities}
    return {name: capacity / total_capacity for name, capacity in capacities.items()}


def _dispatch_order(sources: Iterable[GenerationSource]) -> List[GenerationSource]:
    return sorted(
        sources,
        key=lambda source: (source.opex_per_mwh, source.emissions_t_per_mwh),
    )


def _init_vintages(
    sources: Iterable[GenerationSource], start_year: int
) -> Dict[str, List[Tuple[int, float]]]:
    vintages: Dict[str, List[Tuple[int, float]]] = {}
    for source in sources:
        vintages[source.name] = [(start_year, source.capacity_mw)]
    return vintages


def _retire_capacity(
    vintages: Dict[str, List[Tuple[int, float]]],
    sources_by_name: Dict[str, GenerationSource],
    year: int,
) -> Dict[str, float]:
    retired: Dict[str, float] = {}
    for name, entries in vintages.items():
        lifetime = sources_by_name[name].lifetime_years
        remaining: List[Tuple[int, float]] = []
        retired_capacity = 0.0
        for install_year, capacity in entries:
            if year - install_year >= lifetime:
                retired_capacity += capacity
            else:
                remaining.append((install_year, capacity))
        vintages[name] = remaining
        retired[name] = retired_capacity
    return retired


def _current_capacity(vintages: Dict[str, List[Tuple[int, float]]]) -> Dict[str, float]:
    return {name: sum(capacity for _, capacity in entries) for name, entries in vintages.items()}


def simulate_supply_mix(
    demand_df: pd.DataFrame,
    sources: List[GenerationSource],
    reserve_margin: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if demand_df.empty:
        raise ValueError("demand_df must not be empty")
    if reserve_margin < 0:
        raise ValueError("reserve_margin must be >= 0")

    per_source_rows: List[Dict[str, float | str | int]] = []
    per_year_rows: List[Dict[str, float | str | int]] = []

    base_sources = {source.name: source for source in sources}
    growth_weights = _build_growth_weights(sources)

    for scenario, scenario_df in demand_df.groupby("scenario"):
        scenario_df = scenario_df.sort_values("year")
        start_year = int(scenario_df.iloc[0]["year"])
        vintages = _init_vintages(sources, start_year)
        current_capacities = _current_capacity(vintages)

        for _, row in scenario_df.iterrows():
            year = int(row["year"])
            annual_demand_mwh = float(row["annual_demand_mwh"])
            retired_capacity = _retire_capacity(vintages, base_sources, year)
            current_capacities = _current_capacity(vintages)
            required_capacity_mw = (annual_demand_mwh / 8760.0) * (1.0 + reserve_margin)
            total_capacity_mw = sum(current_capacities.values())
            capacity_added = {name: 0.0 for name in base_sources}
            if required_capacity_mw > total_capacity_mw:
                growth_needed = required_capacity_mw - total_capacity_mw
                for name, weight in growth_weights.items():
                    added = growth_needed * weight
                    capacity_added[name] = added
                    vintages[name].append((year, added))
                total_capacity_mw = sum(current_capacities.values())
                current_capacities = _current_capacity(vintages)

            updated_sources: List[GenerationSource] = []
            for name, base in base_sources.items():
                updated_sources.append(
                    GenerationSource(
                        name=base.name,
                        capacity_mw=current_capacities[name],
                        capacity_factor=base.capacity_factor,
                        capex_per_mw=base.capex_per_mw,
                        opex_per_mwh=base.opex_per_mwh,
                        emissions_t_per_mwh=base.emissions_t_per_mwh,
                        lifetime_years=base.lifetime_years,
                    )
                )

            remaining_demand = annual_demand_mwh
            dispatch_sources = _dispatch_order(updated_sources)
            year_energy_total = 0.0
            year_cost_total = 0.0
            year_emissions_total = 0.0

            for source in dispatch_sources:
                potential_mwh = annual_energy_capacity(source)
                generated_mwh = min(potential_mwh, remaining_demand)
                remaining_demand -= generated_mwh
                capex = annualized_capex(source)
                opex = generated_mwh * source.opex_per_mwh
                total_cost = capex + opex
                emissions = generated_mwh * source.emissions_t_per_mwh

                per_source_rows.append(
                    {
                        "year": year,
                        "scenario": scenario,
                        "source": source.name,
                        "capacity_mw": round(source.capacity_mw, 3),
                        "capacity_added_mw": round(capacity_added.get(source.name, 0.0), 3),
                        "capacity_retired_mw": round(retired_capacity.get(source.name, 0.0), 3),
                        "capacity_factor": source.capacity_factor,
                        "energy_generated_mwh": round(generated_mwh, 3),
                        "annualized_capex": round(capex, 2),
                        "opex": round(opex, 2),
                        "total_cost": round(total_cost, 2),
                        "emissions_t": round(emissions, 3),
                    }
                )

                year_energy_total += generated_mwh
                year_cost_total += total_cost
                year_emissions_total += emissions

            per_year_rows.append(
                {
                    "year": year,
                    "scenario": scenario,
                    "annual_demand_mwh": round(annual_demand_mwh, 3),
                    "energy_generated_mwh": round(year_energy_total, 3),
                    "unmet_demand_mwh": round(max(remaining_demand, 0.0), 3),
                    "required_firm_capacity_mw": round(required_capacity_mw, 3),
                    "total_capacity_mw": round(total_capacity_mw, 3),
                    "total_cost": round(year_cost_total, 2),
                    "total_emissions_t": round(year_emissions_total, 3),
                }
            )

    per_source_df = pd.DataFrame(per_source_rows)
    per_year_df = pd.DataFrame(per_year_rows)
    return per_source_df, per_year_df

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    sources = build_default_sources()
    demand = load_demand_projections(base_dir / "module2_demand_projections.csv")
    per_source_df, per_year_df = simulate_supply_mix(demand, sources, reserve_margin=0.15)

    output_path = base_dir / "module2_supply_outputs.csv"
    per_source_df.to_csv(output_path, index=False)
    totals_path = base_dir / "module2_supply_totals.csv"
    per_year_df.to_csv(totals_path, index=False)

    print("Loaded sources:", [source.name for source in sources])
    print("Per-year totals (sample):")
    print(per_year_df.head(5).to_string(index=False))
    print(f"Wrote per-source breakdown to {output_path}")
    print(f"Wrote per-year totals to {totals_path}")
