"""Strict, dependency-free rate limiting for the public API.

Three independent ceilings, all sliding windows:

* per client, per minute  - stops one visitor hammering the API
* per client, per hour    - stops slow sustained scraping
* global, per hour        - the hard cap that protects the free-tier budgets
                            (database compute, hosting hours) no matter how
                            many clients there are or whether client
                            identification can be spoofed

Only allowed requests are recorded, so being refused never extends a block.
State lives in memory (one process); the free host runs a single instance.
"""

from __future__ import annotations

import logging
import math
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

MINUTE, HOUR = 60.0, 3600.0
# Never reject platform health checks (they do not touch the database).
EXEMPT_PATHS = {"/live", "/health"}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: int = 0  # whole seconds until a retry can succeed
    scope: str = ""  # "client" or "global" when refused


def _retry_after(hits: Sequence[float], limit: int, span: float, now: float) -> float:
    """Seconds until the oldest hit that fills a ``limit``-sized window expires."""
    return hits[-limit] + span - now


class RateLimiter:
    def __init__(
        self,
        per_minute: int,
        per_hour: int,
        global_per_hour: int,
        clock: Callable[[], float] = time.monotonic,
        max_clients: int = 2000,
    ) -> None:
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.global_per_hour = global_per_hour
        self._clock = clock
        self._max_clients = max_clients
        self._clients: OrderedDict[str, deque[float]] = OrderedDict()
        self._global: deque[float] = deque()

    def _trim(self, window: deque[float], now: float) -> None:
        while window and window[0] <= now - HOUR:
            window.popleft()

    def check(self, client: str) -> Decision:
        """Record and allow the request, or refuse it with a retry delay."""
        now = self._clock()
        self._trim(self._global, now)
        hits = self._clients.get(client)
        if hits is None:
            hits = deque()
        self._trim(hits, now)

        # A limit of 0 means "no limit of this kind".
        waits: list[float] = []
        recent = [t for t in hits if t > now - MINUTE]
        if self.per_minute and len(recent) >= self.per_minute:
            waits.append(_retry_after(recent, self.per_minute, MINUTE, now))
        if self.per_hour and len(hits) >= self.per_hour:
            waits.append(_retry_after(hits, self.per_hour, HOUR, now))
        if waits:
            return Decision(False, math.ceil(max(waits)), "client")

        if self.global_per_hour and len(self._global) >= self.global_per_hour:
            return Decision(
                False,
                math.ceil(_retry_after(self._global, self.global_per_hour, HOUR, now)),
                "global",
            )

        hits.append(now)
        self._global.append(now)
        self._clients[client] = hits
        self._clients.move_to_end(client)
        while len(self._clients) > self._max_clients:
            self._clients.popitem(last=False)  # forget the least recent client
        return Decision(True)


def client_ip(request: Request, proxy_hops: int) -> str:
    """Caller address. With ``proxy_hops`` > 0 the Nth entry from the right of
    X-Forwarded-For is used: entries to its left are client-controlled and
    cannot be trusted, entries to its right were added by our own proxies."""
    if proxy_hops > 0:
        parts = [
            p.strip()
            for p in request.headers.get("x-forwarded-for", "").split(",")
            if p.strip()
        ]
        if len(parts) >= proxy_hops:
            return parts[-proxy_hops]
    return request.client.host if request.client else "unknown"


def install_rate_limit(app: FastAPI, limiter: RateLimiter | None, hops: int) -> None:
    """Attach the limiter. It is read from ``app.state.limiter`` on every
    request so it can be swapped (tests) or disabled (None).

    Add this BEFORE the CORS middleware: the last middleware added is the
    outermost, and 429 responses need CORS headers to be readable by the
    browser."""
    app.state.limiter = limiter

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        active: RateLimiter | None = app.state.limiter
        if (
            active is None
            or request.method == "OPTIONS"
            or request.url.path in EXEMPT_PATHS
        ):
            return await call_next(request)
        who = client_ip(request, hops)
        decision = active.check(who)
        if decision.allowed:
            return await call_next(request)
        log.warning(
            "rate limit (%s) hit by %s on %s", decision.scope, who, request.url.path
        )
        detail = (
            "The service is at its free-tier capacity right now."
            if decision.scope == "global"
            else "Too many requests from your connection."
        )
        return JSONResponse(
            {"detail": f"{detail} Try again in {decision.retry_after} seconds."},
            status_code=429,
            headers={"Retry-After": str(decision.retry_after)},
        )
