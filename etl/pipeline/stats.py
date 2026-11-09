import pandas as pd

from extract.stats import extract_player_stats
from transform.stats import transform_stats
from transform.stats_reference import transform_stats_reference
from load.stats import load_player_stats
from load.stats_reference import load_stats_reference


def run_stats_pipeline(
    players_df: pd.DataFrame,
    year: int,
    max_workers: int = 10,
) -> pd.DataFrame:

    extracted_stats = extract_player_stats(
        players_df,
        year=year,
        max_workers=max_workers,
    )

    stats_df = transform_stats(
        extracted_stats,
        year=year,
    )

    stats_reference_df = transform_stats_reference(
        stats_df
    )

    load_stats_reference(
        stats_reference_df
    )

    load_player_stats(
        stats_df
    )

    return stats_df
