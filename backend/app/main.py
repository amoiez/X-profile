"""FastAPI application entrypoint.

Wires up structured logging, CORS, security headers, request-id middleware,
consistent error handling, and the versioned API router.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    logger.info(
        "startup",
        env=settings.app_env,
        provider="mock" if settings.use_mock_provider else "x_api",
        version=__version__,
    )
    yield
    logger.info("shutdown")


app = FastAPI(
    title="X Behavior Analyzer",
    version=__version__,
    description=(
        "Behavior analysis system that reports observable public posting "
        "patterns only. It does not infer personality, intent, or identity."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id)
    try:
        response = await call_next(request)
    finally:
        structlog.contextvars.clear_contextvars()
    response.headers["X-Request-ID"] = request_id
    # Security headers (Nginx also sets these at the edge).
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def _error_response(code: str, message: str, status: int, request: Request) -> JSONResponse:
    request_id = request.headers.get("x-request-id")
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.info("app_error", error_code=exc.code.value)
    return _error_response(exc.code.value, exc.message, exc.http_status, request)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Surface AppError raised inside pydantic validators with its real code.
    for err in exc.errors():
        ctx_err = err.get("ctx", {}).get("error")
        if isinstance(ctx_err, AppError):
            return _error_response(ctx_err.code.value, ctx_err.message, 400, request)
    return _error_response(
        ErrorCode.VALIDATION_ERROR.value, "The request was invalid.", 422, request
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never leak internal traces in production.
    logger.error("unhandled_error", error=str(type(exc).__name__))
    return _error_response(
        ErrorCode.INTERNAL_ERROR.value, "An internal error occurred.", 500, request
    )


app.include_router(api_router)


@app.get("/")
async def root() -> dict:
    return {"service": "X Behavior Analyzer API", "version": __version__, "docs": "/docs"}
