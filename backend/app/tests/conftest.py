"""Shared test fixtures.

Configures a file-based SQLite test database BEFORE any app module imports
(so the app engine and session factory bind to it), then creates the schema.
"""

from __future__ import annotations

import os
import pathlib

# Must be set before importing app modules that read settings at import time.
_TEST_DB = pathlib.Path(__file__).parent / "_test.db"
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}")
os.environ.setdefault("X_PROVIDER", "mock")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "REPORT_STORAGE_PATH", str((pathlib.Path(__file__).parent / "_reports").as_posix())
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.database.base import Base  # noqa: E402
from app.database.session import engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_db_file():
    yield
    try:
        _TEST_DB.unlink(missing_ok=True)
    except OSError:
        pass
