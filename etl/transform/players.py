import json

import pandas as pd
from extract.config import PLAYER_DROP_COLS, TOUR_MAPPING
from transform.helper import clean_string_column


def player_transformation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw player data into the players table schema.

    Parameters
    ----------
    df : pd.DataFrame
        Raw player data.

    Returns
    -------
    pd.DataFrame
        Cleaned player data.
    """

    print(f"DataFrame contains {len(df)} rows")
    print(f"Empty names: {df['displayName'].isna().sum()}")

    df = df.copy()

    # Drop unnecessary columns
    df = df.drop(
        columns=PLAYER_DROP_COLS,
        errors="ignore",
    )

    # Clean country
    df = clean_string_column(
        df,
        "country",
        "Not Available",
    )

    # Clean display name
    df = clean_string_column(
        df,
        "displayName",
        "Unknown Player",
        title_case=False,  # keep McIlroy, DeChambeau, etc. as provided
    )

    # Map PGA Tour codes
    df["primaryTour"] = (
        df["primaryTour"]
        .fillna("No Tour Provided")
        .map(TOUR_MAPPING)
        .fillna("Unknown Tour")
    )

    # Convert dictionaries to JSON strings
    df["playerBio"] = df["playerBio"].apply(
        lambda x: json.dumps(x) if isinstance(x, dict) else x
    )

    # Rename to database schema
    df = df.rename(
        columns={
            "id": "player_id",
            "isActive": "is_active",
            "playerBio": "player_bio",
            "primaryTour": "primary_tour",
            "displayName": "display_name",
        }
    )

    # Select final column order
    df = df[
        [
            "player_id",
            "display_name",
            "is_active",
            "country",
            "player_bio",
            "primary_tour",
        ]
    ]

    print(f"Transformed {len(df)} players")

    return df
