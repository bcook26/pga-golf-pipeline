from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from app.main import app
from app.ratelimit import RateLimiter, client_ip
from fastapi.testclient import TestClient


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def limiter(clock: Clock, minute: int = 3, hour: int = 10, glob: int = 100, **kw):
    return RateLimiter(minute, hour, glob, clock=clock, **kw)


def test_per_minute_limit_and_recovery() -> None:
    clock = Clock()
    rl = limiter(clock)
    assert all(rl.check("a").allowed for _ in range(3))
    refused = rl.check("a")
    assert not refused.allowed and refused.scope == "client"
    assert refused.retry_after == 60
    clock.advance(20)
    assert rl.check("a").retry_after == 40  # counts down
    clock.advance(41)
    assert rl.check("a").allowed


def test_clients_are_independent() -> None:
    rl = limiter(Clock())
    assert all(rl.check("a").allowed for _ in range(3))
    assert not rl.check("a").allowed
    assert rl.check("b").allowed


def test_per_hour_limit_catches_slow_sustained_use() -> None:
    clock = Clock()
    rl = limiter(clock, minute=3, hour=5)
    for _ in range(5):
        assert rl.check("a").allowed
        clock.advance(30)  # slow enough to stay under the per-minute limit
    d = rl.check("a")
    assert not d.allowed and d.scope == "client"
    assert d.retry_after == 3600 - 4 * 30 - 30  # oldest hit leaves the hour window


def test_global_cap_applies_across_clients_and_is_not_extended_by_refusals() -> None:
    clock = Clock()
    rl = limiter(clock, minute=10, hour=10, glob=5)
    for i in range(5):
        assert rl.check(f"client-{i}").allowed
    for i in range(20):  # a flood of new clients, all refused
        d = rl.check(f"other-{i}")
        assert not d.allowed and d.scope == "global"
    assert len(rl._global) == 5  # refusals were not recorded
    clock.advance(3601)
    assert rl.check("late").allowed


def test_refused_requests_do_not_extend_the_block() -> None:
    clock = Clock()
    rl = limiter(clock)
    for _ in range(3):
        rl.check("a")
    for _ in range(50):
        clock.advance(1)
        rl.check("a")  # hammering while blocked
    clock.advance(11)
    assert rl.check("a").allowed  # 61s after the first hit, despite the hammering


def test_zero_disables_a_limit() -> None:
    rl = RateLimiter(0, 0, 0, clock=Clock())
    assert all(rl.check("a").allowed for _ in range(10_000))


def test_client_memory_is_bounded() -> None:
    rl = limiter(Clock(), max_clients=2)
    for name in ("a", "b", "c"):
        rl.check(name)
    assert len(rl._clients) == 2 and "a" not in rl._clients


def _request(forwarded: str | None, peer: str | None = "10.0.0.9"):
    headers = {"x-forwarded-for": forwarded} if forwarded is not None else {}
    return SimpleNamespace(
        headers=headers, client=SimpleNamespace(host=peer) if peer else None
    )


def test_client_ip_uses_socket_peer_without_proxies() -> None:
    assert client_ip(_request("1.1.1.1"), 0) == "10.0.0.9"  # header ignored
    assert client_ip(_request(None, peer=None), 0) == "unknown"


def test_client_ip_ignores_spoofed_left_entries() -> None:
    # client sent "6.6.6.6"; our proxy appended the address it actually saw
    assert client_ip(_request("6.6.6.6, 203.0.113.7"), 1) == "203.0.113.7"
    assert client_ip(_request("6.6.6.6, 203.0.113.7, 10.1.1.1"), 2) == "203.0.113.7"
    # fewer entries than trusted hops: fall back to the peer, never to a guess
    assert client_ip(_request("203.0.113.7"), 2) == "10.0.0.9"


@pytest.fixture()
def tiny_limit() -> Iterator[RateLimiter]:
    original = app.state.limiter
    app.state.limiter = RateLimiter(2, 100, 100)
    yield app.state.limiter
    app.state.limiter = original


def test_middleware_returns_429_with_retry_after_and_cors(
    tiny_limit: RateLimiter,
) -> None:
    client = TestClient(app)
    origin = {"Origin": "http://localhost:5173"}
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    blocked = client.get("/openapi.json", headers=origin)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert "Try again in" in blocked.json()["detail"]
    # the browser can only read the error if CORS headers are on the 429
    assert blocked.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_health_checks_and_preflights_are_never_limited(
    tiny_limit: RateLimiter,
) -> None:
    client = TestClient(app)
    for _ in range(10):
        assert client.get("/live").status_code == 200
        assert client.options(
            "/api/v1/seasons",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        ).status_code in (200, 204)
    assert tiny_limit.check("someone").allowed  # nothing was consumed


def test_live_does_not_need_the_database() -> None:
    assert TestClient(app).get("/live").json() == {"status": "ok"}
