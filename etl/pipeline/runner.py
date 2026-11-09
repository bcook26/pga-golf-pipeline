"""Orchestrates incremental loads and season backfills."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd
from database.postgres import get_engine
from database.runs import (
    players_with_stats,
    record_skip,
    season_already_loaded,
    track_run,
)
from extract.base import GolfDataSource
from pipeline.players import run_players_pipeline
from pipeline.stats import run_stats_pipeline

log = logging.getLogger(__name__)

BACKFILL_YEARS = 4


@dataclass
class RunSummary:
    seasons_loaded: dict[int, int] = field(default_factory=dict)
    seasons_skipped: dict[int, str] = field(default_factory=dict)


def plan_seasons(mode: str, current: int, seasons: list[int] | None) -> list[int]:
    """Seasons to process.

    incremental -> only the current season (new data lands here)
    backfill    -> explicit ``seasons`` or the last BACKFILL_YEARS seasons
    """
    if mode == "incremental":
        return [current]
    if mode == "backfill":
        return sorted(seasons or range(current - BACKFILL_YEARS + 1, current + 1))
    raise ValueError(f"Unknown mode: {mode!r}")


def select_stat_players(
    players_df: pd.DataFrame,
    mode: str,
    all_players: bool,
    known_stat_ids: set[str],
) -> pd.DataFrame:
    """Players worth requesting stats for.

    Only players that actually have stats ever produce rows (empty results are
    never loaded), but each probe costs a request, so:

    * backfill / --all-players: probe everyone (results, including "no
      stats", are cached so this is paid once)
    * incremental: active PGA Tour players plus anyone who already has stats
      in the warehouse (covers recently-retired players still in the window)
    """
    if all_players or mode == "backfill":
        return players_df
    active_pga = players_df["is_active"].fillna(False) & (
        players_df["primary_tour"] == "PGA Tour"
    )
    return players_df[active_pga | players_df["player_id"].isin(known_stat_ids)]


def run(
    source: GolfDataSource,
    mode: str = "incremental",
    seasons: list[int] | None = None,
    force: bool = False,
    all_players: bool = False,
    max_workers: int = 4,
) -> RunSummary:
    engine = get_engine()
    current = source.current_season()
    targets = plan_seasons(mode, current, seasons)
    summary = RunSummary()
    log.info("mode=%s current_season=%s targets=%s", mode, current, targets)

    with track_run(engine, "players", mode, None) as rec:
        players_df = run_players_pipeline(source)
        rec.rows_loaded = len(players_df)

    stat_players = select_stat_players(
        players_df, mode, all_players, players_with_stats(engine)
    )

    for season in targets:
        if not source.supports_season(season):
            reason = f"{source.name} cannot serve season {season}"
        elif season != current and not force and season_already_loaded(engine, season):
            reason = "already loaded (use --force to reload)"
        else:
            with track_run(engine, "stats", mode, season) as rec:
                rec.rows_loaded = run_stats_pipeline(
                    source, stat_players, season, max_workers
                )
            summary.seasons_loaded[season] = rec.rows_loaded or 0
            continue

        log.warning("Skipping season %s: %s", season, reason)
        record_skip(engine, "stats", mode, season, reason)
        summary.seasons_skipped[season] = reason

    return summary
