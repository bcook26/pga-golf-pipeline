"""Orchestrates incremental loads and season backfills."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

import pandas as pd
from database.postgres import get_engine
from database.quality import DataQualityError, load_baseline, save_results
from database.runs import (
    players_with_stats,
    record_skip,
    season_already_loaded,
    track_run,
)
from extract.base import GolfDataSource, StatsSource
from pipeline.players import run_players_pipeline
from pipeline.stats import run_stats_pipeline
from pipeline.stats_bulk import BulkStatsSource, run_bulk_stats_pipeline
from quality.checks import failures, run_quality_checks
from sqlalchemy import Engine

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


def make_quality_gate(
    engine: Engine, run_id: int | None, season: int, ignore_failures: bool = False
) -> Callable[[pd.DataFrame], None]:
    """Validate a transformed frame; record results; abort on fail-level checks."""

    def gate(stats_df: pd.DataFrame) -> None:
        results = run_quality_checks(stats_df, load_baseline(engine, season))
        if run_id is not None:
            save_results(engine, run_id, season, results)
        for r in results:
            level = {
                "pass": logging.INFO,
                "warn": logging.WARNING,
                "fail": logging.ERROR,
            }[r.status]
            log.log(
                level, "DQ %s [%s] season=%s: %s", r.name, r.status, season, r.detail
            )
        bad = failures(results)
        if bad and not ignore_failures:
            names = ", ".join(r.name for r in bad)
            raise DataQualityError(f"data-quality checks failed for {season}: {names}")

    return gate


def run(
    source: GolfDataSource,
    mode: str = "incremental",
    seasons: list[int] | None = None,
    force: bool = False,
    all_players: bool = False,
    max_workers: int = 4,
    stats_source: StatsSource | None = None,
    ignore_quality_failures: bool = False,
) -> RunSummary:
    """``source`` provides the player directory; ``stats_source`` (default:
    ``source``) provides stats. A stats source exposing
    ``fetch_season_stat_details`` is used in bulk (whole-season) mode."""
    engine = get_engine()
    stats_source = stats_source or source
    current = stats_source.current_season()
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
        if not stats_source.supports_season(season):
            reason = f"{stats_source.name} cannot serve season {season}"
        elif season != current and not force and season_already_loaded(engine, season):
            reason = "already loaded (use --force to reload)"
        else:
            with track_run(engine, "stats", mode, season) as rec:
                gate = make_quality_gate(
                    engine, rec.run_id, season, ignore_quality_failures
                )
                if hasattr(stats_source, "fetch_season_stat_details"):
                    rec.rows_loaded = run_bulk_stats_pipeline(
                        cast(BulkStatsSource, stats_source),
                        season,
                        max_workers,
                        validate=gate,
                    )
                else:
                    rec.rows_loaded = run_stats_pipeline(
                        cast(GolfDataSource, stats_source),
                        stat_players,
                        season,
                        max_workers,
                        validate=gate,
                    )
            summary.seasons_loaded[season] = rec.rows_loaded or 0
            continue

        log.warning("Skipping season %s: %s", season, reason)
        record_skip(engine, "stats", mode, season, reason)
        summary.seasons_skipped[season] = reason

    return summary
