import pandas as pd

from extract.players import (
    extract_players,
    player_transformation,
)

from extract.stats import (
    extract_player_stats,
)

from load.postgres import (
    upsert_players,
    upsert_player_stats,
)

def run_pipeline(year: int):

    # -------------------------
    # Extract players
    # -------------------------

    players_df = extract_players()

    # -------------------------
    # Transform players
    # -------------------------

    players_df = player_transformation(
        players_df
    )

    print(
        f"Extracted {len(players_df)} players"
    )

    # -------------------------
    # Load players
    # -------------------------

    upsert_players(
        players_df
    )

    print(
        "Players loaded."
    )

    # -------------------------
    # Extract stats
    # -------------------------

    stats_df = extract_player_stats(
        players_df,
        year=year,
        max_workers=10,
    )

    print(
        f"Extracted {len(stats_df)} stats"
    )

    # -------------------------
    # Load stats
    # -------------------------
    stats_df["category"] = stats_df["category"].astype(str)
    upsert_player_stats(
        stats_df
    )

    print(
        "Player stats loaded."
    )

if __name__ == "__main__":

    run_pipeline(
        year=2026
    )
