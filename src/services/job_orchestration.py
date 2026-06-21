"""Job orchestration helpers for analysis jobs."""

from __future__ import annotations

import json
from typing import Any, Callable, Type

from src.storage.sqlite_store import SQLiteStore


def _store(db_path: str) -> SQLiteStore:
    return SQLiteStore(db_path)


def _with_store(db_path: str, action):
    store = _store(db_path)
    try:
        return action(store)
    finally:
        store.close()


def enqueue_analysis_job(
    db_path: str,
    url: str,
    brand_name: str | None = None,
    use_llm: bool = True,
    use_social: bool = True,
) -> dict:
    def _action(store: SQLiteStore) -> dict:
        job_id = store.create_analysis_job(
            url=url,
            brand_name=brand_name,
            use_llm=use_llm,
            use_social=use_social,
        )
        payload = store.get_analysis_job(job_id)
        print(json.dumps(payload, indent=2))
        return payload

    return _with_store(db_path, _action)


def get_analysis_job(db_path: str, job_id: int) -> dict:
    def _action(store: SQLiteStore) -> dict:
        job = store.get_analysis_job(job_id)
        if not job:
            raise ValueError(f"Analysis job {job_id} not found")
        print(json.dumps(job, indent=2))
        return job

    return _with_store(db_path, _action)


def list_analysis_jobs(
    db_path: str,
    brand_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    def _action(store: SQLiteStore) -> list[dict]:
        jobs = store.list_analysis_jobs(brand_name=brand_name, status=status, limit=limit)
        print(json.dumps(jobs, indent=2))
        return jobs

    return _with_store(db_path, _action)


def execute_analysis_job(
    db_path: str,
    job_id: int,
    run_fn: Callable[..., dict[str, Any]],
    cancel_exc: Type[Exception],
) -> dict:
    """Atomically claim a queued job by id and run it to completion."""
    def _action(store: SQLiteStore):
        existing = store.get_analysis_job(job_id)
        if not existing:
            raise ValueError(f"Analysis job {job_id} not found")
        if existing["status"] != "queued":
            return existing
        if existing.get("cancel_requested"):
            store.cancel_analysis_job(job_id)
            cancelled = store.get_analysis_job(job_id)
            print(json.dumps(cancelled, indent=2))
            return cancelled
        claimed = store.claim_pending_job(job_id=job_id)
        if not claimed:
            return store.get_analysis_job(job_id)
        return claimed

    claimed = _with_store(db_path, _action)
    if not claimed:
        return claimed
    return run_claimed_job(db_path, claimed, run_fn=run_fn, cancel_exc=cancel_exc)


def run_claimed_job(
    db_path: str,
    job: dict,
    run_fn: Callable[..., dict[str, Any]],
    cancel_exc: Type[Exception],
) -> dict:
    """Run the pipeline for a job already claimed (status='running')."""
    job_id = int(job["id"])

    def progress_cb(phase: str) -> None:
        progress_store = _store(db_path)
        try:
            progress_store.update_analysis_job_phase(job_id, phase)
        finally:
            progress_store.close()

    def cancel_check() -> bool:
        progress_store = _store(db_path)
        try:
            current = progress_store.get_analysis_job(job_id)
            return bool(current and (current.get("cancel_requested") or current.get("status") == "cancelled"))
        finally:
            progress_store.close()

    try:
        result = run_fn(
            job["url"],
            brand_name=job.get("brand_name"),
            use_llm=bool(job.get("use_llm")),
            use_social=bool(job.get("use_social")),
            progress_cb=progress_cb,
            cancel_check=cancel_check,
        )
        def _complete(store: SQLiteStore) -> dict:
            store.complete_analysis_job(job_id, result.get("run_id"), result)
            completed = store.get_analysis_job(job_id)
            print(json.dumps(completed, indent=2))
            return completed
        return _with_store(db_path, _complete)
    except cancel_exc as exc:
        def _cancel(store: SQLiteStore, reason: str = str(exc)) -> dict:
            store.cancel_analysis_job(job_id, reason)
            cancelled = store.get_analysis_job(job_id)
            print(json.dumps(cancelled, indent=2))
            return cancelled
        return _with_store(db_path, _cancel)
    except Exception as exc:
        def _fail(store: SQLiteStore, reason: str = str(exc)) -> dict:
            store.fail_analysis_job(job_id, reason)
            failed = store.get_analysis_job(job_id)
            print(json.dumps(failed, indent=2))
            return failed
        return _with_store(db_path, _fail)


def claim_next_job(db_path: str, worker_id: str | None = None) -> dict | None:
    """Claim the oldest queued job for a worker. Returns None if nothing pending."""
    return _with_store(db_path, lambda store: store.claim_pending_job(worker_id=worker_id))


def cancel_analysis_job(db_path: str, job_id: int) -> dict:
    def _action(store: SQLiteStore) -> dict:
        job = store.get_analysis_job(job_id)
        if not job:
            raise ValueError(f"Analysis job {job_id} not found")
        if job["status"] in {"done", "failed", "cancelled"}:
            print(json.dumps(job, indent=2))
            return job
        store.request_analysis_job_cancel(job_id)
        updated = store.get_analysis_job(job_id)
        print(json.dumps(updated, indent=2))
        return updated

    return _with_store(db_path, _action)


def retry_analysis_job(db_path: str, job_id: int) -> dict:
    def _action(store: SQLiteStore) -> dict:
        job = store.get_analysis_job(job_id)
        if not job:
            raise ValueError(f"Analysis job {job_id} not found")
        if job["status"] not in {"failed", "cancelled"}:
            raise ValueError(f"Analysis job {job_id} is not retryable from status {job['status']}")
        store.requeue_analysis_job(job_id)
        queued = store.get_analysis_job(job_id)
        print(json.dumps(queued, indent=2))
        return queued

    return _with_store(db_path, _action)
