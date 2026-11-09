"""Swappable extractor interface.

Any data provider (PGA Tour page data, PGA Tour GraphQL, DataGolf, ...) only
has to implement ``GolfDataSource``; the transform/load/pipeline layers never
know which provider produced the data.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pandas as pd


class HistoricalSeasonUnavailable(Exception):
    """The source cannot serve the requested (non-current) season."""


class StatsSource(Protocol):
    """Minimum a stats provider offers the runner (season discovery)."""

    name: str

    def current_season(self) -> int: ...

    def supports_season(self, season: int) -> bool: ...


@runtime_checkable
class GolfDataSource(Protocol):
    name: str

    def current_season(self) -> int:
        """Season the provider currently serves as 'live'."""

    def supports_season(self, season: int) -> bool:
        """Whether ``fetch_player_stats`` can return data for ``season``."""

    def fetch_players(self) -> pd.DataFrame:
        """Raw player directory (provider-native columns)."""

    def fetch_player_stats(
        self, player_id: str, display_name: str, season: int
    ) -> dict[str, Any] | None:
        """Raw season stats payload for one player, or None if no stats."""
