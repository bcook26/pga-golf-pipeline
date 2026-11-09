from collections.abc import Callable

import pandas as pd
from extract.base import GolfDataSource
from extract.stats import extract_player_stats
from load.stats import load_player_stats
from load.stats_reference import load_stats_reference
from transform.stats import transform_stats
from transform.stats_reference import transform_stats_reference


def run_stats_pipeline(
    source: GolfDataSource,
    players_df: pd.DataFrame,
    year: int,
    max_workers: int = 4,
    validate: Callable[[pd.DataFrame], None] | None = None,
) -> int:
    """Run extract/transform/load for one season; returns stat rows loaded."""
    extracted = extract_player_stats(
        source, players_df, year=year, max_workers=max_workers
    )
    stats_df = transform_stats(extracted, year=year)
    if stats_df.empty:
        return 0
    if validate is not None:
        validate(stats_df)

    load_stats_reference(transform_stats_reference(stats_df))
    return load_player_stats(stats_df)
