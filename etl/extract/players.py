import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from pprint import pprint
from config import TOUR_MAPPING, PLAYER_DROP_COLS
from helper import clean_string_column

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

            return query["state"]["data"]


    return None

def player_transformation(df: pd.DataFrame) -> pd.DataFrame:

    print(f"Dataframe contains {len(df)} rows")
    print(f"Empty names: {df['displayName'].isna().sum()}")

    df = df.drop(
        columns=PLAYER_DROP_COLS,
        errors="ignore"
    )

    # Clean text columns
    df = clean_string_column(df, "country", "Not Available")
    df = clean_string_column(df, "displayName", "Unknown Player")

    # Handle tour mapping separately
    df["primaryTour"] = (
        df["primaryTour"]
        .fillna("No Tour Provided")
        .map(TOUR_MAPPING)
        .fillna("Unknown Tour")
    )

    return df

if __name__ == "__main__":

    players = extract_players()
    player_df = pd.DataFrame(players['players'])
    # transform player dataframe
    output_df = player_transformation(player_df)
    # pprint(output_df.head())
    # pprint(output_df.columns)
