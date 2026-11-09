import json

import pytest
from extract.base import HistoricalSeasonUnavailable
from extract.cache import PayloadCache
from extract.http import RateLimiter
from extract.pgatour_pages import PGATourPageSource, find_query, parse_next_data_queries


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, k):
        return self.store.get(k)

    def setex(self, k, ttl, v):
        self.store[k] = v


def test_rate_limiter_spaces_calls():
    now, slept = [0.0], []
    limiter = RateLimiter(2.0, clock=lambda: now[0], sleep=lambda s: slept.append(s))
    for _ in range(3):
        limiter.wait()
    assert slept == [pytest.approx(0.5), pytest.approx(1.0)]


def test_cache_hit_miss_and_none_is_cached():
    cache = PayloadCache(FakeRedis())
    calls = []

    def producer():
        calls.append(1)
        return None

    assert cache.get_or_set("k", producer) is None
    assert cache.get_or_set("k", producer) is None
    assert len(calls) == 1 and cache.hits == 1 and cache.misses == 1


def test_cache_disabled_falls_through():
    cache = PayloadCache(None)
    assert cache.get_or_set("k", lambda: 5) == 5
    assert not cache.enabled


def test_cache_survives_redis_errors():
    class Broken:
        def get(self, k):
            raise ConnectionError

        def setex(self, *a):
            raise ConnectionError

    assert PayloadCache(Broken()).get_or_set("k", lambda: 1) == 1


def _page(queries):
    data = {"props": {"pageProps": {"dehydratedState": {"queries": queries}}}}
    return f'<script id="__NEXT_DATA__">{json.dumps(data)}</script>'


def test_parse_and_find_query():
    qs = parse_next_data_queries(
        _page(
            [
                {
                    "queryKey": [
                        "playerProfileStats",
                        {"season": "2026", "tourCode": "R"},
                    ],
                    "state": {"data": {"stats": [1]}},
                },
                {
                    "queryKey": ["playerProfileStats", {"season": None}],
                    "state": {"data": None},
                },
            ]
        )
    )
    assert find_query(qs, "playerProfileStats", season="2026", tourCode="R") == {
        "stats": [1]
    }
    assert find_query(qs, "playerProfileStats", season="2025") is None


def test_missing_next_data_raises():
    with pytest.raises(ValueError):
        parse_next_data_queries("<html></html>")


class FakeClient:
    def __init__(self, pages):
        self.pages, self.urls = pages, []

    def get_text(self, url):
        self.urls.append(url)
        return self.pages[url]


def test_source_serves_current_season_only_and_caches():
    stats_page = _page(
        [
            {
                "queryKey": ["playerProfileStats", {"season": "2026", "tourCode": "R"}],
                "state": {"data": {"stats": []}},
            }
        ]
    )
    overview = _page(
        [
            {
                "queryKey": ["statOverview", {"tourCode": "R", "year": 2026}],
                "state": {"data": {}},
            }
        ]
    )
    client = FakeClient(
        {
            "https://www.pgatour.com/stats": overview,
            "https://www.pgatour.com/player/1/jon-rahm/stats": stats_page,
        }
    )
    src = PGATourPageSource(client, PayloadCache(FakeRedis()))
    assert src.current_season() == 2026
    assert src.fetch_player_stats("1", "Jon Rahm", 2026) == {"stats": []}
    src.fetch_player_stats("1", "Jon Rahm", 2026)
    assert client.urls.count("https://www.pgatour.com/player/1/jon-rahm/stats") == 1
    with pytest.raises(HistoricalSeasonUnavailable):
        src.fetch_player_stats("1", "Jon Rahm", 2024)
