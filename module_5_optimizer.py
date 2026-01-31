from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd



# Things to note of in case we want to make changes later: 
# 1. reserve margin is 15% (could be higher/lower depending on what we want) 
# 2. we only have two indicators (reliable/unreliable), 
#   but we could add other levels too such as "near-reliable" (AKA "almost works") 
#   with specific thresholds too, etc. 3. we could benefit from implementing 
#   proper ISO (international organization for standardization) practices to ensure 
#   realibility (e.g., IESO, CAISO)
# Objective definitions: total system cost and total emissions over 2025-2050 (inclusive).
OBJECTIVE_PERIOD_START = 2025
OBJECTIVE_PERIOD_END = 2050
COST_UNIT = "module2_total_cost_units"
EMISSIONS_UNIT = "t"

SCORE_METHOD = "minmax_weighted_sum"
TIE_BREAKER_RULE = "score asc, total_cost asc, total_emissions_t asc, scenario asc"
DEFAULT_TOP_K = 3
SENSITIVITY_EPSILON = 0.02


@dataclass(frozen=True)
class ObjectiveConfig:
    period_start: int = OBJECTIVE_PERIOD_START
    period_end: int = OBJECTIVE_PERIOD_END
    cost_unit: str = COST_UNIT
    emissions_unit: str = EMISSIONS_UNIT


@dataclass(frozen=True)
class ReliabilityConfig:
    mode: str = "hard"  # "hard" or "penalty"
    require_reliability_pass: bool = True
    min_reserve_margin: float | None = 0.15
    max_unmet_demand_mwh: float | None = 0.0
    penalty_strength: float = 1.0


@dataclass(frozen=True)
class FilterConfig:
    max_total_emissions_t: float | None = None
    max_total_cost: float | None = None


@dataclass(frozen=True)
class SelectionConfig:
    top_k: int = DEFAULT_TOP_K
    sensitivity_epsilon: float = SENSITIVITY_EPSILON


@dataclass(frozen=True)
class ScenarioWeights:
    name: str
    cost_weight: float
    emissions_weight: float
    reliability_penalty: float = 1.0
    rationale: str = ""


def load_supply_totals(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    df = pd.read_csv(path)
    expected = {"year", "scenario", "total_cost", "total_emissions_t"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {sorted(missing)}")
    return df


def load_storage_outputs(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    df = pd.read_csv(path)
    expected = {
        "year",
        "scenario",
        "unmet_demand_mwh",
        "reserve_margin",
        "reliability_pass",
    }
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {sorted(missing)}")
    return df


def merge_inputs(
    supply_totals: pd.DataFrame, storage_outputs: pd.DataFrame | None
) -> pd.DataFrame:
    if storage_outputs is None:
        merged = supply_totals.copy()
    else:
        merged = supply_totals.merge(
            storage_outputs,
            on=["year", "scenario"],
            how="left",
            validate="one_to_one",
        )
    return merged.sort_values(["scenario", "year"], kind="mergesort")


def _filter_period(df: pd.DataFrame, objectives: ObjectiveConfig) -> pd.DataFrame:
    filtered = df[
        (df["year"] >= objectives.period_start)
        & (df["year"] <= objectives.period_end)
    ].copy()
    if filtered.empty:
        raise ValueError(
            "No rows in objective period "
            f"{objectives.period_start}-{objectives.period_end}."
        )
    return filtered


def _ensure_optional_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in ("unmet_demand_mwh", "reserve_margin", "reliability_pass"):
        if column not in df.columns:
            df[column] = pd.NA
    return df


def aggregate_scenarios(df: pd.DataFrame) -> pd.DataFrame:
    df = _ensure_optional_columns(df)
    grouped = df.groupby("scenario", as_index=False, sort=False)
    summary = grouped.agg(
        total_cost=("total_cost", "sum"),
        total_emissions_t=("total_emissions_t", "sum"),
        unmet_demand_mwh=("unmet_demand_mwh", "sum"),
        reserve_margin_min=("reserve_margin", "min"),
        reliability_pass=("reliability_pass", "all"),
    )
    if summary.empty:
        raise ValueError("No scenarios available after aggregation.")
    return summary.sort_values("scenario", kind="mergesort").reset_index(drop=True)


def _min_max(series: pd.Series) -> pd.Series:
    min_val = series.min()
    max_val = series.max()
    if max_val <= min_val:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - min_val) / (max_val - min_val)


def _validate_weights(weights: ScenarioWeights) -> None:
    total = weights.cost_weight + weights.emissions_weight
    if weights.cost_weight < 0 or weights.emissions_weight < 0:
        raise ValueError("Weights must be non-negative.")
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"Weights for {weights.name} must sum to 1.0 (got {total:.4f})."
        )


def _validate_reliability_inputs(summary: pd.DataFrame) -> None:
    required = {"unmet_demand_mwh", "reserve_margin_min", "reliability_pass"}
    missing = required - set(summary.columns)
    if missing:
        raise ValueError(
            "Reliability inputs missing from summary: " f"{sorted(missing)}"
        )


def apply_filters(
    summary: pd.DataFrame,
    filters: FilterConfig,
) -> pd.DataFrame:
    filtered = summary.copy()
    if filters.max_total_emissions_t is not None:
        filtered = filtered[
            filtered["total_emissions_t"] <= filters.max_total_emissions_t
        ]
    if filters.max_total_cost is not None:
        filtered = filtered[filtered["total_cost"] <= filters.max_total_cost]
    if filtered.empty:
        raise ValueError("No scenarios remain after applying filters.")
    return filtered


def apply_reliability_rule(
    summary: pd.DataFrame, reliability: ReliabilityConfig
) -> pd.DataFrame:
    _validate_reliability_inputs(summary)
    result = summary.copy()
    passes = result["reliability_pass"].fillna(False)
    if reliability.require_reliability_pass:
        passes = passes.astype(bool)
    if reliability.min_reserve_margin is not None:
        passes = passes & (
            result["reserve_margin_min"] >= reliability.min_reserve_margin
        )
    if reliability.max_unmet_demand_mwh is not None:
        passes = passes & (
            result["unmet_demand_mwh"] <= reliability.max_unmet_demand_mwh
        )
    result["reliability_ok"] = passes
    if reliability.mode == "hard":
        result = result[result["reliability_ok"]]
        if result.empty:
            raise ValueError("No scenarios meet the reliability rule.")
    elif reliability.mode != "penalty":
        raise ValueError("Reliability mode must be 'hard' or 'penalty'.")
    return result


def score_scenarios(
    summary: pd.DataFrame, weights: ScenarioWeights, reliability: ReliabilityConfig
) -> pd.DataFrame:
    scored = summary.copy()
    scored["cost_norm"] = _min_max(scored["total_cost"])
    scored["emissions_norm"] = _min_max(scored["total_emissions_t"])
    scored["base_score"] = (
        weights.cost_weight * scored["cost_norm"]
        + weights.emissions_weight * scored["emissions_norm"]
    )
    if reliability.mode == "penalty":
        penalty = (~scored["reliability_ok"].fillna(False)).astype(float)
        scored["score"] = scored["base_score"] + penalty * weights.reliability_penalty
    else:
        scored["score"] = scored["base_score"]
    return scored


def rank_scenarios(scored: pd.DataFrame) -> pd.DataFrame:
    ranked = scored.sort_values(
        ["score", "total_cost", "total_emissions_t", "scenario"],
        kind="mergesort",
    ).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    return ranked


def explain_scenario(
    row: pd.Series, medians: dict[str, float], reliability: ReliabilityConfig
) -> str:
    parts: list[str] = []
    if row.get("reliability_ok") is False:
        parts.append("Fails reliability rule.")
        if reliability.min_reserve_margin is not None:
            reserve = row.get("reserve_margin_min")
            if pd.notna(reserve):
                parts.append(f"Min reserve margin: {reserve:.2f}.")
        if reliability.max_unmet_demand_mwh is not None:
            unmet = row.get("unmet_demand_mwh")
            if pd.notna(unmet):
                parts.append(f"Unmet demand: {unmet:.1f} MWh.")
    else:
        parts.append("Meets reliability rule.")

    if row.get("total_cost") >= medians["total_cost"]:
        parts.append("Cost is above the median.")
    else:
        parts.append("Cost is below the median.")

    if row.get("total_emissions_t") >= medians["total_emissions_t"]:
        parts.append("Emissions are above the median.")
    else:
        parts.append("Emissions are below the median.")

    return " ".join(parts)


def build_weight_sets() -> Iterable[ScenarioWeights]:
    return [
        ScenarioWeights(
            name="low_cost",
            cost_weight=0.7,
            emissions_weight=0.3,
            rationale="Cost-prioritized planning with emissions as a secondary guardrail.",
        ),
        ScenarioWeights(
            name="low_emissions",
            cost_weight=0.3,
            emissions_weight=0.7,
            rationale="Emissions-prioritized planning with cost awareness.",
        ),
        ScenarioWeights(
            name="balanced",
            cost_weight=0.5,
            emissions_weight=0.5,
            rationale="Even trade-off between cost and emissions.",
        ),
    ]


def _sensitivity_flag(scores: pd.Series, epsilon: float) -> tuple[bool, float]:
    if len(scores) < 2:
        return False, 0.0
    gap = float(scores.iloc[1] - scores.iloc[0])
    return gap <= epsilon, gap


def run_optimizer(
    supply_totals_path: str | Path,
    storage_outputs_path: str | Path | None,
    output_path: str | Path,
    objectives: ObjectiveConfig | None = None,
    reliability: ReliabilityConfig | None = None,
    filters: FilterConfig | None = None,
    selection: SelectionConfig | None = None,
    weight_sets: Sequence[ScenarioWeights] | None = None,
) -> pd.DataFrame:
    objectives = objectives or ObjectiveConfig()
    reliability = reliability or ReliabilityConfig()
    filters = filters or FilterConfig()
    selection = selection or SelectionConfig()
    weight_sets = weight_sets or list(build_weight_sets())

    supply_totals = load_supply_totals(supply_totals_path)
    storage_outputs = (
        load_storage_outputs(storage_outputs_path)
        if storage_outputs_path is not None
        else None
    )
    merged = merge_inputs(supply_totals, storage_outputs)
    merged = _filter_period(merged, objectives)
    summary = aggregate_scenarios(merged)
    summary = apply_filters(summary, filters)
    summary = apply_reliability_rule(summary, reliability)

    medians = {
        "total_cost": summary["total_cost"].median(),
        "total_emissions_t": summary["total_emissions_t"].median(),
    }

    results = []
    for weights in weight_sets:
        _validate_weights(weights)
        scored = score_scenarios(summary, weights, reliability)
        ranked = rank_scenarios(scored)
        sensitivity_flag, sensitivity_gap = _sensitivity_flag(
            ranked["score"], selection.sensitivity_epsilon
        )
        top = ranked.head(selection.top_k).copy()
        top["weight_set"] = weights.name
        top["weight_rationale"] = weights.rationale
        top["sensitivity_flag"] = sensitivity_flag
        top["sensitivity_gap"] = sensitivity_gap
        top["explanation"] = top.apply(
            lambda row: explain_scenario(row, medians, reliability), axis=1
        )
        results.append(top)

    output = pd.concat(results, ignore_index=True)
    output["objective_period_start"] = objectives.period_start
    output["objective_period_end"] = objectives.period_end
    output["objective_cost_unit"] = objectives.cost_unit
    output["objective_emissions_unit"] = objectives.emissions_unit
    output["reliability_mode"] = reliability.mode
    output["score_method"] = SCORE_METHOD
    output["tie_breaker_rule"] = TIE_BREAKER_RULE

    output.to_csv(Path(output_path), index=False)
    return output


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    supply_path = base_dir / "data" / "module2_supply_totals.csv"
    storage_path = base_dir / "data" / "module3_storage_outputs.csv"
    output_path = base_dir / "data" / "module5_optimizer_outputs.csv"
    run_optimizer(supply_path, storage_path, output_path)
