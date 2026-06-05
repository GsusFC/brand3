"""Public Brand3 Scanner API routes."""

from __future__ import annotations

import secrets
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from src.config import BRAND3_DB_PATH
from src.storage.sqlite_store import SQLiteStore

from ..middleware.scanner_api_auth import (
    scanner_api_auth_error,
    scanner_api_error_response,
)
from ..scanner_api.models import (
    magnetism_scan_model_from_row,
    methodology_model,
    research_evidence_model,
    scanner_readiness_from_row,
    scanner_result_metadata_model,
    scanner_scan_mode_from_row,
)
from ..scanner_api.presenters import scanner_result_payload, scanner_status_payload
from ..scanner_api.schemas import ScannerCreateRequest, scanner_openapi_spec
from ..storage import get_magnetism_scan, insert_magnetism_job
from ..workers.queue import get_queue
from ..workers.slug import slug_from_url
from ..workers.url_validator import validate_url

router = APIRouter()

_Lang = Literal["es", "en"]


@router.get("/scanner-api/openapi.json", include_in_schema=False)
async def scanner_api_openapi() -> JSONResponse:
    return JSONResponse(scanner_openapi_spec())


def _api_scan_status(row: dict, *, lang: _Lang = "es") -> dict:
    phase = _magnetism_phase(row)
    readiness = scanner_readiness_from_row(row)
    scan_mode = scanner_scan_mode_from_row(row)
    return scanner_status_payload(row, phase=phase, readiness=readiness, scan_mode=scan_mode, lang=lang)


def _magnetism_phase(row: dict) -> str:
    phase = row.get("phase") or row.get("status") or "queued"
    if row.get("status") == "queued":
        return "queued"
    if row.get("status") == "failed":
        return "failed"
    if row.get("status") == "ready":
        return "ready"
    return str(phase)


def _scan_not_found(scan_id: int) -> JSONResponse:
    return scanner_api_error_response(
        404,
        code="scan_not_found",
        message=f"Magnetism scan #{scan_id} not found.",
    )


def _scan_not_ready(row: dict, *, lang: _Lang = "es") -> JSONResponse:
    return scanner_api_error_response(
        409,
        code="scan_not_ready",
        message="Scanner result is not ready.",
        status=_api_scan_status(row, lang=lang),
    )


def _scan_row_or_error(scan_id: int) -> dict | JSONResponse:
    row = get_magnetism_scan(scan_id)
    if row is None:
        return _scan_not_found(scan_id)
    return row


def _ready_scan_row_or_error(scan_id: int, *, lang: _Lang = "es") -> dict | JSONResponse:
    row = _scan_row_or_error(scan_id)
    if isinstance(row, JSONResponse):
        return row
    if row.get("status") != "ready":
        return _scan_not_ready(row, lang=lang)
    return row


@router.post("/api/v1/scanner", status_code=202, response_model=None)
async def scanner_api_create(request: Request, payload: ScannerCreateRequest) -> dict | JSONResponse:
    """Queue a complete Brand3 Scanner run from URL or an existing Brand Audit run."""
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    url_val = (payload.url or "").strip()
    audit_run_id = payload.audit_run_id
    if bool(url_val) == (audit_run_id is not None):
        return scanner_api_error_response(
            400,
            code="invalid_scanner_create_request",
            message="Provide exactly one of url or audit_run_id.",
        )

    token = secrets.token_urlsafe(12)
    if audit_run_id:
        store = SQLiteStore(BRAND3_DB_PATH)
        try:
            snapshot = store.get_run_snapshot(int(audit_run_id))
        finally:
            store.close()
        if snapshot is None:
            return scanner_api_error_response(
                404,
                code="audit_run_not_found",
                message=f"Brand Audit run #{audit_run_id} not found.",
            )
        run = snapshot.get("run") or {}
        scan_id = insert_magnetism_job(
            token=token,
            brand_name=str(run.get("brand_name") or f"Brand Audit run #{audit_run_id}"),
            url=str(run.get("url") or "Brand Audit snapshot"),
            input_type="audit_run",
            input_value=str(audit_run_id),
            source_run_id=int(audit_run_id),
        )
    else:
        valid, result = validate_url(url_val)
        if not valid:
            return scanner_api_error_response(
                400,
                code="url_rejected",
                message=f"URL rejected: {result}",
            )
        scan_id = insert_magnetism_job(
            token=token,
            brand_name=slug_from_url(result),
            url=result,
            input_type="url",
            input_value=result,
        )

    await get_queue().enqueue_magnetism(token)
    row = get_magnetism_scan(scan_id) or {"id": scan_id, "status": "queued", "phase": "queued", "token": token}
    return _api_scan_status(row, lang=payload.lang)


@router.get("/api/v1/scanner/{scan_id}", response_model=None)
async def scanner_api_status(request: Request, scan_id: int, lang: _Lang = Query("es")) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = _scan_row_or_error(scan_id)
    if isinstance(row, JSONResponse):
        return row
    return _api_scan_status(row, lang=lang)


@router.get("/api/v1/scanner/{scan_id}/result", response_model=None)
async def scanner_api_result(request: Request, scan_id: int, lang: _Lang = Query("es")) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = _ready_scan_row_or_error(scan_id, lang=lang)
    if isinstance(row, JSONResponse):
        return row
    model = magnetism_scan_model_from_row(row)
    metadata = scanner_result_metadata_model(model["payload"])
    return scanner_result_payload(row, model, result_metadata=metadata, lang=lang)


@router.get("/api/v1/scanner/{scan_id}/evidence", response_model=None)
async def scanner_api_evidence(request: Request, scan_id: int) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = _ready_scan_row_or_error(scan_id)
    if isinstance(row, JSONResponse):
        return row
    model = magnetism_scan_model_from_row(row)
    return {
        "id": model["id"],
        "brand_name": model["brand_name"],
        "evidence": research_evidence_model(model["payload"]),
    }


@router.get("/api/v1/scanner/{scan_id}/methodology", response_model=None)
async def scanner_api_methodology(request: Request, scan_id: int) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = _ready_scan_row_or_error(scan_id)
    if isinstance(row, JSONResponse):
        return row
    model = magnetism_scan_model_from_row(row)
    return {
        "id": model["id"],
        "brand_name": model["brand_name"],
        "methodology": methodology_model(model["payload"]),
    }


@router.get("/api/v1/scanner/{scan_id}/audit", response_model=None)
async def scanner_api_audit(request: Request, scan_id: int) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = _ready_scan_row_or_error(scan_id)
    if isinstance(row, JSONResponse):
        return row
    model = magnetism_scan_model_from_row(row)
    source_run_id = model.get("source_run_id")
    if not source_run_id:
        return {"id": scan_id, "available": False, "reason": "missing_source_run"}
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(int(source_run_id))
    finally:
        store.close()
    if snapshot is None:
        return scanner_api_error_response(
            404,
            code="audit_run_not_found",
            message=f"Brand Audit run #{source_run_id} not found.",
        )
    run = snapshot.get("run") or {}
    return {
        "id": scan_id,
        "available": True,
        "source_run_id": int(source_run_id),
        "run": {
            "id": run.get("id"),
            "brand_name": run.get("brand_name"),
            "url": run.get("url"),
            "composite_score": run.get("composite_score"),
            "completed_at": run.get("completed_at"),
        },
        "audit": run.get("audit") if isinstance(run.get("audit"), dict) else {},
    }
