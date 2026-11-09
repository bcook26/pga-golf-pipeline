"""API configuration (same ETL_DB_* variables as the ETL; see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass(frozen=True)
class Settings:
    db_user: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str
    cors_origins: list[str]
    database_url: str | None = None  # e.g. Neon; overrides the ETL_DB_* parts
    db_sslmode: str | None = None
    # Rate limiting (0 disables a limit; all 0 turns the limiter off)
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 600
    rate_limit_global_per_hour: int = 3000
    rate_limit_proxy_hops: int = 0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    return Settings(
        db_user=os.getenv("ETL_DB_USER", "postgres"),
        db_password=os.getenv("ETL_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
        db_host=os.getenv("ETL_DB_HOST", "localhost"),
        db_port=int(os.getenv("ETL_DB_PORT", "5433")),
        db_name=os.getenv("ETL_DB_NAME", "ADHOC_GOLF"),
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        database_url=os.getenv("DATABASE_URL") or None,
        db_sslmode=os.getenv("ETL_DB_SSLMODE") or None,
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        rate_limit_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "600")),
        rate_limit_global_per_hour=int(os.getenv("RATE_LIMIT_GLOBAL_PER_HOUR", "3000")),
        rate_limit_proxy_hops=int(os.getenv("RATE_LIMIT_PROXY_HOPS", "0")),
    )
