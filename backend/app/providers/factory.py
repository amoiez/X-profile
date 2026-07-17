"""Provider factory — selects mock or real provider based on config.

Falls back to the mock provider automatically when the real provider is
requested but no credentials are configured, so the application always runs.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.base import BaseXProvider
from app.providers.mock_x import MockXProvider

logger = get_logger("provider.factory")


def get_provider() -> BaseXProvider:
    if settings.use_mock_provider:
        if settings.x_provider == "x_api":
            logger.warning(
                "provider_fallback_to_mock",
                reason="x_api requested but no bearer token configured",
            )
        return MockXProvider()

    # Imported lazily so mock-only deployments never import httpx client setup.
    from app.providers.x_api import XApiProvider

    return XApiProvider()
