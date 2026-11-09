"""Central runtime configuration, read from environment variables / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    # Postgres
    db_user: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str
    # Redis payload cache
    redis_url: str
    cache_ttl_seconds: int
    # Polite scraping
    requests_per_second: float
    max_retries: int
    request_timeout: float
    user_agent: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        # ETL_DB_* are project-specific so they cannot collide with generic
        # DB_* variables other tools/projects may define in the same .env.
        db_user=os.getenv("ETL_DB_USER", "postgres"),
        db_password=os.getenv("ETL_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
        db_host=os.getenv("ETL_DB_HOST", "localhost"),
        db_port=_env_int("ETL_DB_PORT", 5433),
        db_name=os.getenv("ETL_DB_NAME", "ADHOC_GOLF"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        cache_ttl_seconds=_env_int("CACHE_TTL_SECONDS", 6 * 3600),
        requests_per_second=_env_float("REQUESTS_PER_SECOND", 2.0),
        max_retries=_env_int("MAX_RETRIES", 4),
        request_timeout=_env_float("REQUEST_TIMEOUT", 30.0),
        user_agent=os.getenv(
            "SCRAPER_USER_AGENT",
            "golf-etl-portfolio-project/0.1 (+personal, non-commercial)",
        ),
    )
