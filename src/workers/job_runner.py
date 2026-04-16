"""Polling worker for analysis_jobs.

Claims the oldest queued job atomically and runs it, then polls again. Designed
as a standalone process — start it alongside the FastAPI API so the API only
enqueues and this process drains the queue.

    python -m src.workers.job_runner --poll-interval 1.5

Graceful shutdown on SIGINT / SIGTERM: finishes the current job before exiting.
"""

from __future__ import annotations

import argparse
import logging
import signal
import time
from typing import Callable

from src.services import brand_service


logger = logging.getLogger(__name__)


class _ShutdownFlag:
    def __init__(self) -> None:
        self.requested = False

    def request(self, *_args) -> None:
        self.requested = True
        logger.info("shutdown requested, will exit after current job")


def run(
    poll_interval: float = 1.5,
    worker_id: str | None = None,
    shutdown: _ShutdownFlag | None = None,
    claim: Callable[[str | None], dict | None] | None = None,
    runner: Callable[[dict], dict] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Poll for queued jobs and run them one at a time until shutdown."""
    shutdown = shutdown or _ShutdownFlag()
    claim = claim or brand_service.claim_next_job
    runner = runner or brand_service.run_claimed_job

    logger.info(
        "job worker started (poll=%.1fs, worker_id=%s)",
        poll_interval,
        worker_id or "default",
    )

    while not shutdown.requested:
        try:
            job = claim(worker_id)
        except Exception:
            logger.exception("claim failed, backing off")
            sleep(poll_interval)
            continue

        if not job:
            sleep(poll_interval)
            continue

        logger.info("claimed job %s (%s)", job["id"], job.get("url"))
        try:
            runner(job)
        except Exception:
            logger.exception("job %s crashed in runner", job["id"])

    logger.info("job worker stopped")


def _install_signal_handlers(flag: _ShutdownFlag) -> None:
    signal.signal(signal.SIGINT, flag.request)
    signal.signal(signal.SIGTERM, flag.request)


def main() -> None:
    parser = argparse.ArgumentParser(description="Brand3 analysis job worker")
    parser.add_argument("--poll-interval", type=float, default=1.5, help="Seconds between polls when idle")
    parser.add_argument("--worker-id", default=None, help="Label for this worker in job events")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    flag = _ShutdownFlag()
    _install_signal_handlers(flag)
    run(poll_interval=args.poll_interval, worker_id=args.worker_id, shutdown=flag)


if __name__ == "__main__":
    main()
