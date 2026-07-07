"""Public Brand3 Scanner API routes."""

from __future__ import annotations

import asyncio
import json
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
_DEBUG_REDACTED_KEYS = {
    "html",
    "raw_html",
    "rendered_html",
    "markdown_content",
    "markdown",
    "content",
    "screenshot_base64",
    "image_base64",
    "bytes",
}
_DEBUG_MAX_STRING_LENGTH = 400


@router.get("/scanner-api/openapi.json", include_in_schema=False)
async def scanner_api_openapi() -> JSONResponse:
    return JSONResponse(scanner_openapi_spec())


def _api_scan_status(row: dict, *, sv9_scan_id: int | None = None, lang: _Lang = "es") -> dict:
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
        sv9_scan_id=sv9_scan_id,
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


def _sv9_scan_id_for_source_run(source_run_id: object) -> int | None:
    try:
        run_id = int(source_run_id)
    except (TypeError, ValueError):
        return None
    if run_id <= 0:
        return None
    try:
        from src.sv9.rubric import RUBRIC_VERSION
        from src.sv9.store import Sv9Store

        store = Sv9Store(BRAND3_DB_PATH)
        try:
            scan = store.get_scan_for_run(run_id, rubric_version=RUBRIC_VERSION)
        finally:
            store.close()
    except Exception:
        return None
    if not scan:
        return None
    try:
        return int(scan["id"])
    except (KeyError, TypeError, ValueError):
        return None


async def _sv9_scan_id_for_row(row: dict) -> int | None:
    source_run_id = row.get("source_run_id")
    if not source_run_id:
        return None
    return await asyncio.to_thread(_sv9_scan_id_for_source_run, source_run_id)


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


def _sanitize_debug_value(value):
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            key_str = str(key)
            if key_str in _DEBUG_REDACTED_KEYS:
                text = str(item or "")
                sanitized[key_str] = {
                    "_redacted": True,
                    "length": len(text),
                }
                continue
            sanitized[key_str] = _sanitize_debug_value(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_debug_value(item) for item in value[:50]]
    if isinstance(value, str):
        if len(value) <= _DEBUG_MAX_STRING_LENGTH:
            return value
        return {
            "_truncated": True,
            "length": len(value),
            "preview": value[:_DEBUG_MAX_STRING_LENGTH],
        }
    return value


def _debug_snapshot_payload(snapshot: dict) -> dict:
    from src.visual_signature.acquisition_contract import is_visual_acquisition_source

    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    raw_inputs = snapshot.get("raw_inputs") if isinstance(snapshot.get("raw_inputs"), list) else []
    features = snapshot.get("features") if isinstance(snapshot.get("features"), list) else []
    evidence_items = (
        snapshot.get("evidence_items") if isinstance(snapshot.get("evidence_items"), list) else []
    )
    visual_signature_payload = None
    for item in reversed(raw_inputs):
        if is_visual_acquisition_source(item.get("source")) and isinstance(item.get("payload"), dict):
            visual_signature_payload = item.get("payload")
            break
    return {
        "raw_inputs": [
            {
                "source": str(item.get("source") or ""),
                "created_at": item.get("created_at"),
                "payload": _sanitize_debug_value(item.get("payload") if isinstance(item.get("payload"), dict) else {}),
            }
            for item in raw_inputs
            if isinstance(item, dict)
        ],
        "visual_acquisition_payload": _sanitize_debug_value(
            visual_signature_payload if isinstance(visual_signature_payload, dict) else {}
        ),
        "visual_signature_payload": _sanitize_debug_value(
            visual_signature_payload if isinstance(visual_signature_payload, dict) else {}
        ),
        "features": _sanitize_debug_value(features[:200]),
        "evidence_items": _sanitize_debug_value(evidence_items[:200]),
        "counts": {
            "raw_inputs": len(raw_inputs),
            "features": len(features),
            "evidence_items": len(evidence_items),
        },
        "run_audit_keys": sorted((run.get("audit") or {}).keys()) if isinstance(run.get("audit"), dict) else [],
    }


def _full_debug_snapshot_payload(snapshot: dict) -> dict:
    return snapshot if isinstance(snapshot, dict) else {}


def _scanner_result_debug_payload(row: dict, model: dict[str, object]) -> dict:
    raw_payload = {}
    try:
        candidate = json.loads(str(row.get("raw_payload") or "{}"))
        if isinstance(candidate, dict):
            raw_payload = candidate
    except Exception:
        raw_payload = {}
    payload = model.get("payload") if isinstance(model.get("payload"), dict) else {}
    return {
        "raw_payload": _sanitize_debug_value(raw_payload),
        "normalized_payload": _sanitize_debug_value(payload if isinstance(payload, dict) else {}),
    }


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
    return _api_scan_status(row, sv9_scan_id=await _sv9_scan_id_for_row(row), lang=payload.lang)


@router.get("/api/v1/scanner/{scan_id}", response_model=None)
async def scanner_api_status(request: Request, scan_id: int, lang: _Lang = Query("es")) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = await _scan_row_or_error_async(scan_id)
    if isinstance(row, JSONResponse):
        return row
    return _api_scan_status(row, sv9_scan_id=await _sv9_scan_id_for_row(row), lang=lang)


@router.get("/api/v1/scanner/{scan_id}/result", response_model=None)
async def scanner_api_result(
    request: Request,
    scan_id: int,
    lang: _Lang = Query("es"),
    full: bool = Query(False),
) -> dict | JSONResponse:
    auth_error = scanner_api_auth_error(request)
    if auth_error is not None:
        return auth_error
    row = await _ready_scan_row_or_error(scan_id, lang=lang)
    if isinstance(row, JSONResponse):
        return row
    model = magnetism_scan_model_from_row(row)
    metadata = scanner_result_metadata_model(model["payload"])
    response = scanner_result_payload(
        row,
        model,
        result_metadata=metadata,
        sv9_scan_id=await _sv9_scan_id_for_row(row),
        lang=lang,
    )
    if full:
        response["debug"] = _scanner_result_debug_payload(row, model)
    return response


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


@router.get("/api/v1/scanner/{scan_id}/audit-snapshot", response_model=None)
async def scanner_api_audit_snapshot(
    request: Request,
    scan_id: int,
    full: bool = Query(False),
) -> dict | JSONResponse:
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
        "debug": _full_debug_snapshot_payload(snapshot) if full else _debug_snapshot_payload(snapshot),
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
