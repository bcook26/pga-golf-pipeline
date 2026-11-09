"""Response models (the contract the React/TypeScript client consumes)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

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


class ComparedPlayer(BaseModel):
    player_id: str
    display_name: str


class CompareValue(BaseModel):
    player_id: str
    stat_value: float | None
    rank: int | None


class CompareStat(BaseModel):
    stat_id: str
    stat_name: str | None
    categories: list[str]
    # One entry per requested player, in request order; None = no data
    values: list[CompareValue | None]


class Comparison(BaseModel):
    season: int
    players: list[ComparedPlayer]
    stats: list[CompareStat]


class PlayerSeries(BaseModel):
    player_id: str
    display_name: str
    points: list[StatHistoryPoint]


class ComparisonHistory(BaseModel):
    stat_id: str
    stat_name: str | None
    series: list[PlayerSeries]


class PercentileStat(BaseModel):
    stat_id: str
    stat_name: str | None
    categories: list[str]
    stat_value: float | None
    rank: int
    field_size: int  # number of ranked players (the largest rank) for this stat
    percentile: float  # 0-100, 100 = best (#1)


class PercentileProfile(BaseModel):
    player_id: str
    display_name: str
    season: int
    stats: list[PercentileStat]


class Mover(BaseModel):
    player_id: str
    player_name: str | None
    rank_from: int
    rank_to: int
    rank_change: int  # rank_from - rank_to; positive = moved up the rankings
    value_from: float | None
    value_to: float | None


class Movers(BaseModel):
    stat_id: str
    stat_name: str | None
    season: int
    compare_to: int
    players_compared: int
    improvers: list[Mover]
    decliners: list[Mover]


class AxisInfo(BaseModel):
    stat_id: str
    stat_name: str | None


class ScatterPoint(BaseModel):
    player_id: str
    player_name: str | None
    x: float
    y: float
    rank_x: int | None
    rank_y: int | None


class Scatter(BaseModel):
    season: int
    x: AxisInfo
    y: AxisInfo
    points: list[ScatterPoint]


Status = Literal["ok", "warn", "fail"]


class PipelineRun(BaseModel):
    run_id: int
    pipeline: str
    mode: str
    season: int | None
    status: str
    rows_loaded: int | None
    detail: str | None
    started_at: datetime
    finished_at: datetime | None
    duration_seconds: float | None


class SeasonFreshness(BaseModel):
    season: int
    rows: int
    players: int
    stats: int
    last_success_at: datetime | None
    age_seconds: float | None
    last_run_status: str | None


class QualityResult(BaseModel):
    run_id: int | None
    season: int | None
    check_name: str
    status: Literal["pass", "warn", "fail"]
    observed: float | None
    threshold: str | None
    detail: str | None
    checked_at: datetime


class PipelineStatus(BaseModel):
    generated_at: datetime
    overall: Status
    reasons: list[str]
    seasons: list[SeasonFreshness]
    quality: list[QualityResult]
    runs: list[PipelineRun]
