"""PGA Tour source backed by the Next.js ``__NEXT_DATA__`` page payload.

Limitation: pgatour.com server-renders only the *current* season on player
pages (``?season=`` is ignored; past seasons load client-side), so this source
cannot serve historical seasons. A GraphQL or licensed source implementing
``GolfDataSource`` can be dropped in for backfills.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup, Tag
from extract.base import HistoricalSeasonUnavailable
from extract.cache import PayloadCache
from extract.http import PoliteClient
from settings import get_settings
from transform.helper import create_player_slug

log = logging.getLogger(__name__)

BASE_URL = "https://www.pgatour.com"
TOUR_CODE = "R"
SEASON_TTL = 24 * 3600


def parse_next_data_queries(html: str) -> list[dict[str, Any]]:
    """Return the dehydrated react-query list embedded in a page."""
    script = BeautifulSoup(html, "html.parser").find("script", id="__NEXT_DATA__")
    if not isinstance(script, Tag) or not script.string:
        raise ValueError("__NEXT_DATA__ not found in page")
    data = json.loads(script.string)
    return data["props"]["pageProps"]["dehydratedState"]["queries"]


def find_query(queries: list[dict[str, Any]], name: str, **params: Any):
    """First query whose key[0] == name and whose params match ``params``."""
    for query in queries:
        key = query.get("queryKey") or []
        if not key or key[0] != name:
            continue
        if params:
            if len(key) < 2 or not isinstance(key[1], dict):
                continue
            if any(key[1].get(k) != v for k, v in params.items()):
                continue
        return query["state"]["data"]
    return None


class PGATourPageSource:
    name = "pgatour-pages"

    def __init__(self, client: PoliteClient, cache: PayloadCache) -> None:
        self._client = client
        self._cache = cache
        self._current: int | None = None

    @classmethod
    def from_settings(cls) -> "PGATourPageSource":
        s = get_settings()
        client = PoliteClient(
            requests_per_second=s.requests_per_second,
            max_retries=s.max_retries,
            timeout=s.request_timeout,
            user_agent=s.user_agent,
        )
        cache = PayloadCache.from_url(s.redis_url, s.cache_ttl_seconds)
        return cls(client, cache)

    @property
    def cache(self) -> PayloadCache:
        return self._cache

    def _queries(self, url: str) -> list[dict[str, Any]]:
        return parse_next_data_queries(self._client.get_text(url))

    # -- GolfDataSource -------------------------------------------------

    def current_season(self) -> int:
        if self._current is None:

            def produce() -> int:
                # The season is carried in the react-query *key*, not the data.
                for q in self._queries(f"{BASE_URL}/stats"):
                    key = q.get("queryKey") or []
                    if key and key[0] == "statOverview":
                        return int(key[1]["year"])
                raise ValueError("Could not determine current season")

            self._current = int(
                self._cache.get_or_set("current_season", produce, SEASON_TTL)
            )
        return self._current

    def supports_season(self, season: int) -> bool:
        return season == self.current_season()

    def fetch_players(self) -> pd.DataFrame:
        def produce() -> list[dict[str, Any]]:
            data = find_query(self._queries(f"{BASE_URL}/players"), "playerDirectory")
            if data is None:
                raise ValueError("playerDirectory query not found")
            return data["players"]

        return pd.DataFrame(self._cache.get_or_set("players", produce))

    def fetch_player_stats(
        self, player_id: str, display_name: str, season: int
    ) -> dict[str, Any] | None:
        if not self.supports_season(season):
            raise HistoricalSeasonUnavailable(
                f"{self.name} only serves season {self.current_season()}, "
                f"not {season}"
            )

        def produce() -> dict[str, Any] | None:
            slug = create_player_slug(display_name)
            url = f"{BASE_URL}/player/{player_id}/{slug}/stats"
            return find_query(
                self._queries(url),
                "playerProfileStats",
                season=str(season),
                tourCode=TOUR_CODE,
            )

        return self._cache.get_or_set(f"stats:{season}:{player_id}", produce)
