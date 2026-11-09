from __future__ import annotations

import json
from typing import Any

from app.db import get_conn
from app.schemas import (
    Page,
    PlayerDetail,
    PlayerStat,
    PlayerSummary,
    StatHistory,
    StatHistoryPoint,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection, text

router = APIRouter(prefix="/players", tags=["players"])


def split_categories(value: str | None) -> list[str]:
    return [c for c in (value or "").split(", ") if c]


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _require_player(conn: Connection, player_id: str) -> str:
    name = conn.execute(
        text("SELECT display_name FROM golf.players WHERE player_id = :id"),
        {"id": player_id},
    ).scalar()
    if name is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
    return str(name)


@router.get("", response_model=Page[PlayerSummary])
def list_players(
    search: str | None = Query(None, min_length=1, description="Name contains"),
    country: str | None = None,
    active: bool | None = None,
    has_stats: bool = Query(False, description="Only players with stats"),
    season: int | None = Query(None, description="With has_stats: in this season"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    conn: Connection = Depends(get_conn),
) -> Page[PlayerSummary]:
    where: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if search:
        where.append("p.display_name ILIKE :search ESCAPE '\\'")
        params["search"] = f"%{_escape_like(search)}%"
    if country:
        where.append("p.country ILIKE :country")
        params["country"] = country
    if active is not None:
        where.append("p.is_active = :active")
        params["active"] = active
    if has_stats or season is not None:
        season_clause = " AND s.season = :season" if season is not None else ""
        where.append(
            "EXISTS (SELECT 1 FROM golf.player_stats s "
            f"WHERE s.player_id = p.player_id{season_clause})"
        )
        if season is not None:
            params["season"] = season

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(
        text(f"SELECT count(*) FROM golf.players p {clause}"), params
    ).scalar_one()
    rows = conn.execute(
        text(
            "SELECT p.player_id, p.display_name, p.is_active, p.country, "
            f"p.primary_tour FROM golf.players p {clause} "
            "ORDER BY p.display_name, p.player_id LIMIT :limit OFFSET :offset"
        ),
        params,
    ).mappings()
    return Page(
        items=[PlayerSummary(**r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{player_id}", response_model=PlayerDetail)
def get_player(player_id: str, conn: Connection = Depends(get_conn)) -> PlayerDetail:
    row = (
        conn.execute(
            text(
                "SELECT player_id, display_name, is_active, country, "
                "primary_tour, player_bio FROM golf.players "
                "WHERE player_id = :id"
            ),
            {"id": player_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
    seasons = conn.execute(
        text(
            "SELECT DISTINCT season FROM golf.player_stats "
            "WHERE player_id = :id ORDER BY season DESC"
        ),
        {"id": player_id},
    ).scalars()
    bio: dict[str, Any] | None = None
    if row["player_bio"]:
        try:
            parsed = json.loads(row["player_bio"])
            bio = parsed if isinstance(parsed, dict) else None
        except ValueError:
            bio = None
    return PlayerDetail(
        **{k: row[k] for k in row if k != "player_bio"},
        bio=bio,
        seasons=list(seasons),
    )


@router.get("/{player_id}/stats", response_model=list[PlayerStat])
def player_stats(
    player_id: str,
    season: int | None = None,
    stat_id: str | None = None,
    category: str | None = Query(None, description="Exact category, e.g. PUTTING"),
    conn: Connection = Depends(get_conn),
) -> list[PlayerStat]:
    _require_player(conn, player_id)
    where = ["player_id = :pid"]
    params: dict[str, Any] = {"pid": player_id}
    if season is not None:
        where.append("season = :season")
        params["season"] = season
    if stat_id:
        where.append("stat_id = :stat_id")
        params["stat_id"] = stat_id
    if category:
        where.append("string_to_array(category, ', ') @> ARRAY[:category]")
        params["category"] = category
    rows = conn.execute(
        text(
            "SELECT season, stat_id, stat_name, stat_value, rank, category, "
            "supporting_stat, supporting_value, details "
            f"FROM golf.player_stats WHERE {' AND '.join(where)} "
            "ORDER BY season DESC, stat_id"
        ),
        params,
    ).mappings()
    return [
        PlayerStat(
            season=r["season"],
            stat_id=r["stat_id"],
            stat_name=r["stat_name"],
            stat_value=r["stat_value"],
            rank=r["rank"],
            categories=split_categories(r["category"]),
            supporting_stat=r["supporting_stat"],
            supporting_value=r["supporting_value"],
            details=r["details"],
        )
        for r in rows
    ]


@router.get("/{player_id}/stats/{stat_id}/history", response_model=StatHistory)
def stat_history(
    player_id: str, stat_id: str, conn: Connection = Depends(get_conn)
) -> StatHistory:
    """One stat across every season - drives trend charts."""
    _require_player(conn, player_id)
    rows = list(
        conn.execute(
            text(
                "SELECT season, stat_name, stat_value, rank FROM golf.player_stats "
                "WHERE player_id = :pid AND stat_id = :sid ORDER BY season"
            ),
            {"pid": player_id, "sid": stat_id},
        ).mappings()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No {stat_id} stats for player {player_id}",
        )
    return StatHistory(
        player_id=player_id,
        stat_id=stat_id,
        stat_name=rows[-1]["stat_name"],
        points=[
            StatHistoryPoint(
                season=r["season"], stat_value=r["stat_value"], rank=r["rank"]
            )
            for r in rows
        ],
    )
