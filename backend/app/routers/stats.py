from __future__ import annotations

from typing import Any

from app.db import get_conn
from app.routers.players import _escape_like, split_categories
from app.schemas import (
    AxisInfo,
    Leaderboard,
    LeaderRow,
    Mover,
    Movers,
    Scatter,
    ScatterPoint,
    SeasonInfo,
    StatDefinition,
)
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


@router.get("/stats/scatter", response_model=Scatter)
def stat_scatter(
    x: str = Query(..., description="stat_id for the x axis"),
    y: str = Query(..., description="stat_id for the y axis"),
    season: int | None = Query(None, description="Defaults to latest with both stats"),
    conn: Connection = Depends(get_conn),
) -> Scatter:
    """One point per player that has a numeric value for both stats."""
    if x == y:
        raise HTTPException(status_code=422, detail="x and y must be different stats")
    if season is None:
        season = conn.execute(
            text(
                "SELECT max(a.season) FROM golf.player_stats a JOIN golf.player_stats b "
                "ON a.player_id = b.player_id AND a.season = b.season "
                "WHERE a.stat_id = :x AND b.stat_id = :y"
            ),
            {"x": x, "y": y},
        ).scalar()
        if season is None:
            raise HTTPException(status_code=404, detail="No season has both stats")
    rows = list(
        conn.execute(
            text(
                "SELECT a.player_id, COALESCE(p.display_name, a.player_name) AS name, "
                "a.stat_name AS x_name, b.stat_name AS y_name, "
                "a.stat_value AS xv, b.stat_value AS yv, a.rank AS rx, b.rank AS ry "
                "FROM golf.player_stats a "
                "JOIN golf.player_stats b ON a.player_id = b.player_id "
                "AND a.season = b.season AND b.stat_id = :y "
                "LEFT JOIN golf.players p ON p.player_id = a.player_id "
                "WHERE a.stat_id = :x AND a.season = :season "
                "AND a.stat_value IS NOT NULL AND b.stat_value IS NOT NULL "
                "ORDER BY name"
            ),
            {"x": x, "y": y, "season": season},
        ).mappings()
    )
    if not rows:
        raise HTTPException(
            status_code=404, detail=f"No players have both {x} and {y} in {season}"
        )
    return Scatter(
        season=season,
        x=AxisInfo(stat_id=x, stat_name=rows[0]["x_name"]),
        y=AxisInfo(stat_id=y, stat_name=rows[0]["y_name"]),
        points=[
            ScatterPoint(
                player_id=r["player_id"],
                player_name=r["name"],
                x=r["xv"],
                y=r["yv"],
                rank_x=r["rx"],
                rank_y=r["ry"],
            )
            for r in rows
        ],
    )


@router.get("/stats/{stat_id}/movers", response_model=Movers)
def stat_movers(
    stat_id: str,
    season: int | None = Query(None, description="Defaults to the latest season"),
    compare_to: int | None = Query(None, description="Defaults to the season before"),
    limit: int = Query(10, ge=1, le=50),
    conn: Connection = Depends(get_conn),
) -> Movers:
    """Biggest movers in the rankings between two seasons.

    Uses rank rather than value so "improved" is correct for stats where lower
    is better (e.g. scoring average). Only players ranked in both seasons.
    """
    if season is None:
        season = conn.execute(
            text("SELECT max(season) FROM golf.player_stats WHERE stat_id = :sid"),
            {"sid": stat_id},
        ).scalar()
        if season is None:
            raise HTTPException(status_code=404, detail=f"Stat {stat_id} not found")
    if compare_to is None:
        compare_to = conn.execute(
            text(
                "SELECT max(season) FROM golf.player_stats "
                "WHERE stat_id = :sid AND season < :season"
            ),
            {"sid": stat_id, "season": season},
        ).scalar()
        if compare_to is None:
            raise HTTPException(
                status_code=404, detail=f"No earlier season to compare {stat_id} with"
            )
    if compare_to == season:
        raise HTTPException(
            status_code=422, detail="compare_to must differ from season"
        )

    rows = [
        dict(r)
        for r in conn.execute(
            text(
                "SELECT a.player_id, COALESCE(p.display_name, a.player_name) AS name, "
                "a.stat_name, b.rank AS rank_from, a.rank AS rank_to, "
                "b.stat_value AS value_from, a.stat_value AS value_to "
                "FROM golf.player_stats a "
                "JOIN golf.player_stats b ON a.player_id = b.player_id "
                "AND b.stat_id = a.stat_id AND b.season = :prev "
                "LEFT JOIN golf.players p ON p.player_id = a.player_id "
                "WHERE a.stat_id = :sid AND a.season = :season "
                "AND a.rank IS NOT NULL AND b.rank IS NOT NULL"
            ),
            {"sid": stat_id, "season": season, "prev": compare_to},
        ).mappings()
    ]
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No players ranked on {stat_id} in both {compare_to} and {season}",
        )

    def mover(r: dict[str, Any]) -> Mover:
        return Mover(
            player_id=r["player_id"],
            player_name=r["name"],
            rank_from=r["rank_from"],
            rank_to=r["rank_to"],
            rank_change=r["rank_from"] - r["rank_to"],
            value_from=r["value_from"],
            value_to=r["value_to"],
        )

    moved = [mover(r) for r in rows]
    improvers = sorted(
        (m for m in moved if m.rank_change > 0), key=lambda m: -m.rank_change
    )
    decliners = sorted(
        (m for m in moved if m.rank_change < 0), key=lambda m: m.rank_change
    )
    return Movers(
        stat_id=stat_id,
        stat_name=rows[0]["stat_name"],
        season=season,
        compare_to=compare_to,
        players_compared=len(moved),
        improvers=improvers[:limit],
        decliners=decliners[:limit],
    )


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
