"""Helpers for Magnetism Scanner scan/detail routes."""

from __future__ import annotations

import asyncio

from fastapi import Request

from src.reports.dossier import build_brand_dossier

from ..templates_env import templates
from .magnetism_scanner_impl import (
    _Lang,
    _attach_sv9_link,
    _attach_ui,
    _elapsed,
    _executive_analysis_for_language,
    _internal_audit_display_decision,
    _internal_audit_status_class,
    _internal_audit_status_label,
    _internal_audit_summary_text,
    _sv9_generation_phase_label,
    _sv9_generation_phase_steps,
    _elapsed_label,
    _load_audit_read_context,
    _magnetism_scan_model_async as _load_scan_model_async,
    _REPORT_READ_ANALYZER,
    _with_lang,
    build_audit_aware_tldr_v2,
    build_client_tldr_v2,
)


async def _load_scanner_page_model(
    scan_id: int,
    lang: _Lang,
    active_tab: str,
) -> dict | None:
    model = await _load_scan_model_async(scan_id, lang=lang)
    if model is None:
        return None
    model["active_tab"] = active_tab
    _attach_ui(model, lang)
    await _attach_sv9_link(model)
    return model


def _scan_not_found_response(
    request: Request,
    resource: str,
    lang: _Lang,
) -> object:
    return templates.TemplateResponse(
        request,
        "not_found.html.j2",
        {"resource": resource, "ui_lang": lang},
        status_code=404,
    )


async def _attach_audit_data(model: dict, source_run_id: object, lang: _Lang) -> dict:
    if not source_run_id:
        model["audit"] = {"available": False, "reason": "missing_source_run"}
        model["internal_audit"] = {"available": False, "reason": "missing_source_run"}
        return model

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
        return model

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
    return model


async def _attach_client_tldr_v2_data(model: dict, source_run_id: object, lang: _Lang) -> dict:
    if not source_run_id:
        model["client_tldr_v2"] = {
            "available": False,
            "reason": "missing_source_run",
            "message": "This preview requires an attached Brand Audit run.",
        }
        return model

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
        return model

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
    return model


def _build_sv9_status_context(job: dict, lang: _Lang, phase: str, copy: dict) -> dict:
    return {
        "token": job.get("token", ""),
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
    }
