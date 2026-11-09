"""Tournament pipeline: schedule + per-player results for one season."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from database.postgres import insert_missing_players
from database.quality import DataQualityError
from load.tournaments import load_tournament_results, load_tournaments
from quality.tournaments import champion_mismatches
from transform.tournaments import transform_results, transform_tournaments

log = logging.getLogger(__name__)


class TournamentSource(Protocol):
    name: str

    def fetch_season_tournaments(
        self, season: int, max_workers: int = 4
    ) -> list[dict[str, Any]]: ...


def run_tournaments_pipeline(
    source: TournamentSource, season: int, max_workers: int = 4
) -> int:
    """Extract -> transform -> load one season; returns result rows loaded."""
    items = source.fetch_season_tournaments(season, max_workers=max_workers)
    tournaments = transform_tournaments(items, season)
    if tournaments.empty:
        return 0
    results, players = transform_results(items)

    bad = champion_mismatches(tournaments, results)
    if bad:
        raise DataQualityError(
            f"results do not match the champion for {len(bad)} tournaments "
            f"in {season}: {', '.join(bad[:5])}"
        )

    # Parent rows first: results reference tournaments and players.
    load_tournaments(tournaments)
    stubs = insert_missing_players(players)
    if stubs:
        log.info("Added %d players missing from the directory", stubs)
    fetched = {i["tournament"]["id"] for i in items if i.get("results")}
    return load_tournament_results(results, fetched)
