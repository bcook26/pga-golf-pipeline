"""Audit trail for ETL runs (golf.etl_runs)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.engine import Engine


class RunRecord:
    def __init__(self) -> None:
        self.rows_loaded: int | None = None
        self.detail: str | None = None


@contextmanager
def track_run(
    engine: Engine, pipeline: str, mode: str, season: int | None
) -> Iterator[RunRecord]:
    """Record a run as running -> success/failed around the with-block."""
    with engine.begin() as conn:
        run_id = conn.execute(
            text(
                "INSERT INTO golf.etl_runs (pipeline, mode, season, status) "
                "VALUES (:p, :m, :s, 'running') RETURNING run_id"
            ),
            {"p": pipeline, "m": mode, "s": season},
        ).scalar_one()

    record = RunRecord()
    status, detail = "success", None
    try:
        yield record
    except Exception as exc:
        status, detail = "failed", str(exc)[:1000]
        raise
    finally:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE golf.etl_runs SET status=:st, rows_loaded=:r, "
                    "detail=:d, finished_at=now() WHERE run_id=:id"
                ),
                {
                    "st": status,
                    "r": record.rows_loaded,
                    "d": detail or record.detail,
                    "id": run_id,
                },
            )


def record_skip(
    engine: Engine, pipeline: str, mode: str, season: int, reason: str
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO golf.etl_runs "
                "(pipeline, mode, season, status, detail, finished_at) "
                "VALUES (:p, :m, :s, 'skipped', :d, now())"
            ),
            {"p": pipeline, "m": mode, "s": season, "d": reason},
        )


def season_already_loaded(engine: Engine, season: int) -> bool:
    """True if a previous run successfully loaded stats rows for ``season``."""
    with engine.connect() as conn:
        return bool(
            conn.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM golf.etl_runs "
                    "WHERE pipeline='stats' AND season=:s "
                    "AND status='success' AND COALESCE(rows_loaded,0) > 0)"
                ),
                {"s": season},
            ).scalar_one()
        )
