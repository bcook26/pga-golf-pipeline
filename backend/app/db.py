"""Read-only database access for the API."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from app.config import get_settings
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.engine import URL, make_url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    s = get_settings()
    if s.database_url:
        # Hosted databases (Neon, ...) hand out one URL; force the psycopg 3 driver.
        url = make_url(s.database_url).set(drivername="postgresql+psycopg")
    else:
        url = URL.create(
            "postgresql+psycopg",
            username=s.db_user,
            password=s.db_password,
            host=s.db_host,
            port=s.db_port,
            database=s.db_name,
            query={"sslmode": s.db_sslmode} if s.db_sslmode else {},
        )
    engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
    # The API only reads; make the database enforce it.
    return engine.execution_options(postgresql_readonly=True)


def get_conn() -> Iterator[Connection]:
    """FastAPI dependency: one connection per request."""
    with get_engine().connect() as conn:
        yield conn
