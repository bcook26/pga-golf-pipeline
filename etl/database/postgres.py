"""Generic, idempotent upserts into the golf schema."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import numpy as np
import pandas as pd
from database.connection import engine as make_engine
from database.tables import tables
from sqlalchemy import ColumnElement, Table, and_, delete
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
    delete_where: ColumnElement[bool] | None = None,
) -> int:
    """Upsert ``df`` into ``table`` on ``key_columns``; returns rows sent.

    All chunks run in one transaction, so a failure leaves the table
    untouched. Non-key columns present in ``df`` are updated on conflict.
    If ``delete_where`` is given, matching rows are deleted first in the same
    transaction (used to drop rows that vanished from a fresh pull).
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
        if delete_where is not None:
            conn.execute(delete(table).where(delete_where))
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


def replace_graphql_season_stats(
    df: pd.DataFrame, season: int, stat_ids: set[str]
) -> int:
    """Load a freshly pulled season so the warehouse mirrors it.

    Rows previously loaded from the GraphQL source (``details`` set) for the
    stats that were successfully fetched are removed first, then the new rows
    are upserted, all in one transaction. Rows from other sources
    (``details`` NULL) and stats that failed to fetch are left untouched.
    """
    _, stats, _ = get_tables()
    scope = and_(
        stats.c.season == season,
        stats.c.stat_id.in_(sorted(stat_ids)),
        stats.c.details.is_not(None),
    )
    return upsert_dataframe(
        df, stats, ["player_id", "season", "stat_id"], delete_where=scope
    )


def upsert_stats_reference(df: pd.DataFrame) -> int:
    _, _, reference = get_tables()
    return upsert_dataframe(df, reference, ["stat_id"])


def insert_missing_players(df: pd.DataFrame, engine: Engine | None = None) -> int:
    """Insert minimal player rows that don't exist yet (never overwrites).

    Historical leaderboards include retired players who are absent from the
    current directory; stats rows need them for the foreign key.
    """
    if df.empty:
        return 0
    players, _, _ = get_tables()
    stmt = (
        insert(players)
        .values(to_records(df))
        .on_conflict_do_nothing(index_elements=["player_id"])
    )
    with (engine or get_engine()).begin() as conn:
        return len(conn.execute(stmt.returning(players.c.player_id)).all())
