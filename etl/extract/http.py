"""HTTP client with rate limiting and retries."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe limiter spacing calls at least ``1/rps`` seconds apart."""

    def __init__(
        self,
        requests_per_second: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self._interval = 1.0 / requests_per_second
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next_slot = 0.0

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self._interval
        delay = slot - now
        if delay > 0:
            self._sleep(delay)


class PoliteClient:
    """requests.Session wrapper: rate limited, retries 429/5xx with backoff
    (honouring Retry-After), identifies itself with a User-Agent."""

    def __init__(
        self,
        requests_per_second: float = 2.0,
        max_retries: int = 4,
        timeout: float = 30.0,
        user_agent: str = "golf-etl/0.1",
        limiter: RateLimiter | None = None,
    ) -> None:
        self._limiter = limiter or RateLimiter(requests_per_second)
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers["User-Agent"] = user_agent
        retry = Retry(
            total=max_retries,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "POST"),  # GraphQL reads are idempotent
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def get_text(self, url: str) -> str:
        self._limiter.wait()
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        return response.text

    def post_json(
        self, url: str, payload: dict, headers: dict[str, str] | None = None
    ) -> dict:
        self._limiter.wait()
        response = self._session.post(
            url, json=payload, headers=headers, timeout=self._timeout
        )
        response.raise_for_status()
        return response.json()
