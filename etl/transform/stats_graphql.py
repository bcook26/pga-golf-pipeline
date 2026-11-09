"""Normalise StatDetails leaderboards into player_stats rows."""

from __future__ import annotations

from typing import Any

import pandas as pd
from transform.stats import STATS_COLUMNS, clean_stats_frame

GRAPHQL_STATS_COLUMNS = STATS_COLUMNS + ["details"]


def transform_stat_details(
    items: list[dict[str, Any]], season: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (stats_df, players_df) for the extracted leaderboards.

    Column mapping (matches how the player-page source populated the table):
    stat_value = first column, supporting_stat = second column,
    supporting_value = last column (when there are >2). ``details`` keeps all
    columns losslessly. ``players_df`` holds the (id, name, country) seen in
    the leaderboards so players missing from the directory can be stubbed.
    """
    stat_rows: list[dict[str, Any]] = []
    player_rows: dict[str, dict[str, Any]] = {}

    for item in items:
        payload = item["payload"]
        player_entries = [
            r for r in payload["rows"] if r.get("__typename") == "StatDetailsPlayer"
        ]
        tour_avg = next(
            (
                r["value"]
                for r in payload["rows"]
                if r.get("__typename") == "StatDetailTourAvg"
            ),
            None,
        )
        category = ", ".join(item["categories"]) or None

        for row in player_entries:
            cols = row.get("stats") or []
            player_rows[row["playerId"]] = {
                "player_id": row["playerId"],
                "display_name": row["playerName"],
                "country": row.get("country"),
            }
            stat_rows.append(
                {
                    "player_id": row["playerId"],
                    "player_name": row["playerName"],
                    "season": season,
                    "stat_id": item["stat_id"],
                    "stat_name": payload["statTitle"],
                    "stat_value": cols[0]["statValue"] if cols else None,
                    "rank": row.get("rank"),
                    "category": category,
                    "above_or_below": None,
                    "field_average": tour_avg,
                    "supporting_stat": cols[1]["statValue"] if len(cols) > 1 else None,
                    "supporting_value": (
                        cols[-1]["statValue"] if len(cols) > 2 else None
                    ),
                    "details": [
                        {"name": c["statName"], "value": c["statValue"]} for c in cols
                    ],
                }
            )

    stats_df = clean_stats_frame(pd.DataFrame(stat_rows, columns=GRAPHQL_STATS_COLUMNS))
    players_df = pd.DataFrame(
        list(player_rows.values()), columns=["player_id", "display_name", "country"]
    )
    return stats_df, players_df
