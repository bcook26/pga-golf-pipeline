"""Generic, idempotent upserts into the golf schema."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd
from database.connection import engine as make_engine
from database.tables import tables
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return make_engine()


@lru_cache(maxsize=1)
def get_tables() -> tuple[Table, Table, Table]:
    return tables(get_engine())


def to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame -> list of dicts with NaN/NaT/pd.NA converted to None.

    psycopg would otherwise send float NaN, which Postgres rejects for
    INTEGER columns (e.g. ``rank``).
    """
    cleaned = df.astype(object).where(df.notna(), None)
    return [
        {str(k): (v.item() if isinstance(v, np.generic) else v) for k, v in row.items()}
        for row in cleaned.to_dict(orient="records")
    ]


def upsert_dataframe(
    df: pd.DataFrame,
    table: Table,
    key_columns: list[str],
    chunksize: int = 1000,
    engine: Engine | None = None,
) -> int:
    """Upsert ``df`` into ``table`` on ``key_columns``; returns rows sent.

    All chunks run in one transaction, so a failure leaves the table
    untouched. Non-key columns present in ``df`` are updated on conflict.
    """
    if df.empty:
        return 0

    dupes = df.duplicated(subset=key_columns, keep=False)
    if dupes.any():
        raise ValueError(
            f"{int(dupes.sum())} duplicate key rows for {key_columns} "
            f"in {table.name}; deduplicate before loading"
        )

    update_cols = [c for c in df.columns if c not in key_columns]
    records = to_records(df)
    eng = engine or get_engine()

    with eng.begin() as conn:
        for start in range(0, len(records), chunksize):
            stmt = insert(table).values(records[start : start + chunksize])
            stmt = stmt.on_conflict_do_update(
                index_elements=key_columns,
                set_={c: stmt.excluded[c] for c in update_cols},
            )
            conn.execute(stmt)

    log.info("Upserted %d rows into %s", len(records), table.name)
    return len(records)


def upsert_players(df: pd.DataFrame) -> int:
    players, _, _ = get_tables()
    return upsert_dataframe(df, players, ["player_id"])


def upsert_player_stats(df: pd.DataFrame) -> int:
    _, stats, _ = get_tables()
    return upsert_dataframe(df, stats, ["player_id", "season", "stat_id"])


def upsert_stats_reference(df: pd.DataFrame) -> int:
    _, _, reference = get_tables()
    return upsert_dataframe(df, reference, ["stat_id"])
