"""Aggregate API v1 router.

Analysis routes are added in Milestone 2; health routes are available now.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)

# Analysis routes registered here in Milestone 2.
try:  # pragma: no cover - optional until M2 lands
    from app.api import analyses

    api_router.include_router(analyses.router)
except ImportError:
    pass
