"""Health and readiness endpoints.

/health is a liveness probe (process is up).
/ready checks dependencies (database, Redis) and returns 503 if not ready.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.core.config import settings
from app.database.session import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "xba-backend"}


@router.get("/ready")
async def ready(response: Response) -> dict:
    checks: dict[str, str] = {}
    ok = True

    # Database connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001 - report unhealthy without leaking detail
        checks["database"] = "error"
        ok = False

    # Redis connectivity (optional; not fatal in mock/local without redis)
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        checks["redis"] = "ok"
    except Exception:  # noqa: BLE001
        checks["redis"] = "unavailable"
        # Redis is required for queue in production; treat as not-ready there.
        if settings.is_production:
            ok = False

    checks["provider"] = "mock" if settings.use_mock_provider else "x_api"
    if not ok:
        response.status_code = 503
    return {"status": "ready" if ok else "not_ready", "checks": checks}
