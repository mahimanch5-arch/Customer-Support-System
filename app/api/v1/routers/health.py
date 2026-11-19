"""Service-level health/liveness (unauthenticated)."""
from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.db.session import ping

router = APIRouter(tags=["health"])


@router.get("/health", summary="Service health")
async def health() -> dict:
    db_ok = await ping()
    return {"status": "ok" if db_ok else "degraded", "version": __version__,
            "database": "up" if db_ok else "down"}


@router.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": "customer-support-api", "docs": "/docs", "health": "/health"}
