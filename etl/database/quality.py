"""Persistence for data-quality results and baselines."""

from __future__ import annotations

from quality.checks import Baseline, CheckResult
from sqlalchemy import text
from sqlalchemy.engine import Engine


class DataQualityError(RuntimeError):
    """One or more fail-level checks; the load is aborted."""


def load_baseline(engine: Engine, season: int) -> Baseline:
    with engine.connect() as conn:
        previous_rows = conn.execute(
            text(
                "SELECT rows_loaded FROM golf.etl_runs WHERE pipeline = 'stats' "
                "AND season = :s AND status = 'success' AND rows_loaded > 0 "
                "ORDER BY run_id DESC LIMIT 1"
            ),
            {"s": season},
        ).scalar()
        stat_count = conn.execute(
            text(
                "SELECT count(DISTINCT stat_id) FROM golf.player_stats "
                "WHERE season = :s AND details IS NOT NULL"
            ),
            {"s": season},
        ).scalar()
    return Baseline(previous_rows=previous_rows, previous_stat_count=stat_count or None)


def save_results(
    engine: Engine, run_id: int, season: int, results: list[CheckResult]
) -> None:
    with engine.begin() as conn:
        for r in results:
            conn.execute(
                text(
                    "INSERT INTO golf.data_quality_results "
                    "(run_id, season, check_name, status, observed, threshold, detail) "
                    "VALUES (:run, :season, :name, :status, :obs, :thr, :detail)"
                ),
                {
                    "run": run_id,
                    "season": season,
                    "name": r.name,
                    "status": r.status,
                    "obs": r.observed,
                    "thr": r.threshold,
                    "detail": r.detail,
                },
            )
