from app.db import get_conn
from app.schemas import Health
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection, text

router = APIRouter(tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    """Process liveness only. Platform health checks should use this: it never
    touches the database, so polling it cannot keep a serverless database awake."""
    return {"status": "ok"}


@router.get("/health", response_model=Health)
def health(conn: Connection = Depends(get_conn)) -> Health:
    """Liveness + database connectivity."""
    try:
        conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return Health(status="ok", database="ok")
