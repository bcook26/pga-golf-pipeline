"""Stats pipeline for sources that serve whole-season leaderboards."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Protocol

import pandas as pd
from database.postgres import insert_missing_players
from load.stats import load_graphql_season_stats
from load.stats_reference import load_stats_reference
from transform.stats_graphql import transform_stat_details
from transform.stats_reference import transform_stats_reference

log = logging.getLogger(__name__)


class BulkStatsSource(Protocol):
    name: str

    def fetch_season_stat_details(
        self, season: int, max_workers: int = 4
    ) -> list[dict[str, Any]]: ...


def run_bulk_stats_pipeline(
    source: BulkStatsSource,
    season: int,
    max_workers: int = 4,
    validate: Callable[[pd.DataFrame], None] | None = None,
) -> int:
    """Extract -> transform -> validate -> load one season; returns rows loaded.

    ``validate`` (the data-quality gate) may raise to abort before any write.
    """
    items = source.fetch_season_stat_details(season, max_workers=max_workers)
    stats_df, players_df = transform_stat_details(items, season)
    if stats_df.empty:
        return 0
    if validate is not None:
        validate(stats_df)

    stubs = insert_missing_players(players_df)
    if stubs:
        log.info("Added %d players missing from the directory", stubs)

    load_stats_reference(transform_stats_reference(stats_df))
    fetched_stat_ids = {item["stat_id"] for item in items}
    return load_graphql_season_stats(stats_df, season, fetched_stat_ids)
