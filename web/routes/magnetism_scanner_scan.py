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
    _elapsed,
    _elapsed_label,
    _evidence_reliability_model,
    _executive_analysis_for_language,
    _internal_audit_display_decision,
    _internal_audit_status_class,
    _internal_audit_status_label,
    _internal_audit_summary_text,
    _load_audit_read_context,
    _magnetism_scan_model_async,
    _methodology_model,
    _moodboard_model,
    _run_sv9_generation_job,
    _research_evidence_model,
    build_brand_dossier,
    _sv9_generation_copy,
    _sv9_generation_phase,
    _sv9_generation_phase_label,
    _sv9_generation_phase_steps,
    _with_lang,
    _REPORT_READ_ANALYZER,
    build_audit_aware_tldr_v2,
    build_client_tldr_v2,
)
from .magnetism_scanner_vnext import _evidence_vnext_research_summary

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
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"SV9 generation job {token}", "ui_lang": lang},
            status_code=404,
        )
    if job.get("status") == "ready" and job.get("sv9_scan_id"):
        return RedirectResponse(_with_lang(f"/sv9/scan/{job['sv9_scan_id']}", lang), status_code=303)

    phase = _sv9_generation_phase(job)
    copy = _sv9_generation_copy(lang)
    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {
            "token": token,
            "brand_slug": job.get("brand_name") or f"SV9 scan #{job.get('scan_id')}",
            "status": job.get("status") or "queued",
            "elapsed_seconds": _elapsed(job.get("started_at")),
            "elapsed_label": _elapsed_label(_elapsed(job.get("started_at"))),
            "error_message": job.get("error_message"),
            "phase": phase,
            "phase_label": _sv9_generation_phase_label(phase, job.get("status"), lang=lang),
            "phase_steps": _sv9_generation_phase_steps(phase, job.get("status"), lang=lang),
            "ready_href": _with_lang(f"/sv9/scan/{job['sv9_scan_id']}", lang) if job.get("sv9_scan_id") else None,
            "back_href": _with_lang(f"/magnetism-scanner/scan/{job['scan_id']}", lang),
            "status_label": copy["status_label"],
            "typical_run_label": "30-90 sec",
            "status_note": copy["status_note"],
            "queued_message": copy["queued_message"],
            "ready_message": copy["ready_message"],
            "ready_link_label": copy["ready_link_label"],
            "back_link_label": copy["back_link_label"],
            "ui_lang": lang,
        },
    )


@router.get("/magnetism-scanner/scan/{scan_id}/research")
async def magnetism_scanner_research(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render research evidence for a specific Magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "research"
    model["research"] = _research_evidence_model(model["payload"])
    model["research"]["evidence_vnext_summary"] = _evidence_vnext_research_summary(model.get("source_run_id"))
    _attach_ui(model, lang)
    await _attach_sv9_link(model)

    return templates.TemplateResponse(
        request,
        "magnetism_research.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/moodboard")
async def magnetism_scanner_moodboard(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the visual moodboard for a specific Magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "moodboard"
    model["moodboard"] = _moodboard_model(model)
    _attach_ui(model, lang)
    await _attach_sv9_link(model)

    return templates.TemplateResponse(
        request,
        "magnetism_moodboard.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/audit")
async def magnetism_scanner_audit(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the Brand Audit tab inside the unified Scanner layout."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "audit"
    _attach_ui(model, lang)
    await _attach_sv9_link(model)
    source_run_id = model.get("source_run_id")
    if not source_run_id:
        model["audit"] = {"available": False, "reason": "missing_source_run"}
        model["internal_audit"] = {"available": False, "reason": "missing_source_run"}
        return templates.TemplateResponse(
            request,
            "magnetism_audit.html.j2",
            {"model": model, "ui_lang": lang},
        )

    snapshot, narrative_payload, score_provenance = await asyncio.to_thread(
        _load_audit_read_context,
        int(source_run_id),
        lang,
    )
    if snapshot is None:
        model["audit"] = {
            "available": False,
            "reason": "missing_snapshot",
            "source_run_id": source_run_id,
        }
        model["internal_audit"] = {
            "available": False,
            "reason": "missing_snapshot",
            "source_run_id": source_run_id,
        }
    else:
        audit_context = build_brand_dossier(
            snapshot,
            theme="light",
            analyzer=_REPORT_READ_ANALYZER,
            narrative_payload=narrative_payload,
        )
        audit_context["executive_analysis_v2"] = _executive_analysis_for_language(
            audit_context,
            narrative_payload,
            lang,
        )
        current_tldr = {}
        if isinstance(model.get("payload"), dict):
            current_tldr = model["payload"].get("tldr_brand3") or {}
        tldr_v2 = build_audit_aware_tldr_v2(
            score_provenance=score_provenance,
            current_tldr=current_tldr,
        )
        status_label = _internal_audit_status_label(tldr_v2.get("score_state") or {}, score_provenance)
        model["audit"] = {
            "available": True,
            "source_run_id": int(source_run_id),
            "context": audit_context,
        }
        model["internal_audit"] = {
            "available": True,
            "source_run_id": int(source_run_id),
            "score_provenance": score_provenance,
            "tldr_v2": tldr_v2,
            "score_state": tldr_v2.get("score_state") or {},
            "reviewed_score": score_provenance.get("reviewed_score") or None,
            "status_label": status_label,
            "display_decision_label": _internal_audit_display_decision(tldr_v2.get("score_state") or {}),
            "status_class": _internal_audit_status_class(status_label),
            "summary": _internal_audit_summary_text(score_provenance, tldr_v2, lang=lang),
        }

    return templates.TemplateResponse(
        request,
        "magnetism_audit.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/client-tldr-v2")
async def magnetism_scanner_client_tldr_v2(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the experimental client-facing TLDR v2 preview."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "client_tldr_v2"
    _attach_ui(model, lang)
    await _attach_sv9_link(model)
    source_run_id = model.get("source_run_id")
    if not source_run_id:
        model["client_tldr_v2"] = {
            "available": False,
            "reason": "missing_source_run",
            "message": "This preview requires an attached Brand Audit run.",
        }
        return templates.TemplateResponse(
            request,
            "magnetism_client_tldr_v2.html.j2",
            {"model": model, "ui_lang": lang},
        )

    snapshot, narrative_payload, score_provenance = await asyncio.to_thread(
        _load_audit_read_context,
        int(source_run_id),
        lang,
    )

    if snapshot is None:
        model["client_tldr_v2"] = {
            "available": False,
            "reason": "missing_snapshot",
            "message": "The attached Brand Audit snapshot is unavailable.",
        }
    else:
        report_context = build_brand_dossier(
            snapshot,
            theme="light",
            analyzer=_REPORT_READ_ANALYZER,
            narrative_payload=narrative_payload,
        )
        current_tldr = {}
        if isinstance(model.get("payload"), dict):
            current_tldr = model["payload"].get("tldr_brand3") or {}
        model["client_tldr_v2"] = {
            "available": True,
            **build_client_tldr_v2(
                brand_name=str(model.get("brand_name") or "brand scan"),
                url=str(model.get("url") or ""),
                current_tldr=current_tldr,
                score_provenance=score_provenance,
                report_base=report_context,
                lang=lang,
                scanner_display_score=model.get("magnetism_score"),
            ),
        }

    return templates.TemplateResponse(
        request,
        "magnetism_client_tldr_v2.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/evidence-reliability")
async def magnetism_scanner_evidence_reliability(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render Research Pack quality diagnostics for a specific Magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "evidence_reliability"
    model["quality"] = _evidence_reliability_model(model["payload"])
    _attach_ui(model, lang)
    await _attach_sv9_link(model)

    return templates.TemplateResponse(
        request,
        "magnetism_evidence_reliability.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/methodology")
async def magnetism_scanner_methodology(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render methodology details for a specific Magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "methodology"
    model["methodology"] = _methodology_model(model["payload"])
    _attach_ui(model, lang)
    await _attach_sv9_link(model)

    return templates.TemplateResponse(
        request,
        "magnetism_methodology.html.j2",
        {"model": model, "ui_lang": lang},
    )
