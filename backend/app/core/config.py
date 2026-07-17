"""Application configuration loaded from environment variables.

All settings are read from the environment (or a local `.env` file during
development). Secrets are never hard-coded. See `.env.example` for the full
list of supported variables.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_env: Literal["development", "production", "test"] = "development"
    app_secret_key: str = "change-me"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- X provider ---
    x_provider: Literal["mock", "x_api"] = "mock"
    x_api_bearer_token: str = ""
    x_api_base_url: str = "https://api.twitter.com/2"
    x_default_post_limit: int = 200
    x_max_post_limit: int = 500
    x_cache_ttl_seconds: int = 3600
    x_request_timeout_seconds: int = 15
    x_max_retries: int = 3

    # --- Auth ---
    jwt_secret_key: str = "change-me-jwt"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- Reports ---
    report_storage_path: str = "./reports_storage"

    # --- Analysis ---
    low_confidence_post_threshold: int = 10
    default_timezone: str = "UTC"

    # --- Observability ---
    log_level: str = "INFO"
    sentry_dsn: str = ""

    # --- Rate limiting ---
    rate_limit_per_minute: int = 30
    analysis_rate_limit_per_hour: int = 20

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def use_mock_provider(self) -> bool:
        # Fall back to mock automatically if a real provider was requested
        # but no credentials are configured, so the app always runs.
        if self.x_provider == "x_api" and not self.x_api_bearer_token:
            return True
        return self.x_provider == "mock"

    # Alembic / sync tooling needs a non-async URL.
    @property
    def sync_database_url(self) -> str:
        return (
            self.database_url.replace("+asyncpg", "")
            .replace("+aiosqlite", "")
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
