"""Response models (the contract the React/TypeScript client consumes)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class PlayerSummary(BaseModel):
    player_id: str
    display_name: str
    is_active: bool | None
    country: str | None
    primary_tour: str | None


class PlayerDetail(PlayerSummary):
    bio: dict[str, Any] | None
    seasons: list[int]  # seasons with stats for this player


class PlayerStat(BaseModel):
    season: int
    stat_id: str
    stat_name: str | None
    stat_value: float | None
    rank: int | None
    categories: list[str]
    supporting_stat: str | None
    supporting_value: str | None
    details: list[dict[str, Any]] | None


class StatHistoryPoint(BaseModel):
    season: int
    stat_value: float | None
    rank: int | None


class StatHistory(BaseModel):
    player_id: str
    stat_id: str
    stat_name: str | None
    points: list[StatHistoryPoint]


class StatDefinition(BaseModel):
    stat_id: str
    stat_name: str
    categories: list[str]


class LeaderRow(BaseModel):
    rank: int | None
    player_id: str
    player_name: str | None
    stat_value: float | None
    supporting_stat: str | None
    supporting_value: str | None


class Leaderboard(BaseModel):
    stat_id: str
    stat_name: str
    season: int
    rows: list[LeaderRow]


class SeasonInfo(BaseModel):
    season: int
    players: int
    stats: int
    rows: int


class Health(BaseModel):
    status: str
    database: str
