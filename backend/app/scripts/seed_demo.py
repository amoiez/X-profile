"""Seed demonstration analyses.

Runs the analysis pipeline (mock provider) for a handful of usernames so a
fresh deployment has example data to explore. Idempotent-ish: it simply adds
new jobs each run.

Usage:
    python -m app.scripts.seed_demo
"""

from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from app.database.base import Base
from app.database.session import AsyncSessionLocal, engine
from app.services import analysis_runner, job_service

configure_logging()
logger = get_logger("seed")

# A mix of archetypes and error states for demonstration.
DEMO_USERNAMES = ["news_bot", "sample_user", "coffee_lover", "empty_demo", "protected_demo"]


async def _ensure_schema() -> None:
    # Safe for local/dev SQLite; production uses Alembic migrations.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed() -> None:
    await _ensure_schema()
    for username in DEMO_USERNAMES:
        async with AsyncSessionLocal() as session:
            job = await job_service.create_job(
                session, username=username, post_limit=150, tz="UTC"
            )
            job_id = job.id
        await analysis_runner.run_job(job_id)
        async with AsyncSessionLocal() as session:
            job = await job_service.get_job(session, job_id)
            logger.info("seeded", username=username, status=job.status,
                        posts=job.actual_post_count, error=job.error_code)
    logger.info("seed_complete", count=len(DEMO_USERNAMES))


if __name__ == "__main__":
    asyncio.run(seed())
