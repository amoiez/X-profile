"""Job queue abstraction.

Production: jobs are pushed to a Redis list and consumed by the `worker`
service. Local/dev without Redis: jobs run inline as an asyncio background task
so the app is fully functional in demo mode with no extra services.

`enqueue()` returns immediately in both modes; the API always responds with a
job id without waiting for analysis to finish.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("queue")

JOB_QUEUE_KEY = "xba:jobs"

# Keep references to inline tasks so they are not garbage-collected.
_inline_tasks: set[asyncio.Task] = set()


async def _redis_client():
    import redis.asyncio as aioredis

    client = aioredis.from_url(settings.redis_url)
    await client.ping()
    return client


async def enqueue(job_id: str) -> str:
    """Enqueue a job for processing. Returns 'redis' or 'inline'."""
    try:
        client = await _redis_client()
        await client.lpush(JOB_QUEUE_KEY, job_id)
        await client.aclose()
        logger.info("job_enqueued", job_id=job_id, mode="redis")
        return "redis"
    except Exception:  # noqa: BLE001 - Redis unavailable => inline fallback
        _run_inline(job_id)
        logger.info("job_enqueued", job_id=job_id, mode="inline")
        return "inline"


def _run_inline(job_id: str) -> None:
    # Imported here to avoid a circular import at module load.
    from app.services.analysis_runner import run_job

    task = asyncio.create_task(run_job(job_id))
    _inline_tasks.add(task)
    task.add_done_callback(_inline_tasks.discard)
