import pandas as pd

from extract.players import extract_players
from transform.players import player_transformation
from load.players import load_players


def run_players_pipeline() -> pd.DataFrame:
    """
    Run the players extraction, transformation, and load pipeline.

    Returns
    -------
    pd.DataFrame
        Transformed player data.
    """

    # Extract
    raw_players_df = extract_players()

    # Transform
    players_df = player_transformation(
        raw_players_df
    )

    # Load
    load_players(
        players_df
    )

    return players_df


if __name__ == "__main__":
    players_df = run_players_pipeline()

    print(
        f"Players pipeline complete: "
        f"{len(players_df)} players processed."
    )
