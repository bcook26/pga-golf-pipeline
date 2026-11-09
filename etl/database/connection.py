from settings import get_settings
from sqlalchemy.engine import URL, Engine, create_engine, make_url


def engine() -> Engine:
    """Build a SQLAlchemy engine from environment settings."""
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
    return create_engine(url, pool_pre_ping=True)
