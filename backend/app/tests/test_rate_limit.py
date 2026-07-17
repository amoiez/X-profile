"""Rate-limit behavior test.

The global limiter is disabled in the test environment so the suite can run
freely; here we build a minimal app with an ENABLED limiter to verify slowapi
enforcement and the 429 error envelope mapping.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.errors import ErrorCode


def _build_app() -> FastAPI:
    limiter = Limiter(key_func=get_remote_address, enabled=True)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(RateLimitExceeded)
    async def _handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": {"code": ErrorCode.RATE_LIMITED.value,
                               "message": "Too many requests.", "request_id": None}},
        )

    @app.post("/limited")
    @limiter.limit("2/minute")
    async def limited(request: Request):
        return {"ok": True}

    return app


async def test_requests_are_rate_limited():
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        assert (await ac.post("/limited")).status_code == 200
        assert (await ac.post("/limited")).status_code == 200
        blocked = await ac.post("/limited")
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "RATE_LIMITED"
