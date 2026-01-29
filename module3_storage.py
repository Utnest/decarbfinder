"""Module 3: Storage modeling and reliability checks.

This module consumes Module 2 outputs (per-year supply totals) and applies
storage dispatch plus simple reliability metrics.

Expected input CSV (from Module 2):
  - module2_supply_totals.csv
    columns: year, scenario, annual_demand_mwh, energy_generated_mwh,
             unmet_demand_mwh, required_firm_capacity_mw, total_capacity_mw,
             total_cost, total_emissions_t

Outputs (to be produced by this module):
  - module3_storage_outputs.csv
    columns: year, scenario, annual_demand_mwh, energy_generated_mwh,
             storage_delivered_mwh, unmet_demand_mwh, reserve_margin,
             reliability_pass
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class StorageParams:
    """Storage configuration for a single scenario run."""

    energy_capacity_mwh: float
    power_capacity_mw: float
    round_trip_efficiency: float
    initial_soc_fraction: float = 0.5


def load_supply_totals(path: str | Path) -> pd.DataFrame:
    """Load Module 2 per-year totals as a DataFrame."""
    path = Path(path)
    df = pd.read_csv(path)
    expected = {
        "year",
        "scenario",
        "annual_demand_mwh",
        "energy_generated_mwh",
        "required_firm_capacity_mw",
        "total_capacity_mw",
    }
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {sorted(missing)}")
    return df


def default_storage_params() -> StorageParams:
    """Return placeholder storage parameters until calibrated."""
    return StorageParams(
        energy_capacity_mwh=2000.0,
        power_capacity_mw=500.0,
        round_trip_efficiency=0.9,
        initial_soc_fraction=0.5,
    )


def dispatch_storage(
    supply_totals: pd.DataFrame, storage: StorageParams
) -> pd.DataFrame:
    """Apply storage dispatch and calculate unmet demand."""
    if supply_totals.empty:
        raise ValueError("supply_totals must not be empty")
    if not 0.0 <= storage.initial_soc_fraction <= 1.0:
        raise ValueError("initial_soc_fraction must be between 0 and 1")
    if storage.round_trip_efficiency <= 0 or storage.round_trip_efficiency > 1:
        raise ValueError("round_trip_efficiency must be in (0, 1]")

    results = supply_totals.copy()
    deficits: Iterable[float] = (
        results["annual_demand_mwh"] - results["energy_generated_mwh"]
    )
    results["deficit_mwh"] = deficits.clip(lower=0.0)

    energy_limit = storage.energy_capacity_mwh * storage.initial_soc_fraction
    power_limit = storage.power_capacity_mw * 8760.0
    deliverable = min(energy_limit, power_limit)
    delivered_raw = results["deficit_mwh"].clip(upper=deliverable)
    results["storage_delivered_mwh"] = delivered_raw * storage.round_trip_efficiency
    results["unmet_demand_mwh"] = (
        results["deficit_mwh"] - results["storage_delivered_mwh"]
    ).clip(lower=0.0)
    return results


def compute_reliability(
    storage_results: pd.DataFrame, reserve_margin_target: float = 0.15
) -> pd.DataFrame:
    """Compute reserve margin and pass/fail flags per year."""
    if reserve_margin_target < 0:
        raise ValueError("reserve_margin_target must be >= 0")
    results = storage_results.copy()
    avg_mw = results["annual_demand_mwh"] / 8760.0
    results["reserve_margin"] = (results["total_capacity_mw"] - avg_mw) / avg_mw
    results["reliability_pass"] = (
        (results["reserve_margin"] >= reserve_margin_target)
        & (results["unmet_demand_mwh"] <= 0.0)
    )
    return results


def save_outputs(results: pd.DataFrame, output_path: str | Path) -> None:
    """Persist per-year storage results."""
    output_path = Path(output_path)
    results.to_csv(output_path, index=False)


def run_module(
    input_path: str | Path,
    output_path: str | Path,
    reserve_margin_target: float = 0.15,
) -> pd.DataFrame:
    """Orchestrate Module 3: load, dispatch, compute reliability, save."""
    supply_totals = load_supply_totals(input_path)
    storage = default_storage_params()
    storage_results = dispatch_storage(supply_totals, storage)
    reliability_results = compute_reliability(
        storage_results, reserve_margin_target=reserve_margin_target
    )
    output_columns = [
        "year",
        "scenario",
        "annual_demand_mwh",
        "energy_generated_mwh",
        "storage_delivered_mwh",
        "unmet_demand_mwh",
        "reserve_margin",
        "reliability_pass",
    ]
    save_outputs(reliability_results[output_columns], output_path)
    return reliability_results


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "data" / "module2_supply_totals.csv"
    output_path = base_dir / "data" / "module3_storage_outputs.csv"
    run_module(input_path, output_path)
