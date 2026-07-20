import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from pprint import pprint


URL = "https://www.pgatour.com/stats"


def extract_stats(url):

    response = requests.get(url)

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
        print(query["queryKey"])

    return queries


def parse_stat_query(queries):

    for query in queries:

        query_key = query["queryKey"]

        if (
            query_key[0] == "statDetails"
            and query_key[1]["year"] == 2026
            and query_key[1]["eventQuery"] is None
        ):

            return query["state"]["data"]

    return None


def transform_stats(data):
    if data is None:
        raise ValueError("No stats data found")

    if "rows" not in data:
        raise KeyError(f"'rows' key not found. Available keys: {data.keys()}")

    rows = []

    for player in data["rows"]:

        # Get the primary stat value (first stat in the array)
        stat_value = player["stats"][0]["statValue"] if player["stats"] else None

        rows.append(
            {
                "tour_code": data["tourCode"],
                "season": data["year"],
                "stat_id": data["statId"],
                "player_id": player["playerId"],
                "player_name": player["playerName"],
                "country": player["country"],
                "rank": player["rank"],
                "stat_value": stat_value
            }
        )

    return pd.DataFrame(rows)



if __name__ == "__main__":

    queries = extract_stats(
        "https://www.pgatour.com/stats/detail/120"
    )

    stats_data = parse_stat_query(
        queries
    )
    pprint(stats_data["rows"][0])

    # pprint(stats_data)

    # transformed = transform_stats(stats_data)

    # # print(type(stats_data))

    # # pprint(stats_data.keys())

    # pprint(transformed)

