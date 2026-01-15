from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class HourlyDemand:
    date: str
    hour: int
    ontario_demand_mw: float


@dataclass(frozen=True)
class DemandSummary:
    year: int
    total_mwh: float
    average_mw: float
    peak_mw: float
    hours: int


def _filtered_csv_lines(path: Path) -> Iterable[str]:
    with path.open("r", newline="") as handle:
        for line in handle:
            if line.startswith("\\"):
                continue
            if not line.strip():
                continue
            yield line


def load_hourly_demand(path: str | Path) -> List[HourlyDemand]:
    path = Path(path)
    reader = csv.DictReader(_filtered_csv_lines(path))
    if not reader.fieldnames:
        raise ValueError(f"No header row found in {path}")
    if "Date" not in reader.fieldnames or "Hour" not in reader.fieldnames:
        raise ValueError(f"Unexpected header in {path}: {reader.fieldnames}")
    demand_field = "Ontario Demand"
    if demand_field not in reader.fieldnames:
        raise ValueError(f"Missing '{demand_field}' column in {path}")

    records: List[HourlyDemand] = []
    for row in reader:
        date = (row.get("Date") or "").strip()
        hour_raw = (row.get("Hour") or "").strip()
        demand_raw = (row.get(demand_field) or "").strip()
        if not date or not hour_raw or not demand_raw:
            continue
        records.append(
            HourlyDemand(
                date=date,
                hour=int(hour_raw),
                ontario_demand_mw=float(demand_raw),
            )
        )
    return records


def build_hourly_profile(records: Iterable[HourlyDemand]) -> List[float]:
    ordered = sorted(records, key=lambda record: (record.date, record.hour))
    return [record.ontario_demand_mw for record in ordered]


def summarize_year(records: Iterable[HourlyDemand]) -> DemandSummary:
    records_list = list(records)
    if not records_list:
        raise ValueError("No records provided")
    year = int(records_list[0].date[:4])
    total_mwh = sum(record.ontario_demand_mw for record in records_list)
    hours = len(records_list)
    average_mw = total_mwh / hours
    peak_mw = max(record.ontario_demand_mw for record in records_list)
    return DemandSummary(
        year=year,
        total_mwh=total_mwh,
        average_mw=average_mw,
        peak_mw=peak_mw,
        hours=hours,
    )


def load_demand_directory(
    directory: str | Path, pattern: str = "PUB_Demand_*.csv"
) -> Tuple[Dict[int, DemandSummary], Dict[int, List[float]]]:
    directory = Path(directory)
    summaries: Dict[int, DemandSummary] = {}
    profiles: Dict[int, List[float]] = {}
    for path in sorted(directory.glob(pattern)):
        records = load_hourly_demand(path)
        summary = summarize_year(records)
        summaries[summary.year] = summary
        profiles[summary.year] = build_hourly_profile(records)
    if not summaries:
        raise ValueError(f"No demand files found in {directory}")
    return summaries, profiles


def compute_cagr(summaries: Dict[int, DemandSummary]) -> float:
    years = sorted(summaries)
    if len(years) < 2:
        return 0.0
    start_year = years[0]
    end_year = years[-1]
    start_value = summaries[start_year].total_mwh
    end_value = summaries[end_year].total_mwh
    span = end_year - start_year
    if span <= 0 or start_value <= 0:
        return 0.0
    return (end_value / start_value) ** (1 / span) - 1


def project_annual_demand(
    base_year: int,
    base_total_mwh: float,
    start_year: int,
    end_year: int,
    base_growth_rate: float,
    population_growth: float = 0.0,
    electrification_uplift: float = 0.0,
    scenario_multiplier: float = 1.0,
) -> Dict[int, float]:
    if end_year < start_year:
        raise ValueError("end_year must be >= start_year")
    if base_total_mwh <= 0:
        raise ValueError("base_total_mwh must be positive")
    effective_growth = (1 + base_growth_rate) * (1 + population_growth) * (
        1 + electrification_uplift
    ) - 1
    projections: Dict[int, float] = {}
    for year in range(start_year, end_year + 1):
        years_from_base = year - base_year
        projected = base_total_mwh * ((1 + effective_growth) ** years_from_base)
        projections[year] = projected * scenario_multiplier
    return projections


def scale_hourly_profile(
    base_profile: Iterable[float], base_total_mwh: float, target_total_mwh: float
) -> List[float]:
    if base_total_mwh <= 0:
        raise ValueError("base_total_mwh must be positive")
    scale = target_total_mwh / base_total_mwh
    return [value * scale for value in base_profile]

def export_projections_csv(
    projections: Dict[int, float],
    output_path: str | Path,
    scenario_name: str = "baseline"
) -> None:
    """Export projections to CSV for Module 2"""
    output_path = Path(output_path)
    with output_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "scenario", "annual_demand_mwh"])
        for year, demand in sorted(projections.items()):
            writer.writerow([year, scenario_name, demand])
    print(f"Exported projections to {output_path}")

if __name__ == "__main__":
    summaries, profiles = load_demand_directory(Path(__file__).resolve().parent)
    cagr = compute_cagr(summaries)
    latest_year = max(summaries)
    latest_summary = summaries[latest_year]
    projections = project_annual_demand(
        base_year=latest_year,
        base_total_mwh=latest_summary.total_mwh,
        start_year=latest_year,
        end_year=2050,
        base_growth_rate=cagr,
        population_growth=0.003,
        electrification_uplift=0.005,
    )

    export_projections_csv(
        projections,
        output_path=Path(__file__).resolve().parent / "module2_demand_projections.csv",
        scenario_name="base_case"
    )
    print("Loaded years:", sorted(summaries))
    print("CAGR:", round(cagr, 4))
    print("Latest year summary:", latest_summary)
    print("Projection 2030 MWh:", round(projections[2030], 2))
