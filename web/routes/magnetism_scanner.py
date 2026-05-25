"""FastAPI routes for the Brand3 Magnetism Scanner."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..config import settings
from ..middleware.team_cookie import create_serializer, is_team_request

from src.config import BRAND3_DB_PATH, LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.extractor import MagnetismExtractor
from src.services.magnetism_service import (
    run_legacy_manual_magnetism,
    run_magnetism_from_audit_snapshot,
    run_magnetism_from_url,
)
from src.storage.sqlite_store import SQLiteStore

from ..storage import get_magnetism_scan, insert_magnetism_scan, list_magnetism_scans
from ..templates_env import templates
from ..workers.url_validator import validate_url

router = APIRouter()


def _is_unlocked_team_request(request: Request) -> bool:
    return is_team_request(request, create_serializer(settings.cookie_secret))


def _team_only_response(request: Request):
    return templates.TemplateResponse(
        request,
        "error.html.j2",
        {
            "status_code": 403,
            "error": "Magnetism Scanner is currently restricted to FLOC team access. Unlock via /team/unlock?token=...",
        },
        status_code=403,
    )


@router.get("/magnetism-scanner")
async def magnetism_scanner_index(request: Request):
    """Render index page of Magnetism Scanner showing past analyses and inputs."""
    if not _is_unlocked_team_request(request):
        return _team_only_response(request)

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
    """Run analysis on the provided URL (scraped) or copy-pasted text block."""
    if not _is_unlocked_team_request(request):
        return _team_only_response(request)

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

    # Validate URL if it is provided
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

    llm = LLMAnalyzer(model=LLM_PREMIUM_MODEL)

    try:
        if normalized_url:
            payload = run_magnetism_from_url(normalized_url, llm=llm)
        else:
            payload = run_legacy_manual_magnetism(manual_val, llm=llm)

        # Save to database
        scan_id = insert_magnetism_scan(
            brand_name=payload["brand_name"],
            url=payload["url"] or "Manual Upload",
            magnetism_score=payload["magnetism_score"],
            coherence_score=payload["coherence_score"],
            quadrant=payload["quadrant"],
            raw_payload=json.dumps(payload, ensure_ascii=False),
        )

        # Redirect to details page
        return RedirectResponse(f"/magnetism-scanner/scan/{scan_id}", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(
            request,
            "error.html.j2",
            {"status_code": 500, "error": f"Analysis failed: {str(e)}"},
            status_code=500,
        )


@router.post("/magnetism-scanner/from-run")
async def magnetism_scanner_from_run(
    request: Request,
    run_id: int = Form(...),
):
    """Create a Magnetism scan from an existing Brand Audit run snapshot."""
    if not _is_unlocked_team_request(request):
        return _team_only_response(request)

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

    llm = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
    payload = run_magnetism_from_audit_snapshot(snapshot, llm=llm)

    scan_id = insert_magnetism_scan(
        brand_name=payload["brand_name"],
        url=payload["url"] or "Manual Upload",
        magnetism_score=payload["magnetism_score"],
        coherence_score=payload["coherence_score"],
        quadrant=payload["quadrant"],
        raw_payload=json.dumps(payload, ensure_ascii=False),
    )
    return RedirectResponse(f"/magnetism-scanner/scan/{scan_id}", status_code=303)


@router.get("/magnetism-scanner/scan/{scan_id}")
async def magnetism_scanner_detail(request: Request, scan_id: int):
    """Render details sheet of a specific magnetism scan."""
    if not _is_unlocked_team_request(request):
        return _team_only_response(request)

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
