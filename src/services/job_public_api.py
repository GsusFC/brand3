"""Public job orchestration wrappers for Brand3."""

from __future__ import annotations

from src.config import BRAND3_DB_PATH
from src.services.analysis_exceptions import AnalysisJobCancelled
from src.services.job_orchestration import (
    cancel_analysis_job as _cancel_analysis_job,
    claim_next_job as _claim_next_job,
    enqueue_analysis_job as _enqueue_analysis_job,
    execute_analysis_job as _execute_analysis_job,
    get_analysis_job as _get_analysis_job,
    list_analysis_jobs as _list_analysis_jobs,
    run_claimed_job as _run_claimed_job,
    retry_analysis_job as _retry_analysis_job,
)
from src.services.run_workflow import run as _run_workflow


def _service():
    from src.services import brand_service as service

    return service


def enqueue_analysis_job(
    url: str,
    brand_name: str | None = None,
    use_llm: bool = True,
    use_social: bool = True,
) -> dict:
    service = _service()
    return _enqueue_analysis_job(
        getattr(service, "BRAND3_DB_PATH", BRAND3_DB_PATH),
        url,
        brand_name=brand_name,
        use_llm=use_llm,
        use_social=use_social,
    )


def get_analysis_job(job_id: int) -> dict:
    service = _service()
    return _get_analysis_job(getattr(service, "BRAND3_DB_PATH", BRAND3_DB_PATH), job_id)


def list_analysis_jobs(
    brand_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    service = _service()
    return _list_analysis_jobs(getattr(service, "BRAND3_DB_PATH", BRAND3_DB_PATH), brand_name=brand_name, status=status, limit=limit)


def execute_analysis_job(job_id: int) -> dict:
    service = _service()
    return _execute_analysis_job(
        getattr(service, "BRAND3_DB_PATH", BRAND3_DB_PATH),
        job_id,
        run_fn=getattr(service, "run", _run_workflow),
        cancel_exc=AnalysisJobCancelled,
    )


def run_claimed_job(job: dict) -> dict:
    service = _service()
    return _run_claimed_job(
        getattr(service, "BRAND3_DB_PATH", BRAND3_DB_PATH),
        job,
        run_fn=getattr(service, "run", _run_workflow),
        cancel_exc=AnalysisJobCancelled,
    )


def claim_next_job(worker_id: str | None = None) -> dict | None:
    service = _service()
    return _claim_next_job(getattr(service, "BRAND3_DB_PATH", BRAND3_DB_PATH), worker_id=worker_id)


def cancel_analysis_job(job_id: int) -> dict:
    service = _service()
    return _cancel_analysis_job(getattr(service, "BRAND3_DB_PATH", BRAND3_DB_PATH), job_id)


def retry_analysis_job(job_id: int) -> dict:
    service = _service()
    return _retry_analysis_job(getattr(service, "BRAND3_DB_PATH", BRAND3_DB_PATH), job_id)
