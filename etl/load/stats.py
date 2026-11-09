import pandas as pd
from database.postgres import replace_graphql_season_stats, upsert_player_stats


def load_player_stats(
    df: pd.DataFrame,
) -> int:

    return upsert_player_stats(df)


def load_graphql_season_stats(df: pd.DataFrame, season: int, stat_ids: set[str]) -> int:
    return replace_graphql_season_stats(df, season, stat_ids)
