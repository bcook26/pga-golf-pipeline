from __future__ import annotations

from typing import Any

from app.db import get_conn
from app.routers.players import _escape_like, split_categories
from app.schemas import Leaderboard, LeaderRow, SeasonInfo, StatDefinition
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection, text

router = APIRouter(tags=["stats"])


@router.get("/seasons", response_model=list[SeasonInfo])
def list_seasons(conn: Connection = Depends(get_conn)) -> list[SeasonInfo]:
    rows = conn.execute(
        text(
            "SELECT season, count(DISTINCT player_id) AS players, "
            "count(DISTINCT stat_id) AS stats, count(*) AS rows "
            "FROM golf.player_stats GROUP BY season ORDER BY season DESC"
        )
    ).mappings()
    return [SeasonInfo(**r) for r in rows]


@router.get("/stats/categories", response_model=list[str])
def list_categories(conn: Connection = Depends(get_conn)) -> list[str]:
    return list(
        conn.execute(
            text(
                "SELECT DISTINCT unnest(string_to_array(category, ', ')) AS c "
                "FROM golf.player_stats WHERE category IS NOT NULL ORDER BY c"
            )
        ).scalars()
    )


@router.get("/stats", response_model=list[StatDefinition])
def list_stats(
    search: str | None = Query(None, min_length=1),
    category: str | None = None,
    conn: Connection = Depends(get_conn),
) -> list[StatDefinition]:
    """Stat catalogue with the categories each stat belongs to."""
    where: list[str] = []
    params: dict[str, Any] = {}
    if search:
        where.append("r.stat_name ILIKE :search ESCAPE '\\'")
        params["search"] = f"%{_escape_like(search)}%"
    if category:
        where.append("string_to_array(c.category, ', ') @> ARRAY[:category]")
        params["category"] = category
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = conn.execute(
        text(
            "SELECT r.stat_id, r.stat_name, c.category "
            "FROM golf.stats_reference r "
            "LEFT JOIN (SELECT DISTINCT ON (stat_id) stat_id, category "
            "           FROM golf.player_stats WHERE category IS NOT NULL "
            "           ORDER BY stat_id, season DESC) c USING (stat_id) "
            f"{clause} ORDER BY r.stat_name"
        ),
        params,
    ).mappings()
    return [
        StatDefinition(
            stat_id=r["stat_id"],
            stat_name=r["stat_name"],
            categories=split_categories(r["category"]),
        )
        for r in rows
    ]


@router.get("/stats/{stat_id}/leaders", response_model=Leaderboard)
def stat_leaders(
    stat_id: str,
    season: int | None = Query(None, description="Defaults to latest season"),
    limit: int = Query(25, ge=1, le=200),
    conn: Connection = Depends(get_conn),
) -> Leaderboard:
    if season is None:
        season = conn.execute(
            text("SELECT max(season) FROM golf.player_stats WHERE stat_id = :sid"),
            {"sid": stat_id},
        ).scalar()
        if season is None:
            raise HTTPException(status_code=404, detail=f"Stat {stat_id} not found")
    rows = list(
        conn.execute(
            text(
                "SELECT rank, player_id, player_name, stat_name, stat_value, "
                "supporting_stat, supporting_value FROM golf.player_stats "
                "WHERE stat_id = :sid AND season = :season AND rank IS NOT NULL "
                "ORDER BY rank, player_name LIMIT :limit"
            ),
            {"sid": stat_id, "season": season, "limit": limit},
        ).mappings()
    )
    if not rows:
        raise HTTPException(
            status_code=404, detail=f"No leaderboard for stat {stat_id} in {season}"
        )
    return Leaderboard(
        stat_id=stat_id,
        stat_name=rows[0]["stat_name"] or stat_id,
        season=season,
        rows=[LeaderRow(**{k: r[k] for k in LeaderRow.model_fields}) for r in rows],
    )
