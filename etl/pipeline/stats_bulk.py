"""Stats pipeline for sources that serve whole-season leaderboards."""

from __future__ import annotations

import logging
from typing import Any, Protocol

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
    source: BulkStatsSource, season: int, max_workers: int = 4
) -> int:
    """Extract -> transform -> load one season; returns stat rows loaded."""
    items = source.fetch_season_stat_details(season, max_workers=max_workers)
    stats_df, players_df = transform_stat_details(items, season)
    if stats_df.empty:
        return 0

    stubs = insert_missing_players(players_df)
    if stubs:
        log.info("Added %d players missing from the directory", stubs)

    load_stats_reference(transform_stats_reference(stats_df))
    fetched_stat_ids = {item["stat_id"] for item in items}
    return load_graphql_season_stats(stats_df, season, fetched_stat_ids)
