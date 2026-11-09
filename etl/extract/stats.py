# Standard library
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third Party Modules
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# Local Modules
from transform.helper import create_player_slug


def extract_stats(
    player_id: str,
    player_slug: str,
):
    url = (
        f"https://www.pgatour.com/player/"
        f"{player_id}/{player_slug}/stats"
    )

    response = requests.get(
        url,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    script = soup.find(
        "script",
        id="__NEXT_DATA__",
    )

    if script is None:
        raise ValueError(
            f"__NEXT_DATA__ not found "
            f"for player {player_id}"
        )

    next_data = json.loads(script.string)

    return (
        next_data["props"]
        ["pageProps"]
        ["dehydratedState"]
        ["queries"]
    )


def extract_single_player_stats(
    player,
    year: int,
):
    player_id = player["player_id"]
    player_name = player["display_name"]

    player_slug = create_player_slug(
        player_name,
    )

    try:
        queries = extract_stats(
            player_id,
            player_slug,
        )

        stats_data = parse_stat_query(
            queries,
            year=year,
        )

        if stats_data is None:
            return None

        return {
            "player_id": player_id,
            "player_name": player_name,
            "season": year,
            "raw_stats": stats_data,
        }

    except Exception as e:
        print(
            f"Failed to extract "
            f"{player_name}: {e}"
        )

        return None


def extract_player_stats(
    players_df: pd.DataFrame,
    year: int,
    max_workers: int = 10,
) -> pd.DataFrame:

    all_stats = []

    with ThreadPoolExecutor(
        max_workers=max_workers,
    ) as executor:

        futures = [
            executor.submit(
                extract_single_player_stats,
                player,
                year,
            )
            for _, player in players_df.iterrows()
        ]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc=f"Extracting {year} player stats",
        ):
            player_stats = future.result()

            if player_stats is not None:
                all_stats.append(player_stats)

    return pd.DataFrame(all_stats)


def parse_stat_query(
    queries,
    year: int,
):
    for query in queries:

        query_key = query.get(
            "queryKey",
            [],
        )

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
