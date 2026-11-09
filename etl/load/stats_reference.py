import pandas as pd
from database.postgres import upsert_stats_reference


def load_stats_reference(
    df: pd.DataFrame,
) -> int:

    return upsert_stats_reference(df)
