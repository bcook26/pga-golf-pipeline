"""CLI entry point.

python full_pipeline.py --mode incremental
python full_pipeline.py --mode backfill                 # last 4 seasons
python full_pipeline.py --mode backfill --seasons 2023 2024 --force
"""

from __future__ import annotations

import argparse
import logging
import time

from extract.pgatour_graphql import PGATourGraphQLSource
from extract.pgatour_pages import PGATourPageSource
from pipeline.runner import run


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PGA Tour ETL")
    p.add_argument("--mode", choices=["incremental", "backfill"], default="incremental")
    p.add_argument("--seasons", type=int, nargs="+", help="backfill: explicit seasons")
    p.add_argument("--force", action="store_true", help="reload already-loaded seasons")
    p.add_argument(
        "--all-players",
        action="store_true",
        help="probe every player for stats (default for backfill)",
    )
    p.add_argument(
        "--stats-source",
        choices=["graphql", "pages"],
        default="graphql",
        help="graphql serves history (needs PGA_GRAPHQL_KEY); pages = current season only",
    )
    p.add_argument(
        "--ignore-quality-failures",
        action="store_true",
        help="record failing data-quality checks but still load (use with care)",
    )
    p.add_argument(
        "--no-tournaments",
        action="store_true",
        help="skip the tournament schedule/results load",
    )
    p.add_argument("--max-workers", type=int, default=4)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    args = parse_args(argv)
    start = time.perf_counter()

    source = PGATourPageSource.from_settings()
    stats_source = (
        PGATourGraphQLSource.from_settings(cache=source.cache)
        if args.stats_source == "graphql"
        else source
    )
    summary = run(
        source,
        stats_source=stats_source,
        mode=args.mode,
        seasons=args.seasons,
        force=args.force,
        all_players=args.all_players,
        max_workers=args.max_workers,
        ignore_quality_failures=args.ignore_quality_failures,
        include_tournaments=not args.no_tournaments,
    )

    minutes, seconds = divmod(time.perf_counter() - start, 60)
    print(
        f"Done in {int(minutes)}m {seconds:.1f}s | loaded={summary.seasons_loaded} "
        f"skipped={summary.seasons_skipped} | "
        f"tournament results={summary.tournaments_loaded} "
        f"tournament failures={summary.tournaments_failed} | cache hits={source.cache.hits} "
        f"misses={source.cache.misses}"
    )


if __name__ == "__main__":
    main()
