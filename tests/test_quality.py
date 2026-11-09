import numpy as np
import pandas as pd
import pytest
from quality.checks import (
    Baseline,
    check_finite_values,
    check_null_rank_rate,
    check_null_value_rate,
    check_rank_one_present,
    check_rank_validity,
    check_row_count_drift,
    check_stat_coverage,
    failures,
    run_quality_checks,
)


def frame(n=100, null_values=0.0, null_ranks=0.0, stats=4):
    df = pd.DataFrame(
        {
            "player_id": [str(i) for i in range(n)],
            "stat_id": [f"s{i % stats}" for i in range(n)],
            "stat_value": np.arange(n, dtype=float),
            "rank": pd.array(range(1, n + 1), dtype="Int64"),
        }
    )
    # ranks restart per stat so each stat has a #1
    df["rank"] = pd.array(df.groupby("stat_id").cumcount() + 1, dtype="Int64")
    df.loc[: int(n * null_values) - 1, "stat_value"] = np.nan
    if null_ranks:
        df.loc[: int(n * null_ranks) - 1, "rank"] = pd.NA
    return df


def test_healthy_frame_passes_everything():
    results = run_quality_checks(frame(), Baseline(100, 4))
    assert [r.status for r in results] == ["pass"] * len(results)


@pytest.mark.parametrize(
    "rate,status", [(0.126, "pass"), (0.25, "warn"), (0.5, "fail")]
)
def test_null_value_rate_thresholds(rate, status):
    assert check_null_value_rate(frame(null_values=rate)).status == status


@pytest.mark.parametrize("rate,status", [(0.0, "pass"), (0.10, "warn"), (0.30, "fail")])
def test_null_rank_rate_thresholds(rate, status):
    assert check_null_rank_rate(frame(null_ranks=rate)).status == status


def test_invalid_rank_fails():
    df = frame()
    df.loc[0, "rank"] = 0
    assert check_rank_validity(df).status == "fail"


def test_infinite_values_fail():
    df = frame()
    df.loc[0, "stat_value"] = np.inf
    assert check_finite_values(df).status == "fail"


def test_missing_rank_one_warns():
    df = frame()
    df.loc[df.stat_id == "s0", "rank"] = df.loc[df.stat_id == "s0", "rank"] + 1
    r = check_rank_one_present(df)
    assert r.status == "warn" and r.observed == 1.0


@pytest.mark.parametrize(
    "previous,status",
    [
        (100, "pass"),  # unchanged
        (105, "pass"),  # 95%
        (115, "warn"),  # 87%
        (150, "fail"),  # 67%: lost a third of the rows
        (50, "warn"),  # 2x growth
        (None, "pass"),  # no baseline yet
    ],
)
def test_row_count_drift(previous, status):
    assert check_row_count_drift(frame(), Baseline(previous)).status == status


def test_stat_coverage_drop():
    assert check_stat_coverage(frame(stats=4), Baseline(None, 4)).status == "pass"
    assert (
        check_stat_coverage(frame(stats=4), Baseline(None, 5)).status == "warn"
    )  # 80%
    assert (
        check_stat_coverage(frame(stats=4), Baseline(None, 8)).status == "fail"
    )  # 50%
    assert check_stat_coverage(frame(stats=4), Baseline()).status == "pass"


def test_failures_filters():
    results = run_quality_checks(frame(null_values=0.5), Baseline(100, 4))
    assert [r.name for r in failures(results)] == ["null_value_rate"]
