from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

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

def anual_energy(source: GenerationSource) -> float:
    return source.capacity_mw * source.capacity_factor * 8760.0

def total_annual_cost(source: GenerationSource, annual_energy_mwh: float = None) -> float:
    if annual_energy_mwh is None:
        annual_energy_mwh = anual_energy(source)
    annualized_capex = source.capex_per_mw * source.capacity_mw / source.lifetime_years
    opex = source.opex_per_mwh * annual_energy_mwh
    return annualized_capex + opex

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    sources = build_default_sources()
    demand = load_demand_projections(base_dir / "module2_demand_projections.csv")
    required_capacity = compute_required_firm_capacity(demand, reserve_margin=0.15)
    anual_energy_dict = {source.name: anual_energy(source) for source in sources}

    print("Loaded sources:", [source.name for source in sources])
    print("Required firm capacity (MW) sample:", dict(list(required_capacity.items())[:3]))
    print("Annual energy production (MWh) sample:", anual_energy_dict)