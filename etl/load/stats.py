import pandas as pd

from database.postgres import upsert_player_stats


def load_player_stats(
    df: pd.DataFrame,
) -> None:

    upsert_player_stats(df)
