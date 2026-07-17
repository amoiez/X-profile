"""Rate limiter (slowapi).

Disabled automatically in the test environment so the suite can exercise the
API freely; enabled in development/production with per-IP limits.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.app_env != "test",
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    headers_enabled=True,
)

ANALYSIS_LIMIT = f"{settings.analysis_rate_limit_per_hour}/hour"
