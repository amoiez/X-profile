"""Aggregate API v1 router.

Analysis routes are added in Milestone 2; health routes are available now.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import admin, analyses, auth, health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(analyses.router)
api_router.include_router(admin.router)
