import pandas as pd
from extract.base import GolfDataSource
from extract.players import extract_players
from load.players import load_players
from transform.players import player_transformation


def run_players_pipeline(source: GolfDataSource) -> pd.DataFrame:
    """Extract, transform and load the player directory."""
    raw_players_df = extract_players(source)
    players_df = player_transformation(raw_players_df)
    load_players(players_df)
    return players_df
