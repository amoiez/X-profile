"""Worker entrypoint.

Milestone 1 provides a minimal, healthy worker loop so the container starts
cleanly. Milestone 2 replaces the body with real job consumption from Redis.
"""

from __future__ import annotations

import asyncio
import signal

from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("worker")

_shutdown = asyncio.Event()


def _handle_signal(*_args) -> None:
    _shutdown.set()


async def main() -> None:
    logger.info("worker_started", note="M1 idle loop; job processing added in M2")
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _handle_signal)
            except NotImplementedError:  # Windows
                signal.signal(sig, _handle_signal)
    except Exception:  # noqa: BLE001
        pass

    while not _shutdown.is_set():
        await asyncio.sleep(2)
    logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
