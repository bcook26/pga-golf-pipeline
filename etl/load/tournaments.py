import pandas as pd
from database.postgres import replace_tournament_results, upsert_tournaments


def load_tournaments(df: pd.DataFrame) -> int:
    return upsert_tournaments(df)


def load_tournament_results(df: pd.DataFrame, tournament_ids: set[str]) -> int:
    return replace_tournament_results(df, tournament_ids)
