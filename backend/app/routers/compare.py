"""Compare 2-4 players head to head."""

from __future__ import annotations

from typing import Any

from app.db import get_conn
from app.routers.players import split_categories
from app.schemas import (
    ComparedPlayer,
    CompareStat,
    CompareValue,
    Comparison,
    ComparisonHistory,
    PlayerSeries,
    StatHistoryPoint,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection, text

router = APIRouter(prefix="/compare", tags=["compare"])

MIN_PLAYERS, MAX_PLAYERS = 2, 4


def _load_players(conn: Connection, ids: list[str]) -> list[ComparedPlayer]:
    """Validate the id list and return players in request order."""
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Duplicate player ids")
    rows = conn.execute(
        text(
            "SELECT player_id, display_name FROM golf.players "
            "WHERE player_id = ANY(CAST(:ids AS varchar[]))"
        ),
        {"ids": ids},
    ).mappings()
    by_id = {r["player_id"]: r["display_name"] for r in rows}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise HTTPException(
            status_code=404, detail=f"Player(s) not found: {', '.join(missing)}"
        )
    return [ComparedPlayer(player_id=i, display_name=by_id[i]) for i in ids]


PlayerIds = Query(
    ...,
    min_length=MIN_PLAYERS,
    max_length=MAX_PLAYERS,
    alias="players",
    description=f"{MIN_PLAYERS}-{MAX_PLAYERS} player ids (repeat the parameter)",
)


@router.get("", response_model=Comparison)
def compare_players(
    ids: list[str] = PlayerIds,
    season: int | None = Query(None, description="Defaults to latest with data"),
    category: str | None = Query(None, description="Exact category, e.g. PUTTING"),
    conn: Connection = Depends(get_conn),
) -> Comparison:
    """Every stat any of the players has in ``season``, side by side."""
    players = _load_players(conn, ids)
    if season is None:
        season = conn.execute(
            text(
                "SELECT max(season) FROM golf.player_stats "
                "WHERE player_id = ANY(CAST(:ids AS varchar[]))"
            ),
            {"ids": ids},
        ).scalar()
        if season is None:
            raise HTTPException(
                status_code=404, detail="None of these players have statistics"
            )

    where = ["season = :season", "player_id = ANY(CAST(:ids AS varchar[]))"]
    params: dict[str, Any] = {"season": season, "ids": ids}
    if category:
        where.append("string_to_array(category, ', ') @> ARRAY[:category]")
        params["category"] = category
    rows = conn.execute(
        text(
            "SELECT stat_id, stat_name, category, player_id, stat_value, rank "
            f"FROM golf.player_stats WHERE {' AND '.join(where)} "
            "ORDER BY stat_name, stat_id"
        ),
        params,
    ).mappings()

    grouped: dict[str, dict[str, Any]] = {}
    for r in rows:
        entry = grouped.setdefault(
            r["stat_id"],
            {
                "stat_name": r["stat_name"],
                "categories": split_categories(r["category"]),
                "by_player": {},
            },
        )
        entry["by_player"][r["player_id"]] = CompareValue(
            player_id=r["player_id"], stat_value=r["stat_value"], rank=r["rank"]
        )

    stats = [
        CompareStat(
            stat_id=stat_id,
            stat_name=e["stat_name"],
            categories=e["categories"],
            values=[e["by_player"].get(p.player_id) for p in players],
        )
        for stat_id, e in grouped.items()
    ]
    return Comparison(season=season, players=players, stats=stats)


@router.get("/history", response_model=ComparisonHistory)
def compare_history(
    stat_id: str,
    ids: list[str] = PlayerIds,
    conn: Connection = Depends(get_conn),
) -> ComparisonHistory:
    """One stat across seasons for each player - drives the multi-line chart."""
    players = _load_players(conn, ids)
    rows = conn.execute(
        text(
            "SELECT player_id, season, stat_name, stat_value, rank "
            "FROM golf.player_stats WHERE stat_id = :sid "
            "AND player_id = ANY(CAST(:ids AS varchar[])) ORDER BY season"
        ),
        {"sid": stat_id, "ids": ids},
    ).mappings()

    points: dict[str, list[StatHistoryPoint]] = {p.player_id: [] for p in players}
    stat_name: str | None = None
    for r in rows:
        stat_name = r["stat_name"] or stat_name
        points[r["player_id"]].append(
            StatHistoryPoint(
                season=r["season"], stat_value=r["stat_value"], rank=r["rank"]
            )
        )
    if not any(points.values()):
        raise HTTPException(
            status_code=404, detail=f"No {stat_id} stats for these players"
        )
    return ComparisonHistory(
        stat_id=stat_id,
        stat_name=stat_name,
        series=[
            PlayerSeries(
                player_id=p.player_id,
                display_name=p.display_name,
                points=points[p.player_id],
            )
            for p in players
        ],
    )
