"""Data-quality checks on a transformed stats frame, before it is loaded.

Pure functions: no database access, so they are easy to unit test. Thresholds
are calibrated on the real data (about 12.6% of stat_value is legitimately null
because some stats are non-numeric, e.g. "-"), see THRESHOLDS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

Status = Literal["pass", "warn", "fail"]

# (warn_above, fail_above) for rates; (warn_below, fail_below) for ratios.
THRESHOLDS: dict[str, tuple[float, float]] = {
    "null_value_rate": (0.20, 0.40),
    "null_rank_rate": (0.05, 0.20),
    "row_count_ratio": (0.90, 0.80),  # new rows / previous rows (drops only)
    "stat_coverage_ratio": (0.90, 0.75),  # distinct stats / previous
}
ROW_GROWTH_WARN = 1.50  # warn when a load grows by more than 50%


@dataclass(frozen=True)
class Baseline:
    """What the warehouse held for this season before the load."""

    previous_rows: int | None = None
    previous_stat_count: int | None = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    observed: float | None
    threshold: str
    detail: str


def _rate_check(name: str, observed: float, what: str) -> CheckResult:
    warn, fail = THRESHOLDS[name]
    status: Status = (
        "fail" if observed > fail else "warn" if observed > warn else "pass"
    )
    return CheckResult(
        name,
        status,
        round(observed, 4),
        f"warn > {warn:.0%}, fail > {fail:.0%}",
        f"{observed:.1%} of rows have {what}",
    )


def check_null_value_rate(df: pd.DataFrame) -> CheckResult:
    return _rate_check(
        "null_value_rate",
        float(df["stat_value"].isna().mean()),
        "no numeric stat_value",
    )


def check_null_rank_rate(df: pd.DataFrame) -> CheckResult:
    return _rate_check("null_rank_rate", float(df["rank"].isna().mean()), "no rank")


def check_rank_validity(df: pd.DataFrame) -> CheckResult:
    """Ranks are 1-based; anything below 1 means a parsing problem."""
    bad = int((df["rank"].dropna().astype(float) < 1).sum())
    return CheckResult(
        "rank_validity",
        "fail" if bad else "pass",
        float(bad),
        "no rank < 1",
        f"{bad} rows have rank < 1" if bad else "all ranks >= 1",
    )


def check_finite_values(df: pd.DataFrame) -> CheckResult:
    values = pd.to_numeric(df["stat_value"], errors="coerce").astype(float)
    bad = int(np.isinf(values).sum())
    return CheckResult(
        "finite_values",
        "fail" if bad else "pass",
        float(bad),
        "no infinite stat_value",
        f"{bad} infinite values" if bad else "all values finite or null",
    )


def check_rank_one_present(df: pd.DataFrame) -> CheckResult:
    """Every stat that has ranks should have someone ranked #1."""
    ranked = df.dropna(subset=["rank"])
    lowest = ranked.groupby("stat_id")["rank"].min()
    missing = int((lowest.astype(float) != 1).sum())
    return CheckResult(
        "rank_one_present",
        "warn" if missing else "pass",
        float(missing),
        "every ranked stat has a #1",
        (
            f"{missing} stats have no #1"
            if missing
            else f"all {len(lowest)} ranked stats have a #1"
        ),
    )


def check_row_count_drift(df: pd.DataFrame, baseline: Baseline) -> CheckResult:
    name = "row_count_drift"
    if not baseline.previous_rows:
        return CheckResult(
            name,
            "pass",
            float(len(df)),
            "needs a previous load",
            "no baseline yet (first load)",
        )
    ratio = len(df) / baseline.previous_rows
    warn_below, fail_below = THRESHOLDS["row_count_ratio"]
    warn_above = ROW_GROWTH_WARN
    status: Status = (
        "fail"
        if ratio < fail_below
        else "warn" if ratio < warn_below or ratio > warn_above else "pass"
    )
    return CheckResult(
        name,
        status,
        round(ratio, 4),
        f"warn < {warn_below:.0%} or > {warn_above:.0%}, fail < {fail_below:.0%} of previous",
        f"{len(df):,} rows vs {baseline.previous_rows:,} previously ({ratio:.1%})",
    )


def check_stat_coverage(df: pd.DataFrame, baseline: Baseline) -> CheckResult:
    name = "stat_coverage"
    current = int(df["stat_id"].nunique())
    if not baseline.previous_stat_count:
        return CheckResult(
            name,
            "pass",
            float(current),
            "needs a previous load",
            f"{current} stats (no baseline yet)",
        )
    ratio = current / baseline.previous_stat_count
    warn_below, fail_below = THRESHOLDS["stat_coverage_ratio"]
    status: Status = (
        "fail" if ratio < fail_below else "warn" if ratio < warn_below else "pass"
    )
    return CheckResult(
        name,
        status,
        round(ratio, 4),
        f"warn < {warn_below:.0%}, fail < {fail_below:.0%} of previous",
        f"{current} distinct stats vs {baseline.previous_stat_count} previously",
    )


def run_quality_checks(
    df: pd.DataFrame, baseline: Baseline | None = None
) -> list[CheckResult]:
    baseline = baseline or Baseline()
    return [
        check_null_value_rate(df),
        check_null_rank_rate(df),
        check_rank_validity(df),
        check_finite_values(df),
        check_rank_one_present(df),
        check_row_count_drift(df, baseline),
        check_stat_coverage(df, baseline),
    ]


def failures(results: list[CheckResult]) -> list[CheckResult]:
    return [r for r in results if r.status == "fail"]
