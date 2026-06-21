"""Job orchestration helpers for analysis jobs."""

from __future__ import annotations

import json
from typing import Any, Callable, Type

from src.storage.sqlite_store import SQLiteStore


def _store(db_path: str) -> SQLiteStore:
    return SQLiteStore(db_path)


def enqueue_analysis_job(
    db_path: str,
    url: str,
    brand_name: str | None = None,
    use_llm: bool = True,
    use_social: bool = True,
) -> dict:
    store = _store(db_path)
    try:
        job_id = store.create_analysis_job(
            url=url,
            brand_name=brand_name,
            use_llm=use_llm,
            use_social=use_social,
        )
        payload = store.get_analysis_job(job_id)
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def get_analysis_job(db_path: str, job_id: int) -> dict:
    store = _store(db_path)
    try:
        job = store.get_analysis_job(job_id)
        if not job:
            raise ValueError(f"Analysis job {job_id} not found")
        print(json.dumps(job, indent=2))
        return job
    finally:
        store.close()


def list_analysis_jobs(
    db_path: str,
    brand_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    store = _store(db_path)
    try:
        jobs = store.list_analysis_jobs(brand_name=brand_name, status=status, limit=limit)
        print(json.dumps(jobs, indent=2))
        return jobs
    finally:
        store.close()


def execute_analysis_job(
    db_path: str,
    job_id: int,
    run_fn: Callable[..., dict[str, Any]],
    cancel_exc: Type[Exception],
) -> dict:
    """Atomically claim a queued job by id and run it to completion."""
    store = _store(db_path)
    try:
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
    finally:
        store.close()

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
        store = _store(db_path)
        try:
            store.complete_analysis_job(job_id, result.get("run_id"), result)
            completed = store.get_analysis_job(job_id)
            print(json.dumps(completed, indent=2))
            return completed
        finally:
            store.close()
    except cancel_exc as exc:
        store = _store(db_path)
        try:
            store.cancel_analysis_job(job_id, str(exc))
            cancelled = store.get_analysis_job(job_id)
            print(json.dumps(cancelled, indent=2))
            return cancelled
        finally:
            store.close()
    except Exception as exc:
        store = _store(db_path)
        try:
            store.fail_analysis_job(job_id, str(exc))
            failed = store.get_analysis_job(job_id)
            print(json.dumps(failed, indent=2))
            return failed
        finally:
            store.close()


def claim_next_job(db_path: str, worker_id: str | None = None) -> dict | None:
    """Claim the oldest queued job for a worker. Returns None if nothing pending."""
    store = _store(db_path)
    try:
        return store.claim_pending_job(worker_id=worker_id)
    finally:
        store.close()


def cancel_analysis_job(db_path: str, job_id: int) -> dict:
    store = _store(db_path)
    try:
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
    finally:
        store.close()


def retry_analysis_job(db_path: str, job_id: int) -> dict:
    store = _store(db_path)
    try:
        job = store.get_analysis_job(job_id)
        if not job:
            raise ValueError(f"Analysis job {job_id} not found")
        if job["status"] not in {"failed", "cancelled"}:
            raise ValueError(f"Analysis job {job_id} is not retryable from status {job['status']}")
        store.requeue_analysis_job(job_id)
        queued = store.get_analysis_job(job_id)
        print(json.dumps(queued, indent=2))
        return queued
    finally:
        store.close()
