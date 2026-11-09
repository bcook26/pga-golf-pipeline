import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from extract.base import GolfDataSource
from tqdm import tqdm

log = logging.getLogger(__name__)


def extract_single_player_stats(
    source: GolfDataSource, player: pd.Series, year: int
) -> dict | None:
    player_id = player["player_id"]
    player_name = player["display_name"]
    try:
        stats_data = source.fetch_player_stats(player_id, player_name, year)
    except Exception as exc:  # noqa: BLE001 - one bad player must not fail the run
        log.warning("Failed to extract %s (%s): %s", player_name, player_id, exc)
        return None

    if stats_data is None:
        return None
    return {
        "player_id": player_id,
        "player_name": player_name,
        "season": year,
        "raw_stats": stats_data,
    }


def extract_player_stats(
    source: GolfDataSource,
    players_df: pd.DataFrame,
    year: int,
    max_workers: int = 4,
) -> pd.DataFrame:
    """Fetch season stats for every player (rate limiting lives in the source)."""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(extract_single_player_stats, source, player, year)
            for _, player in players_df.iterrows()
        ]
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc=f"Extracting {year} player stats",
        ):
            result = future.result()
            if result is not None:
                results.append(result)
    return pd.DataFrame(results)
