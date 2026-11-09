"""FastAPI application: read API over the golf warehouse.

Run (from ``backend/``):  uvicorn app.main:app --reload
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

from app.config import get_settings
from app.routers import compare, health, pipeline, players, stats
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

API_PREFIX = "/api/v1"

app = FastAPI(
    title="Golf Stats API",
    version="0.1.0",
    description="Player and season statistics from the PGA Tour ETL warehouse.",
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
