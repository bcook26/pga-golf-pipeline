"""FastAPI application: read API over the golf warehouse.

Run (from ``backend/``):  uvicorn app.main:app --reload
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

from app.config import get_settings
from app.ratelimit import RateLimiter, install_rate_limit
from app.routers import compare, health, pipeline, players, stats, tournaments
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

API_PREFIX = "/api/v1"

app = FastAPI(
    title="Golf Stats API",
    version="0.1.0",
    description="Player and season statistics from the PGA Tour ETL warehouse.",
)

_s = get_settings()
_limits = (
    _s.rate_limit_per_minute,
    _s.rate_limit_per_hour,
    _s.rate_limit_global_per_hour,
)
# Added before CORS so that CORS is outermost and 429s stay readable by browsers.
install_rate_limit(
    app,
    RateLimiter(*_limits) if any(_limits) else None,
    _s.rate_limit_proxy_hops,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(players.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(compare.router, prefix=API_PREFIX)
app.include_router(pipeline.router, prefix=API_PREFIX)
app.include_router(tournaments.router, prefix=API_PREFIX)
