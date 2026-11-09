from __future__ import annotations

from typing import Any

from app.db import get_conn
from app.routers.players import _escape_like
from app.schemas import (
    TournamentDetail,
    TournamentResult,
    TournamentSummary,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection, text

router = APIRouter(tags=["tournaments"])

# Only individual stroke-play events have player results. Team and match-play
# events (Zurich Classic, Ryder Cup, Presidents Cup) are left out: completed
# tournaments without results are hidden, upcoming ones are still listed.
SUMMARY_SQL = """
SELECT t.tournament_id, t.season, t.name, t.start_date, t.course_name, t.city,
       t.state_code, t.country_code, t.purse_usd, t.status, t.category,
       w.player_id AS winner_id, p.display_name AS winner_name,
       w.to_par AS winning_to_par,
       (SELECT count(*) FROM golf.tournament_results r
         WHERE r.tournament_id = t.tournament_id) AS field_size
FROM golf.tournaments t
LEFT JOIN LATERAL (
    SELECT r.player_id, r.to_par FROM golf.tournament_results r
    WHERE r.tournament_id = t.tournament_id AND r.position = 1
    ORDER BY (r.player_id = t.champion_id) DESC, r.player_id LIMIT 1
) w ON true
LEFT JOIN golf.players p ON p.player_id = w.player_id
"""

HAS_PLAYER_RESULTS = (
    "(t.status IS DISTINCT FROM 'completed' OR EXISTS ("
    "SELECT 1 FROM golf.tournament_results x WHERE x.tournament_id = t.tournament_id))"
)


@router.get("/tournaments", response_model=list[TournamentSummary])
def list_tournaments(
    season: int | None = Query(None, description="defaults to the latest season"),
    search: str | None = Query(None, min_length=1),
    category: str | None = Query(None, description="SIGNATURE or PLAYOFF"),
    conn: Connection = Depends(get_conn),
) -> list[TournamentSummary]:
    """A season's tournaments in date order, with winner and winning score."""
    if season is None:
        season = conn.execute(text("SELECT max(season) FROM golf.tournaments")).scalar()
        if season is None:
            return []
    where = ["t.season = :season", HAS_PLAYER_RESULTS]
    params: dict[str, Any] = {"season": season}
    if search:
        where.append("t.name ILIKE :search ESCAPE '\\'")
        params["search"] = f"%{_escape_like(search)}%"
    if category:
        where.append("t.category = :category")
        params["category"] = category.upper()
    rows = conn.execute(
        text(
            f"{SUMMARY_SQL} WHERE {' AND '.join(where)} "
            "ORDER BY t.start_date NULLS LAST, t.tournament_id"
        ),
        params,
    ).mappings()
    return [TournamentSummary(**r) for r in rows]


@router.get("/tournaments/{tournament_id}", response_model=TournamentDetail)
def get_tournament(
    tournament_id: str, conn: Connection = Depends(get_conn)
) -> TournamentDetail:
    """One tournament with every player's result (finishers first, then cuts)."""
    summary = (
        conn.execute(
            text(f"{SUMMARY_SQL} WHERE t.tournament_id = :id"),
            {"id": tournament_id},
        )
        .mappings()
        .first()
    )
    if summary is None:
        raise HTTPException(404, f"Tournament {tournament_id} not found")
    rows = conn.execute(
        text(
            "SELECT r.*, p.display_name AS player_name "
            "FROM golf.tournament_results r "
            "LEFT JOIN golf.players p ON p.player_id = r.player_id "
            "WHERE r.tournament_id = :id "
            "ORDER BY CASE r.status WHEN 'finished' THEN 0 WHEN 'cut' THEN 1 ELSE 2 END, "
            "r.position NULLS LAST, r.total_score NULLS LAST, p.display_name"
        ),
        {"id": tournament_id},
    ).mappings()
    results = [
        TournamentResult(
            **{k: r[k] for k in TournamentResult.model_fields if k != "rounds"},
            rounds=[r["round_1"], r["round_2"], r["round_3"], r["round_4"]],
        )
        for r in rows
    ]
    return TournamentDetail(**summary, results=results)
