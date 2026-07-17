"""Worker entrypoint.

Consumes analysis job ids from the Redis queue and runs the analysis pipeline.
Uses a blocking pop with a timeout so it shuts down promptly on signals.

If Redis is unavailable the API falls back to inline execution, so this worker
is required only for the production/queued path.
"""

from __future__ import annotations

import asyncio
import signal

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.services.analysis_runner import run_job
from app.services.queue import JOB_QUEUE_KEY

configure_logging()
logger = get_logger("worker")

_shutdown = asyncio.Event()


def _handle_signal(*_args) -> None:
    _shutdown.set()


async def _consume() -> None:
    import redis.asyncio as aioredis

    client = aioredis.from_url(settings.redis_url)
    logger.info("worker_started", queue=JOB_QUEUE_KEY)
    while not _shutdown.is_set():
        try:
            item = await client.brpop([JOB_QUEUE_KEY], timeout=2)
        except Exception as exc:  # noqa: BLE001 - keep worker alive on redis blips
            logger.error("worker_redis_error", error=type(exc).__name__)
            await asyncio.sleep(2)
            continue
        if item is None:
            continue
        _key, job_id = item
        job_id = job_id.decode() if isinstance(job_id, bytes) else job_id
        logger.info("worker_job_received", job_id=job_id)
        try:
            await run_job(job_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("worker_job_error", job_id=job_id, error=type(exc).__name__)
    await client.aclose()
    logger.info("worker_stopped")


async def main() -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:  # Windows
            signal.signal(sig, _handle_signal)

    # Retry connecting to Redis until it is available.
    while not _shutdown.is_set():
        try:
            await _consume()
            break
        except Exception as exc:  # noqa: BLE001
            logger.error("worker_start_error", error=type(exc).__name__)
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
