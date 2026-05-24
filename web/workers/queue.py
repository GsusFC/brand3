"""Asyncio-backed analysis queue.

A single queue instance runs N worker loops (default 2). Each worker reads a
token from the queue, loads the `web_requests` row, calls the engine in a
thread, and updates the row. Crash-tolerance is handled by the database —
rows marked as ``running`` without a completion timestamp on startup are
flipped back to ``queued`` (see `AnalysisQueue.restart_in_flight`).
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from ..config import settings

log = logging.getLogger("brand3.web.queue")


# Test/DI hook — production code resolves the callable at runtime.
_run_analysis_override = None


def set_run_analysis_override(fn) -> None:
    """Patch the engine entrypoint (used by tests)."""
    global _run_analysis_override
    _run_analysis_override = fn


def _call_engine(url: str, progress_cb=None) -> dict:
    """Run the engine in a blocking call — always invoked via `to_thread`."""
    if _run_analysis_override is not None:
        signature = inspect.signature(_run_analysis_override)
        if "progress_cb" in signature.parameters:
            return _run_analysis_override(url, progress_cb=progress_cb)
        return _run_analysis_override(url)
    from src.services.brand_service import run as brand_service_run
    return brand_service_run(
        url,
        use_social=True,
        use_llm=True,
        progress_cb=progress_cb,
    )


def _db_path() -> Path:
    from src.config import BRAND3_DB_PATH
    return Path(BRAND3_DB_PATH)


@dataclass
class QueueStats:
    queued: int = 0
    running: int = 0


class AnalysisQueue:
    """Asyncio task pool with SQLite-backed status rows."""

    def __init__(self, max_concurrent: int | None = None):
        self.max_concurrent = max_concurrent or settings.max_concurrent_analyses
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._running: set[str] = set()
        self._stop = asyncio.Event()

    async def enqueue(self, token: str) -> None:
        await self._queue.put(token)

    def stats(self) -> QueueStats:
        return QueueStats(queued=self._queue.qsize(), running=len(self._running))

    async def start(self) -> None:
        self._stop.clear()
        self.restart_in_flight()
        for i in range(self.max_concurrent):
            task = asyncio.create_task(self._worker_loop(i), name=f"brand3-worker-{i}")
            self._workers.append(task)
        log.info("queue started — workers=%d", self.max_concurrent)

    async def stop(self) -> None:
        self._stop.set()
        for task in self._workers:
            task.cancel()
        for task in self._workers:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._workers.clear()
        log.info("queue stopped")

    def restart_in_flight(self) -> None:
        """Reset `running` rows to `queued` after an ungraceful restart."""
        with sqlite3.connect(str(_db_path())) as conn:
            cur = conn.execute(
                "UPDATE web_requests SET status='queued', phase='queued', "
                "phase_updated_at=NULL, started_at=NULL "
                "WHERE status='running'"
            )
            if cur.rowcount:
                log.warning("reset %d stale running rows back to queued", cur.rowcount)
            tokens = [
                row[0]
                for row in conn.execute(
                    "SELECT token FROM web_requests WHERE status='queued' "
                    "ORDER BY created_at ASC"
                ).fetchall()
            ]
            conn.commit()
        for token in tokens:
            self._queue.put_nowait(token)

    async def _worker_loop(self, worker_id: int) -> None:
        log.info("worker[%d] online", worker_id)
        while not self._stop.is_set():
            try:
                token = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            self._running.add(token)
            try:
                await self._process(token)
            except Exception:
                log.exception("worker[%d] crashed on token=%s", worker_id, token)
            finally:
                self._running.discard(token)
                self._queue.task_done()

    async def _process(self, token: str) -> None:
        request = _load_request(token)
        if request is None:
            log.warning("token not found: %s", token)
            return

        _set_status(
            token,
            status="running",
            phase="collecting",
            phase_updated_at=_now(),
            started_at=_now(),
        )
        log.info("analysis started token=%s url=%s", token, request["url"])

        def progress_cb(phase: str) -> None:
            _set_status(token, phase=phase, phase_updated_at=_now())

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_call_engine, request["url"], progress_cb),
                timeout=settings.analysis_timeout_seconds,
            )
        except asyncio.TimeoutError:
            _set_status(token, status="failed",
                        phase="failed",
                        phase_updated_at=_now(),
                        completed_at=_now(),
                        error_message="timeout")
            log.warning("analysis timeout token=%s", token)
            return
        except Exception as exc:  # noqa: BLE001
            _set_status(token, status="failed",
                        phase="failed",
                        phase_updated_at=_now(),
                        completed_at=_now(),
                        error_message=str(exc)[:500])
            log.exception("analysis failed token=%s", token)
            return

        run_id = int(result.get("run_id") or 0) or None
        _set_status(
            token,
            status="ready",
            phase="ready",
            phase_updated_at=_now(),
            completed_at=_now(),
            run_id=run_id,
        )
        log.info("analysis ready token=%s run_id=%s", token, run_id)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def _load_request(token: str) -> dict | None:
    with sqlite3.connect(str(_db_path())) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM web_requests WHERE token = ?", (token,)
        ).fetchone()
    return dict(row) if row else None


def _set_status(token: str, **columns) -> None:
    if not columns:
        return
    assignments = ", ".join(f"{k} = ?" for k in columns)
    values = list(columns.values()) + [token]
    with sqlite3.connect(str(_db_path())) as conn:
        conn.execute(
            f"UPDATE web_requests SET {assignments} WHERE token = ?",
            values,
        )
        conn.commit()


# Module-level singleton — the FastAPI lifespan owns start/stop.
queue: AnalysisQueue | None = None


def get_queue() -> AnalysisQueue:
    global queue
    if queue is None:
        queue = AnalysisQueue()
    return queue
