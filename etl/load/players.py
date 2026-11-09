import pandas as pd

from database.postgres import upsert_players


def load_players(
    df: pd.DataFrame,
) -> None:

    upsert_players(df)
