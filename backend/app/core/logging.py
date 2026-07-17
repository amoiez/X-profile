"""Structured JSON logging configuration.

Logs are emitted as JSON with a consistent set of fields (timestamp,
severity, service, request_id, job_id, error_code). Credentials and full
post bodies are never logged. A small redaction processor scrubs common
token-bearing keys defensively.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import settings

SERVICE_NAME = "xba-backend"

_SENSITIVE_KEYS = {
    "authorization",
    "bearer",
    "token",
    "x_api_bearer_token",
    "password",
    "password_hash",
    "access_token",
    "refresh_token",
    "secret",
    "jwt_secret_key",
    "app_secret_key",
}


def _redact_sensitive(_logger, _method, event_dict: dict) -> dict:
    """Redact any sensitive values that accidentally reach the logger."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict


def _add_service(_logger, _method, event_dict: dict) -> dict:
    event_dict.setdefault("service", SERVICE_NAME)
    return event_dict


def configure_logging() -> None:
    """Configure structlog + stdlib logging for JSON output."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_service,
            _redact_sensitive,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name or SERVICE_NAME)
