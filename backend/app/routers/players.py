from __future__ import annotations

import json
from typing import Any

from app.db import get_conn
from app.schemas import (
    Page,
    PercentileProfile,
    PercentileStat,
    PlayerDetail,
    PlayerStat,
    PlayerSummary,
    PlayerTournamentResult,
    PlayerTournaments,
    PlayerTournamentTotals,
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


def percentile(rank: int, field_size: int) -> float:
    """0-100 where #1 -> 100 and the last-ranked player -> 0."""
    if field_size <= 1:
        return 100.0
    return round(max(0.0, min(100.0, (field_size - rank) / (field_size - 1) * 100)), 1)


@router.get("/{player_id}/percentiles", response_model=PercentileProfile)
def player_percentiles(
    player_id: str,
    season: int | None = Query(None, description="Defaults to the player's latest"),
    category: str | None = Query(
        None, description="Exact category, e.g. STROKES_GAINED"
    ),
    conn: Connection = Depends(get_conn),
) -> PercentileProfile:
    """Where the player ranks within the field on each stat (percentile)."""
    name = _require_player(conn, player_id)
    if season is None:
        season = conn.execute(
            text("SELECT max(season) FROM golf.player_stats WHERE player_id = :id"),
            {"id": player_id},
        ).scalar()
        if season is None:
            raise HTTPException(
                status_code=404, detail=f"No stats for player {player_id}"
            )
    where = ["s.season = :season", "s.player_id = :pid", "s.rank IS NOT NULL"]
    params: dict[str, Any] = {"season": season, "pid": player_id}
    if category:
        where.append("string_to_array(s.category, ', ') @> ARRAY[:category]")
        params["category"] = category
    rows = conn.execute(
        text(
            "WITH field AS (SELECT stat_id, max(rank) AS n FROM golf.player_stats "
            "WHERE season = :season AND rank IS NOT NULL GROUP BY stat_id) "
            "SELECT s.stat_id, s.stat_name, s.category, s.stat_value, s.rank, f.n "
            "FROM golf.player_stats s JOIN field f USING (stat_id) "
            f"WHERE {' AND '.join(where)} ORDER BY s.stat_name, s.stat_id"
        ),
        params,
    ).mappings()
    return PercentileProfile(
        player_id=player_id,
        display_name=name,
        season=season,
        stats=[
            PercentileStat(
                stat_id=r["stat_id"],
                stat_name=r["stat_name"],
                categories=split_categories(r["category"]),
                stat_value=r["stat_value"],
                rank=r["rank"],
                field_size=r["n"],
                percentile=percentile(r["rank"], r["n"]),
            )
            for r in rows
        ],
    )


@router.get("/{player_id}/tournaments", response_model=PlayerTournaments)
def player_tournaments(
    player_id: str,
    season: int | None = Query(None, description="omit for all seasons"),
    conn: Connection = Depends(get_conn),
) -> PlayerTournaments:
    """A player's tournament results (newest first) with season totals."""
    name = _require_player(conn, player_id)
    params: dict[str, Any] = {"p": player_id}
    season_filter = ""
    if season is not None:
        season_filter = "AND t.season = :season "
        params["season"] = season
    rows = conn.execute(
        text(
            "SELECT t.tournament_id, t.name AS tournament_name, t.season, "
            "t.start_date, r.position_text, r.position, r.is_tied, r.status, "
            "r.total_score, r.to_par, r.fedex_points, r.earnings_usd, "
            "(SELECT count(*) FROM golf.tournament_results f "
            " WHERE f.tournament_id = t.tournament_id) AS field_size "
            "FROM golf.tournament_results r "
            "JOIN golf.tournaments t ON t.tournament_id = r.tournament_id "
            f"WHERE r.player_id = :p {season_filter}"
            "ORDER BY t.start_date DESC NULLS LAST, t.tournament_id DESC"
        ),
        params,
    ).mappings()
    results = [PlayerTournamentResult(**r) for r in rows]
    totals = PlayerTournamentTotals(
        starts=len(results),
        cuts_made=sum(1 for r in results if r.status == "finished"),
        wins=sum(1 for r in results if r.position == 1),
        top_10s=sum(1 for r in results if r.position is not None and r.position <= 10),
        earnings_usd=sum(r.earnings_usd or 0 for r in results),
        fedex_points=sum(r.fedex_points or 0 for r in results),
    )
    return PlayerTournaments(
        player_id=player_id,
        display_name=name,
        season=season,
        totals=totals,
        results=results,
    )
