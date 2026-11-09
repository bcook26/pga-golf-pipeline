"""Cross-checks between the schedule and the results of the same tournaments."""

from __future__ import annotations

import pandas as pd


def champion_mismatches(tournaments: pd.DataFrame, results: pd.DataFrame) -> list[str]:
    """Tournament ids whose champion is not among the position-1 finishers.

    Only completed tournaments that have results and a champion are compared.
    The two come from different API calls, so disagreement means the results
    belong to another edition (this has happened: an unrecognised ``year``
    argument silently returned the latest edition).
    """
    if tournaments.empty or results.empty:
        return []
    winners = (
        results[results["position"] == 1]
        .groupby("tournament_id")["player_id"]
        .agg(set)
        .to_dict()
    )
    completed = tournaments[
        (tournaments["status"] == "completed") & tournaments["champion_id"].notna()
    ]
    return sorted(
        str(row.tournament_id)
        for row in completed.itertuples()
        if row.tournament_id in winners
        and row.champion_id not in winners[row.tournament_id]
    )
