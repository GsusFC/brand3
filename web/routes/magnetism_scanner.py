"""FastAPI routes for the Brand3 Magnetism Scanner."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH
from src.features.magnetism.extractor import MagnetismExtractor
from src.storage.sqlite_store import SQLiteStore

from ..storage import (
    get_magnetism_scan,
    get_magnetism_scan_by_token,
    insert_magnetism_job,
    insert_magnetism_scan,
    list_magnetism_scans,
)
from ..templates_env import templates
from ..workers.queue import get_queue
from ..workers.slug import slug_from_url
from ..workers.url_validator import validate_url

router = APIRouter()



@router.get("/magnetism-scanner")
async def magnetism_scanner_index(request: Request):
    """Render index page of Magnetism Scanner showing past analyses and inputs."""
    scans = list_magnetism_scans(limit=25)
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        audit_runs = store.list_runs(limit=12)
    finally:
        store.close()

    # Format dates nicely for template listing
    for scan in scans:
        try:
            dt = datetime.fromisoformat(scan["created_at"].replace("Z", "+00:00"))
            scan["formatted_date"] = dt.strftime("%b %d, %Y · %H:%M")
        except Exception:
            scan["formatted_date"] = scan["created_at"]

    return templates.TemplateResponse(
        request,
        "magnetism_scanner.html.j2",
        {
            "model": {
                "title": "Magnetism Scanner",
                "intro": (
                    "Dissect any brand's positioning across the 7 layers of the Magenta Circle "
                    "and map its competitive magnetism and message coherence."
                ),
                "scans": scans,
                "audit_runs": audit_runs,
            }
        },
    )


@router.post("/magnetism-scanner/analyze")
async def magnetism_scanner_analyze(
    request: Request,
    url: str = Form(None),
    manual_text: str = Form(None),
):
    """Queue analysis on the provided URL or copy-pasted text block."""
    url_val = (url or "").strip()
    manual_val = (manual_text or "").strip()

    if not url_val and not manual_val:
        return templates.TemplateResponse(
            request,
            "error.html.j2",
            {
                "status_code": 400,
                "error": "Input required: Please provide either a website URL to scan or paste manual text content.",
            },
            status_code=400,
        )

    normalized_url = ""
    if url_val:
        valid, result = validate_url(url_val)
        if not valid:
            return templates.TemplateResponse(
                request,
                "error.html.j2",
                {"status_code": 400, "error": f"URL rejected: {result}"},
                status_code=400,
            )
        normalized_url = result

    token = secrets.token_urlsafe(12)
    if normalized_url:
        input_type = "url"
        input_value = normalized_url
        brand_name = slug_from_url(normalized_url)
        display_url = normalized_url
    else:
        input_type = "manual"
        input_value = manual_val
        brand_name = "Manual Upload Brand"
        display_url = "Manual Upload"

    insert_magnetism_job(
        token=token,
        brand_name=brand_name,
        url=display_url,
        input_type=input_type,
        input_value=input_value,
    )
    await get_queue().enqueue_magnetism(token)
    return RedirectResponse(f"/magnetism-scanner/{token}/status", status_code=303)


@router.post("/magnetism-scanner/from-run")
async def magnetism_scanner_from_run(
    request: Request,
    run_id: int = Form(...),
):
    """Queue a Magnetism scan from an existing Brand Audit run snapshot."""
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
    finally:
        store.close()

    if snapshot is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Brand Audit run #{run_id}"},
            status_code=404,
        )

    run = snapshot.get("run") or {}
    token = secrets.token_urlsafe(12)
    insert_magnetism_job(
        token=token,
        brand_name=str(run.get("brand_name") or f"Brand Audit run #{run_id}"),
        url=str(run.get("url") or "Brand Audit snapshot"),
        input_type="audit_run",
        input_value=str(run_id),
        source_run_id=run_id,
    )
    await get_queue().enqueue_magnetism(token)
    return RedirectResponse(f"/magnetism-scanner/{token}/status", status_code=303)


_MAGNETISM_PHASES = [
    ("queued", "Queued"),
    ("collecting", "Collecting Brand Audit evidence"),
    ("extracting", "Extracting Magnetism signals"),
    ("interpreting", "Interpreting TLDR Brand3 blocks"),
    ("scoring", "Scoring magnetism and coherence"),
    ("finalizing", "Writing Magnetism report"),
]

_MAGNETISM_PHASE_LABELS = {
    **{key: label for key, label in _MAGNETISM_PHASES},
    "ready": "Magnetism report ready",
    "failed": "Magnetism scan failed",
}


@router.get("/magnetism-scanner/{token}/status")
async def magnetism_scanner_status(request: Request, token: str):
    """Render the shared waiting page for an in-flight Magnetism scan."""
    row = get_magnetism_scan_by_token(token)
    if row is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan token {token}"},
            status_code=404,
        )
    if row.get("status") == "ready":
        return RedirectResponse("/magnetism-scanner/scan/{}".format(row["id"]), status_code=303)

    phase = _magnetism_phase(row)
    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {
            "token": token,
            "brand_slug": row.get("brand_name") or "magnetism scan",
            "status": row.get("status") or "queued",
            "elapsed_seconds": _elapsed(row.get("started_at")),
            "elapsed_label": _elapsed_label(_elapsed(row.get("started_at"))),
            "error_message": row.get("error_message"),
            "phase": phase,
            "phase_label": _MAGNETISM_PHASE_LABELS.get(phase, "Working"),
            "phase_steps": _phase_steps(_MAGNETISM_PHASES, phase, row.get("status") or "queued"),
            "ready_href": "/magnetism-scanner/scan/{}".format(row["id"]),
            "back_href": "/magnetism-scanner",
            "status_label": "magnetism_status",
            "typical_run_label": "1-4 min",
            "status_note": "Page auto-refreshes every 5 seconds. This checklist reflects Magnetism Scanner phase, not a percentage estimate.",
        },
    )


def _elapsed(started_at: str | None) -> int:
    if not started_at:
        return 0
    try:
        dt = datetime.fromisoformat(str(started_at).replace(" ", "T"))
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))


def _elapsed_label(seconds: int) -> str:
    minutes, rest = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{rest:02d}"


def _magnetism_phase(row: dict) -> str:
    phase = row.get("phase") or row.get("status") or "queued"
    if row.get("status") == "queued":
        return "queued"
    if row.get("status") == "failed":
        return "failed"
    if row.get("status") == "ready":
        return "ready"
    return str(phase)


def _phase_steps(phases: list[tuple[str, str]], current_phase: str, status: str) -> list[dict]:
    if status == "failed":
        current_phase = "failed"
    if status == "ready":
        current_phase = "ready"

    current_index = next(
        (idx for idx, (key, _label) in enumerate(phases) if key == current_phase),
        -1,
    )
    steps = []
    for idx, (key, label) in enumerate(phases):
        if current_phase == "ready" or (current_index >= 0 and idx < current_index):
            state = "done"
        elif key == current_phase:
            state = "active"
        elif current_phase == "failed" and current_index >= 0 and idx == current_index:
            state = "failed"
        else:
            state = "pending"
        steps.append({"key": key, "label": label, "state": state})
    if current_phase == "failed":
        steps.append({"key": "failed", "label": "Magnetism scan failed", "state": "failed"})
    if current_phase == "ready":
        steps.append({"key": "ready", "label": "Magnetism report ready", "state": "done"})
    return steps


@router.get("/magnetism-scanner/scan/{scan_id}")
async def magnetism_scanner_detail(request: Request, scan_id: int):
    """Render details sheet of a specific magnetism scan."""
    row = get_magnetism_scan(scan_id)
    if row is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}"},
            status_code=404,
        )

    try:
        payload = json.loads(row["raw_payload"])
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupted scan payload in database.")
    if not payload.get("metrics") or not payload.get("tldr_brand3"):
        payload = MagnetismExtractor(llm=None)._normalize_analysis(payload)
    else:
        payload = MagnetismExtractor(llm=None).ensure_tldr_v03_contract(payload)

    # Format timestamp nicely
    try:
        # In SQLite, row['created_at'] is 'YYYY-MM-DD HH:MM:SS' or ISO format
        dt = datetime.fromisoformat(row["created_at"].replace(" ", "T"))
        formatted_date = dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except Exception:
        formatted_date = row["created_at"]

    return templates.TemplateResponse(
        request,
        "magnetism_detail.html.j2",
        {
            "model": {
                "id": scan_id,
                "title": f"Magnetism: {payload['brand_name']}",
                "brand_name": payload["brand_name"],
                "url": payload["url"],
                "created_at": formatted_date,
                "magnetism_score": payload["magnetism_score"],
                "coherence_score": payload["coherence_score"],
                "quadrant": payload["quadrant"],
                "executive_headline": payload["executive_headline"],
                "observations": payload["observations"],
                "tldr_grid": payload["tldr_grid"],
                "tldr_brand3": payload.get("tldr_brand3") or {},
                "metrics": payload.get("metrics") or {},
                "diagnosis": payload.get("diagnosis") or {},
                "limitations": payload.get("limitations") or [],
                "source": payload.get("source") or "direct_scan",
                "source_run_id": payload.get("source_run_id"),
                "extraction_mode": payload.get("extraction_mode") or "unknown",
                "canonical_evidence_source": payload.get("canonical_evidence_source"),
                "direct_source_provider": payload.get("direct_source_provider"),
                "deprecation": payload.get("deprecation") or {},
                "evidence_packet_summary": payload.get("evidence_packet_summary") or {},
                "content_distillation_summary": payload.get("content_distillation_summary") or {},
                "system_reading": payload.get("system_reading") or {},
                "score_breakdown": payload["score_breakdown"],
                "magenta_circle": payload["magenta_circle"],
                "fallback_used": payload.get("fallback_used", False),
            }
        },
    )
