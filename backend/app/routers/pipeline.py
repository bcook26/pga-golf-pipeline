"""Operational view of the ETL: runs, freshness and data-quality results."""

from __future__ import annotations

from datetime import UTC, datetime

from app.config import get_settings
from app.db import get_conn
from app.schemas import (
    PipelineRun,
    PipelineStatus,
    QualityResult,
    SeasonFreshness,
    Status,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection, text

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

SEVERITY = {"fail": 0, "warn": 1, "pass": 2}  # sort order: worst first
LEVEL: dict[str, int] = {"ok": 0, "warn": 1, "fail": 2}


@router.get("/status", response_model=PipelineStatus)
def pipeline_status(
    runs: int = Query(25, ge=1, le=100, description="How many recent runs to return"),
    conn: Connection = Depends(get_conn),
) -> PipelineStatus:
    now = datetime.now(UTC)

    run_rows = conn.execute(
        text(
            "SELECT run_id, pipeline, mode, season, status, rows_loaded, detail, "
            "started_at, finished_at, "
            "EXTRACT(EPOCH FROM (finished_at - started_at)) AS duration_seconds "
            "FROM golf.etl_runs ORDER BY run_id DESC LIMIT :n"
        ),
        {"n": runs},
    ).mappings()
    recent = [PipelineRun(**r) for r in run_rows]

    season_rows = conn.execute(
        text(
            "SELECT p.season, p.rows, p.players, p.stats, "
            "r.last_success_at, r.last_run_status "
            "FROM (SELECT season, count(*) AS rows, "
            "      count(DISTINCT player_id) AS players, "
            "      count(DISTINCT stat_id) AS stats "
            "      FROM golf.player_stats GROUP BY season) p "
            "LEFT JOIN (SELECT season, "
            "      max(finished_at) FILTER (WHERE status = 'success') AS last_success_at, "
            "      (array_agg(status ORDER BY run_id DESC))[1] AS last_run_status "
            "      FROM golf.etl_runs WHERE pipeline = 'stats' GROUP BY season) r "
            "USING (season) ORDER BY p.season DESC"
        )
    ).mappings()
    seasons = [
        SeasonFreshness(
            **r,
            age_seconds=(
                (now - r["last_success_at"]).total_seconds()
                if r["last_success_at"]
                else None
            ),
        )
        for r in season_rows
    ]

    quality_rows = conn.execute(
        text(
            "SELECT DISTINCT ON (season, check_name) run_id, season, check_name, "
            "status, observed, threshold, detail, checked_at "
            "FROM golf.data_quality_results "
            "ORDER BY season, check_name, checked_at DESC"
        )
    ).mappings()
    quality = sorted(
        (QualityResult(**r) for r in quality_rows),
        key=lambda q: (-(q.season or 0), SEVERITY[q.status], q.check_name),
    )

    reasons: list[str] = []
    overall: Status = "ok"

    def escalate(level: Status, reason: str) -> None:
        """Record a reason and raise the overall status (ok < warn < fail)."""
        nonlocal overall
        reasons.append(reason)
        if LEVEL[level] > LEVEL[overall]:
            overall = level

    latest_by_key: dict[tuple[str, int | None], PipelineRun] = {}
    for run in recent:  # newest first
        latest_by_key.setdefault((run.pipeline, run.season), run)
    for (pipeline, season), run in latest_by_key.items():
        if run.status == "failed":
            label = f"{pipeline} {season}" if season else pipeline
            escalate("fail", f"Latest {label} run failed: {run.detail or 'see runs'}")
    for q in quality:
        if q.status == "fail":
            escalate("fail", f"{q.season}: {q.check_name} failed - {q.detail}")
        elif q.status == "warn":
            escalate("warn", f"{q.season}: {q.check_name} warning - {q.detail}")
    if seasons and seasons[0].age_seconds is not None:
        if seasons[0].age_seconds > get_settings().pipeline_stale_after_hours * 3600:
            hours = seasons[0].age_seconds / 3600
            escalate("warn", f"Season {seasons[0].season} last loaded {hours:.0f}h ago")

    return PipelineStatus(
        generated_at=now,
        overall=overall,
        reasons=reasons,
        seasons=seasons,
        quality=quality,
        runs=recent,
    )
