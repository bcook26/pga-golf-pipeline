from settings import get_settings
from sqlalchemy.engine import URL, Engine, create_engine


def engine() -> Engine:
    """Build a SQLAlchemy engine from environment settings."""
    s = get_settings()
    url = URL.create(
        "postgresql+psycopg",
        username=s.db_user,
        password=s.db_password,
        host=s.db_host,
        port=s.db_port,
        database=s.db_name,
    )
    return create_engine(url, pool_pre_ping=True)
