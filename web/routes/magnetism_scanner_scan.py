"""Scan detail and SV9 routes for the Magnetism Scanner."""

from __future__ import annotations

import asyncio
import secrets

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ..templates_env import templates
from ..storage import (
    get_sv9_generation_job,
    get_sv9_generation_job_by_scan_id,
    insert_sv9_generation_job,
)
from .magnetism_scanner_impl import (
    _Lang,
    _attach_sv9_link,
    _attach_ui,
    _LOG,
    _magnetism_scan_model_async,
    _methodology_model,
    _moodboard_model,
    _run_sv9_generation_job,
    _research_evidence_model,
    _sv9_generation_copy,
    _sv9_generation_phase,
    _with_lang,
)
from .magnetism_scanner_impl import _evidence_reliability_model
from .magnetism_scanner_vnext import _evidence_vnext_research_summary
from .magnetism_scanner_scan_copy import (
    _attach_audit_data,
    _attach_client_tldr_v2_data,
    _build_sv9_status_context,
    _load_scanner_page_model,
    _scan_not_found_response,
)

router = APIRouter()


@router.get("/magnetism-scanner/scan/{scan_id}")
async def magnetism_scanner_detail(
    request: Request,
    scan_id: int,
    lang: _Lang = Query("es"),
    base: bool = Query(False),
):
    """Render details sheet of a specific magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "tldr"
    _attach_ui(model, lang)
    await _attach_sv9_link(model)
    if model.get("sv9_scan_id") and not base:
        return RedirectResponse(
            _with_lang(f"/sv9/scan/{model['sv9_scan_id']}", lang),
            status_code=303,
        )

    return templates.TemplateResponse(
        request,
        "magnetism_detail.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.post("/magnetism-scanner/scan/{scan_id}/generate-sv9")
async def magnetism_scanner_generate_sv9(
    request: Request,
    scan_id: int,
    lang: _Lang = Query("es"),
):
    """Queue SV9 generation and redirect to a loading page."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )

    source_run_id = model.get("source_run_id")
    if not source_run_id:
        raise HTTPException(status_code=409, detail="scan does not have a Brand Audit source run")

    existing_job = await asyncio.to_thread(
        get_sv9_generation_job_by_scan_id,
        scan_id,
    )
    if existing_job:
        return RedirectResponse(_with_lang(f"/magnetism-scanner/sv9/{existing_job['token']}/status", lang), status_code=303)

    token = secrets.token_urlsafe(12)
    await asyncio.to_thread(
        insert_sv9_generation_job,
        token=token,
        scan_id=scan_id,
        source_run_id=int(source_run_id),
        brand_name=str(model.get("brand_name") or f"Magnetism scan #{scan_id}"),
    )
    _LOG.debug("Queued SV9 generation job %s for scan %s", token, scan_id)
    asyncio.create_task(_run_sv9_generation_job(token))
    return RedirectResponse(_with_lang(f"/magnetism-scanner/sv9/{token}/status", lang), status_code=303)


@router.get("/magnetism-scanner/sv9/{token}/status")
async def magnetism_scanner_sv9_status(request: Request, token: str, lang: _Lang = Query("es")):
    """Intermediate loading page while the shadow SV9 scan is materialized."""
    job = await asyncio.to_thread(get_sv9_generation_job, token)
    if job is None:
        return _scan_not_found_response(request, f"SV9 generation job {token}", lang)
    if job.get("status") == "ready" and job.get("sv9_scan_id"):
        return RedirectResponse(_with_lang(f"/sv9/scan/{job['sv9_scan_id']}", lang), status_code=303)

    phase = _sv9_generation_phase(job)
    copy = _sv9_generation_copy(lang)
    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {"token": token, **_build_sv9_status_context(job, lang=lang, phase=phase, copy=copy)},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/research")
async def magnetism_scanner_research(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render research evidence for a specific Magnetism scan."""
    model = await _load_scanner_page_model(scan_id, lang=lang, active_tab="research")
    if model is None:
        return _scan_not_found_response(request, f"Magnetism scan #{scan_id}", lang)
    model["research"] = _research_evidence_model(model["payload"])
    model["research"]["evidence_vnext_summary"] = _evidence_vnext_research_summary(model.get("source_run_id"))

    return templates.TemplateResponse(
        request,
        "magnetism_research.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/moodboard")
async def magnetism_scanner_moodboard(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the visual moodboard for a specific Magnetism scan."""
    model = await _load_scanner_page_model(scan_id, lang=lang, active_tab="moodboard")
    if model is None:
        return _scan_not_found_response(request, f"Magnetism scan #{scan_id}", lang)
    model["moodboard"] = _moodboard_model(model)

    return templates.TemplateResponse(
        request,
        "magnetism_moodboard.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/audit")
async def magnetism_scanner_audit(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the Brand Audit tab inside the unified Scanner layout."""
    model = await _load_scanner_page_model(scan_id, lang=lang, active_tab="audit")
    if model is None:
        return _scan_not_found_response(request, f"Magnetism scan #{scan_id}", lang)
    await _attach_audit_data(model, model.get("source_run_id"), lang)

    return templates.TemplateResponse(
        request,
        "magnetism_audit.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/client-tldr-v2")
async def magnetism_scanner_client_tldr_v2(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the experimental client-facing TLDR v2 preview."""
    model = await _load_scanner_page_model(scan_id, lang=lang, active_tab="client_tldr_v2")
    if model is None:
        return _scan_not_found_response(request, f"Magnetism scan #{scan_id}", lang)
    await _attach_client_tldr_v2_data(model, model.get("source_run_id"), lang)

    return templates.TemplateResponse(
        request,
        "magnetism_client_tldr_v2.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/evidence-reliability")
async def magnetism_scanner_evidence_reliability(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render Research Pack quality diagnostics for a specific Magnetism scan."""
    model = await _load_scanner_page_model(scan_id, lang=lang, active_tab="evidence_reliability")
    if model is None:
        return _scan_not_found_response(request, f"Magnetism scan #{scan_id}", lang)
    model["quality"] = _evidence_reliability_model(model["payload"])

    return templates.TemplateResponse(
        request,
        "magnetism_evidence_reliability.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/methodology")
async def magnetism_scanner_methodology(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render methodology details for a specific Magnetism scan."""
    model = await _load_scanner_page_model(scan_id, lang=lang, active_tab="methodology")
    if model is None:
        return _scan_not_found_response(request, f"Magnetism scan #{scan_id}", lang)
    model["methodology"] = _methodology_model(model["payload"])

    return templates.TemplateResponse(
        request,
        "magnetism_methodology.html.j2",
        {"model": model, "ui_lang": lang},
    )
