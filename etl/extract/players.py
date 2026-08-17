import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from pprint import pprint
from .config import TOUR_MAPPING, PLAYER_DROP_COLS
from .helper import clean_string_column

URL = "https://www.pgatour.com/players"


def extract_players():

    response = requests.get(URL)

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    script = soup.find(
        "script",
        id="__NEXT_DATA__"
    )

    next_data = json.loads(
        script.string
    )


    queries = (
        next_data["props"]
        ["pageProps"]
        ["dehydratedState"]
        ["queries"]
    )


    for query in queries:

        if "playerDirectory" in str(query["queryKey"]):

            return pd.DataFrame(query["state"]["data"]["players"])


    return None

def player_transformation(df: pd.DataFrame) -> pd.DataFrame:

    print(f"Dataframe contains {len(df)} rows")
    print(f"Empty names: {df['displayName'].isna().sum()}")

    df = df.drop(
        columns=PLAYER_DROP_COLS,
        errors="ignore"
    )

    # Clean text columns
    df = clean_string_column(
        df,
        "country",
        "Not Available"
    )

    df = clean_string_column(
        df,
        "displayName",
        "Unknown Player"
    )

    # Handle tour mapping
    df["primaryTour"] = (
        df["primaryTour"]
        .fillna("No Tour Provided")
        .map(TOUR_MAPPING)
        .fillna("Unknown Tour")
    )

    # Rename columns for PostgreSQL
    df = df.rename(
        columns={
            "id": "player_id",
            "isActive": "is_active",
            "playerBio": "player_bio",
            "primaryTour": "primary_tour",
            "displayName": "display_name",
        }
    )

    return df

if __name__ == "__main__":
    year = 2026
    player_df = extract_players()
    # transform player dataframe
    output_df = player_transformation(player_df)
    output_df.to_csv(f"players_{year}.csv",index=False)
    pprint(output_df.head())
    pprint(output_df.columns)
