"""CLI entry point.

python full_pipeline.py --mode incremental
python full_pipeline.py --mode backfill                 # last 4 seasons
python full_pipeline.py --mode backfill --seasons 2023 2024 --force
"""

from __future__ import annotations

import argparse
import logging
import time

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
    p.add_argument("--max-workers", type=int, default=4)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    args = parse_args(argv)
    start = time.perf_counter()

    source = PGATourPageSource.from_settings()
    summary = run(
        source,
        mode=args.mode,
        seasons=args.seasons,
        force=args.force,
        all_players=args.all_players,
        max_workers=args.max_workers,
    )

    minutes, seconds = divmod(time.perf_counter() - start, 60)
    print(
        f"Done in {int(minutes)}m {seconds:.1f}s | loaded={summary.seasons_loaded} "
        f"skipped={summary.seasons_skipped} | cache hits={source.cache.hits} "
        f"misses={source.cache.misses}"
    )


if __name__ == "__main__":
    main()
