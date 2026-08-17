# Standard library
import json
from pprint import pprint

# Third Party Modules
import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Local Module
from .helper import create_player_slug

def extract_stats(player_id, player_slug):

    url = (
        f"https://www.pgatour.com/player/"
        f"{player_id}/{player_slug}/stats"
    )

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    script = soup.find(
        "script",
        id="__NEXT_DATA__"
    )

    if script is None:
        raise ValueError(
            f"__NEXT_DATA__ not found "
            f"for player {player_id}"
        )

    next_data = json.loads(script.string)

    queries = (
        next_data["props"]
        ["pageProps"]
        ["dehydratedState"]
        ["queries"]
    )

    return queries

def extract_single_player_stats(
    player,
    year: int
):

    player_id = player["player_id"]
    player_name = player["display_name"]

    player_slug = create_player_slug(
        player_name
    )

    # print(
    #     f"Extracting stats for "
    #     f"{player_name} ({player_id})"
    # )

    try:

        queries = extract_stats(
            player_id,
            player_slug
        )

        stats_data = parse_stat_query(
            queries,
            year=year
        )

        player_stats = transform_stats(
            stats_data,
            year=year
        )

        return player_stats

    except Exception as e:

        print(
            f"Failed to extract "
            f"{player_name}: {e}"
        )

        return pd.DataFrame()
    
def extract_player_stats(
    players_df,
    year: int,
    max_workers: int = 10
):

    all_stats = []

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:

        futures = [
            executor.submit(
                extract_single_player_stats,
                player,
                year
            )
            for _, player in players_df.iterrows()
        ]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc=f"Extracting {year} player stats"
        ):

            player_stats = future.result()

            if not player_stats.empty:
                all_stats.append(player_stats)

    if not all_stats:
        return pd.DataFrame()

    return pd.concat(
        all_stats,
        ignore_index=True
    )


def parse_stat_query(queries, year: int = 2026):

    for query in queries:

        query_key = query.get("queryKey", [])

        if not query_key:
            continue

        if query_key[0] != "playerProfileStats":
            continue

        params = query_key[1]

        if params.get("season") != str(year):
            continue

        if params.get("tourCode") != "R":
            continue

        return query["state"]["data"]

    return None


def transform_stats(data, year: int, player_name: str):

    if data is None:
        return pd.DataFrame()

    rows = []

    for stat in data.get("stats", []):

        supporting_stat = stat.get("supportingStat")
        supporting_value = stat.get("supportingValue")

        rows.append(
            {
                "player_id": data.get("playerId"),
                "player_name": player_name,
                "season": year,
                "stat_id": stat.get("statId"),
                "stat_name": stat.get("title"),
                "stat_value": stat.get("value"),
                "rank": stat.get("rank"),
                "category": stat.get("category"),
                "above_or_below": stat.get("aboveOrBelow"),
                "field_average": stat.get("fieldAverage"),
                "supporting_stat": (
                    supporting_stat.get("value")
                    if isinstance(supporting_stat, dict)
                    else None
                ),
                "supporting_value": (
                    supporting_value.get("value")
                    if isinstance(supporting_value, dict)
                    else None
                ),
            }
        )

    return pd.DataFrame(rows)

if __name__ == "__main__":

    from players import (
        extract_players,
        player_transformation
    )
    year = 2026

    # Extract complete player directory
    players_df = extract_players()

    players_df = player_transformation(
        players_df
    )

    print(
        f"Total players: {len(players_df)}"
    )

    stats_df = extract_player_stats(
        players_df,
        year=year,
        max_workers=10
    )

    print(
        f"Total stat rows: {len(stats_df)}"
    )

    print(
        f"Players with {year} stats: "
        f"{stats_df['player_id'].nunique()}"
    )

    stats_df.to_csv(
        f"stats_{year}.csv",
        index=False
    )
