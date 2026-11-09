"""Normalise the PGA Tour schedule and tournament results."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import pandas as pd

TOURNAMENT_COLUMNS = [
    "tournament_id",
    "season",
    "name",
    "start_date",
    "course_name",
    "city",
    "state_code",
    "country_code",
    "purse_usd",
    "status",
    "category",
    "champion_id",
    "sequence_number",
]

RESULT_COLUMNS = [
    "tournament_id",
    "player_id",
    "position_text",
    "position",
    "is_tied",
    "status",
    "total_score",
    "to_par",
    "round_1",
    "round_2",
    "round_3",
    "round_4",
    "fedex_points",
    "earnings_usd",
]

NON_FINISH = {"CUT": "cut", "W/D": "wd", "WD": "wd", "DQ": "dq"}


def parse_int(value: Any) -> int | None:
    """'257' -> 257, '+3' -> 3, '-35' -> -35, 'E' -> 0; anything else -> None."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text.upper() == "E":
        return 0
    return int(text) if re.fullmatch(r"[+-]?\d+", text) else None


def parse_money(value: Any) -> float | None:
    """'$3,600,000.00' -> 3600000.0; '700.000' -> 700.0; '--' -> None."""
    if value is None:
        return None
    text = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def parse_position(text: Any) -> tuple[int | None, bool, str]:
    """(numeric position, tied?, status) from '1', 'T11', 'CUT', 'W/D', 'DQ'."""
    raw = str(text or "").strip().upper()
    if raw in NON_FINISH:
        return None, False, NON_FINISH[raw]
    m = re.fullmatch(r"(T?)(\d+)", raw)
    if m:
        return int(m.group(2)), bool(m.group(1)), "finished"
    return None, False, "other"


def _purse(value: Any) -> int | None:
    amount = parse_money(value)
    return int(amount) if amount is not None else None


def _start_date(millis: Any) -> Any:
    if millis in (None, ""):
        return None
    return datetime.fromtimestamp(int(millis) / 1000, tz=timezone.utc).date()


def transform_tournaments(items: list[dict[str, Any]], season: int) -> pd.DataFrame:
    """Schedule entries -> tournaments rows (one per tournament id)."""
    rows = []
    for item in items:
        t = item["tournament"]
        category = t.get("tournamentCategoryInfo") or {}
        rows.append(
            {
                "tournament_id": t["id"],
                "season": season,
                "name": (t.get("tournamentName") or "").strip() or t["id"],
                "start_date": _start_date(t.get("startDate")),
                "course_name": t.get("courseName") or None,
                "city": t.get("city") or None,
                "state_code": t.get("stateCode") or None,
                "country_code": t.get("countryCode") or None,
                "purse_usd": _purse(t.get("purse")),
                "status": str(t.get("tournamentStatus") or "").lower() or None,
                "category": category.get("type"),
                "champion_id": t.get("championId") or None,
                "sequence_number": t.get("sequenceNumber"),
            }
        )
    df = pd.DataFrame(rows, columns=TOURNAMENT_COLUMNS)
    df["purse_usd"] = df["purse_usd"].astype("Int64")
    df["sequence_number"] = df["sequence_number"].astype("Int64")
    return df.drop_duplicates(subset=["tournament_id"], keep="last").reset_index(
        drop=True
    )


def _additional(headers: list[str], values: list[str]) -> tuple[float | None, ...]:
    """(fedex points, earnings) located by header text, not position."""
    by_header = {h.lower(): v for h, v in zip(headers, values)}
    points = next((v for h, v in by_header.items() if "fedex" in h), None)
    money = next((v for h, v in by_header.items() if "money" in h), None)
    return parse_money(points), parse_money(money)


def transform_results(
    items: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (results_df, players_df) for every tournament that has results."""
    result_rows: list[dict[str, Any]] = []
    players: dict[str, dict[str, Any]] = {}

    for item in items:
        payload = item.get("results")
        if not payload:
            continue
        headers = payload.get("additionalDataHeaders") or []
        for row in payload.get("players") or []:
            player = row["player"]
            position, tied, status = parse_position(row.get("position"))
            points, earnings = _additional(headers, row.get("additionalData") or [])
            rounds = [parse_int(r.get("score")) for r in row.get("rounds") or []]
            rounds += [None] * (4 - len(rounds))
            players[player["id"]] = {
                "player_id": player["id"],
                "display_name": player.get("displayName") or player["id"],
                "country": player.get("country"),
            }
            result_rows.append(
                {
                    "tournament_id": item["tournament"]["id"],
                    "player_id": player["id"],
                    "position_text": row.get("position"),
                    "position": position,
                    "is_tied": tied,
                    "status": status,
                    "total_score": parse_int(row.get("total")),
                    "to_par": parse_int(row.get("parRelativeScore")),
                    "round_1": rounds[0],
                    "round_2": rounds[1],
                    "round_3": rounds[2],
                    "round_4": rounds[3],
                    "fedex_points": points,
                    "earnings_usd": earnings,
                }
            )

    results = pd.DataFrame(result_rows, columns=RESULT_COLUMNS)
    for col in (
        "position",
        "total_score",
        "to_par",
        "round_1",
        "round_2",
        "round_3",
        "round_4",
    ):
        results[col] = results[col].astype("Int64")
    results = results.drop_duplicates(
        subset=["tournament_id", "player_id"], keep="first"
    ).reset_index(drop=True)
    players_df = pd.DataFrame(
        list(players.values()), columns=["player_id", "display_name", "country"]
    )
    return results, players_df
