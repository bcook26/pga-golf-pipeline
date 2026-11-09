import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from pprint import pprint
from transform.players import player_transformation

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



if __name__ == "__main__":
    year = 2026
    player_df = extract_players()
    # transform player dataframe
    output_df = player_transformation(player_df)
    output_df.to_csv(f"players_{year}.csv",index=False)
    pprint(output_df.head())
    pprint(output_df.columns)
