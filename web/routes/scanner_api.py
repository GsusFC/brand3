"""Public Brand3 Scanner API routes."""

from __future__ import annotations

import asyncio
import secrets
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from src.config import BRAND3_DB_PATH
from src.features.magnetism.client_tldr_v2 import build_client_tldr_v2
from src.reports.dossier import build_brand_dossier
from src.scoring.provenance import build_score_provenance_report
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
    scanner_failure_diagnostics_from_row,
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


def _load_run_summary(run_id: int) -> dict | None:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        return store.get_run_summary(run_id)
    finally:
        store.close()


class _ReportReadAnalyzer:
    """Keep API strategic-reading context reads deterministic and side-effect free."""

    def _call(self, *args, **kwargs) -> str:
        return ""

    def _call_json(self, *args, **kwargs) -> dict:
        return {}


_REPORT_READ_ANALYZER = _ReportReadAnalyzer()


@router.get("/scanner-api/openapi.json", include_in_schema=False)
async def scanner_api_openapi() -> JSONResponse:
    return JSONResponse(scanner_openapi_spec())


def _api_scan_status(row: dict, *, lang: _Lang = "es") -> dict:
    phase = _magnetism_phase(row)
    readiness = scanner_readiness_from_row(row)
    scan_mode = scanner_scan_mode_from_row(row)
    failure_diagnostics = scanner_failure_diagnostics_from_row(row)
    return scanner_status_payload(
        row,
        phase=phase,
        readiness=readiness,
        scan_mode=scan_mode,
        failure_diagnostics=failure_diagnostics,
        lang=lang,
    )


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


async def _scan_row_or_error_async(scan_id: int) -> dict | JSONResponse:
    row = await asyncio.to_thread(get_magnetism_scan, scan_id)
    if row is None:
        return _scan_not_found(scan_id)
    return row


async def _ready_scan_row_or_error(scan_id: int, *, lang: _Lang = "es") -> dict | JSONResponse:
    row = await _scan_row_or_error_async(scan_id)
    if isinstance(row, JSONResponse):
        return row
    if row.get("status") != "ready":
        return _scan_not_ready(row, lang=lang)
    return row


def _report_translation_payload(store: SQLiteStore, run_id: int, lang: _Lang) -> dict | None:
    if lang == "en":
        return None
    try:
        return store.get_report_translation(run_id, lang)
    except Exception:
        return None


def _load_run_snapshot(run_id: int) -> dict | None:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        return store.get_run_snapshot(run_id)
    finally:
        store.close()


def _load_strategic_read_context(run_id: int, lang: _Lang) -> tuple[dict | None, dict | None, dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
        narrative_payload = _report_translation_payload(store, run_id, lang)
        score_provenance = build_score_provenance_report(store, run_id)
        return snapshot, narrative_payload, score_provenance
    finally:
        store.close()


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
        run = await asyncio.to_thread(_load_run_summary, int(audit_run_id))
        if run is None:
            return scanner_api_error_response(
                404,
                code="audit_run_not_found",
                message=f"Brand Audit run #{audit_run_id} not found.",
            )
        scan_id = await asyncio.to_thread(
            insert_magnetism_job,
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
        scan_id = await asyncio.to_thread(
            insert_magnetism_job,
            token=token,
            brand_name=slug_from_url(result),
            url=result,
            input_type="url",
            input_value=result,
        )

    await get_queue().enqueue_magnetism(token)
    row = await asyncio.to_thread(get_magnetism_scan, scan_id)
    row = row or {"id": scan_id, "status": "queued", "phase": "queued", "token": token}
    return _api_scan_status(row, lang=payload.lang)


@router.get("/api/v1/scanner/{scan_id}", response_model=None)
async def scanner_api_status(request: Request, scan_id: int, lang: _Lang = Query("es")) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = await _scan_row_or_error_async(scan_id)
    if isinstance(row, JSONResponse):
        return row
    return _api_scan_status(row, lang=lang)


@router.get("/api/v1/scanner/{scan_id}/result", response_model=None)
async def scanner_api_result(request: Request, scan_id: int, lang: _Lang = Query("es")) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = await _ready_scan_row_or_error(scan_id, lang=lang)
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
    row = await _ready_scan_row_or_error(scan_id)
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
    row = await _ready_scan_row_or_error(scan_id)
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
    row = await _ready_scan_row_or_error(scan_id)
    if isinstance(row, JSONResponse):
        return row
    model = magnetism_scan_model_from_row(row)
    source_run_id = model.get("source_run_id")
    if not source_run_id:
        return {"id": scan_id, "available": False, "reason": "missing_source_run"}
    snapshot = await asyncio.to_thread(_load_run_snapshot, int(source_run_id))
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


@router.get("/api/v1/scanner/{scan_id}/strategic-reading", response_model=None)
async def scanner_api_strategic_reading(
    request: Request,
    scan_id: int,
    lang: _Lang = Query("es"),
) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = await _ready_scan_row_or_error(scan_id, lang=lang)
    if isinstance(row, JSONResponse):
        return row
    model = magnetism_scan_model_from_row(row)
    source_run_id = model.get("source_run_id")
    base_response = {
        "id": scan_id,
        "brand_name": model["brand_name"],
        "url": model["url"],
        "layer": "client_strategic_reading",
        "internal_name": "client_tldr_v2",
        "ui_url": f"/magnetism-scanner/scan/{scan_id}/client-tldr-v2?lang={lang}",
    }
    if not source_run_id:
        return {
            **base_response,
            "available": False,
            "source_run_id": None,
            "reason": "missing_source_run",
            "client_strategic_reading": None,
        }

    snapshot, narrative_payload, score_provenance = await asyncio.to_thread(
        _load_strategic_read_context,
        int(source_run_id),
        lang,
    )

    if snapshot is None:
        return {
            **base_response,
            "available": False,
            "source_run_id": int(source_run_id),
            "reason": "missing_snapshot",
            "client_strategic_reading": None,
        }

    report_context = build_brand_dossier(
        snapshot,
        theme="light",
        analyzer=_REPORT_READ_ANALYZER,
        narrative_payload=narrative_payload,
    )
    payload = model["payload"] if isinstance(model.get("payload"), dict) else {}
    current_tldr = payload.get("tldr_brand3") if isinstance(payload.get("tldr_brand3"), dict) else {}
    return {
        **base_response,
        "available": True,
        "source_run_id": int(source_run_id),
        "reason": None,
        "client_strategic_reading": build_client_tldr_v2(
            brand_name=str(model.get("brand_name") or "brand scan"),
            url=str(model.get("url") or ""),
            current_tldr=current_tldr,
            score_provenance=score_provenance,
            report_base=report_context,
            lang=lang,
            scanner_display_score=model.get("magnetism_score"),
        ),
    }
