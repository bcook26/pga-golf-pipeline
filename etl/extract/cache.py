"""Redis-backed payload cache.

Caches *parsed* payloads (not whole HTML pages) so re-runs and backfills do
not re-hit the source. Degrades gracefully: if Redis is unreachable the cache
is disabled and every call goes straight to the producer.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

log = logging.getLogger(__name__)


class PayloadCache:
    def __init__(
        self,
        client: Any | None,
        ttl_seconds: int = 6 * 3600,
        namespace: str = "golf",
    ) -> None:
        self._client = client
        self._ttl = ttl_seconds
        self._ns = namespace
        self.hits = 0
        self.misses = 0

    @classmethod
    def from_url(cls, url: str, ttl_seconds: int, namespace: str = "golf"):
        try:
            import redis

            client = redis.Redis.from_url(url, socket_connect_timeout=2)
            client.ping()
        except Exception as exc:  # noqa: BLE001 - any failure disables cache
            log.warning("Redis unavailable (%s); payload cache disabled", exc)
            client = None
        return cls(client, ttl_seconds, namespace)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def _key(self, key: str) -> str:
        return f"{self._ns}:{key}"

    def get_or_set(
        self,
        key: str,
        producer: Callable[[], Any],
        ttl_seconds: int | None = None,
    ) -> Any:
        """Return cached value for ``key`` or compute, store and return it.

        ``None`` results are cached too (stored in an envelope) so players
        with no stats are not re-fetched on every run.
        """
        full_key = self._key(key)
        if self._client is not None:
            try:
                raw = self._client.get(full_key)
                if raw is not None:
                    self.hits += 1
                    return json.loads(raw)["v"]
            except Exception as exc:  # noqa: BLE001
                log.warning("Cache read failed for %s: %s", full_key, exc)

        self.misses += 1
        value = producer()

        if self._client is not None:
            try:
                self._client.setex(
                    full_key,
                    ttl_seconds or self._ttl,
                    json.dumps({"v": value}),
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("Cache write failed for %s: %s", full_key, exc)
        return value
