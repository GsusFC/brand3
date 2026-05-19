"""Experimental Brand3 lab routes."""

from __future__ import annotations

import json
import secrets
from datetime import datetime

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import settings
from src.config import BRAND3_DB_PATH
from ..presenters import enrich
from ..brand3_lab_data import (
    build_brand3_lab_audit_case_model,
    build_brand3_lab_audit_review_model,
    build_brand3_lab_case_model,
    build_brand3_lab_experiment_model,
    build_brand3_lab_signal_depth_model,
    build_narrative_shadow_adapter_model,
    build_perceptual_narrative_comparison_model,
    run_narrative_shadow_adapter_trial,
)
from ..middleware.rate_limit import get_client_ip
from ..middleware.team_cookie import create_serializer, is_team_request
from ..storage import get_request, insert_request, list_latest_public
from ..templates_env import templates
from ..workers.queue import get_queue
from ..workers.slug import slug_from_url
from ..workers.url_validator import validate_url
from .status import _PHASE_LABELS, _elapsed, _elapsed_label, _phase, _phase_steps
from src.config import LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.reports.evidence_packet import build_evidence_packet_v0
from src.reports.evidence_packet_prompt_input import build_prompt_input_candidate_v0
from src.reports.narrative_shadow_adapter import build_shadow_narrative_request
from src.reports.renderer import ReportRenderer
from src.storage.sqlite_store import SQLiteStore


class _WebLabFallbackAnalyzer:
    def _call(self, *args, **kwargs) -> str:
        return ""

    def _call_json(self, *args, **kwargs) -> dict:
        return {}

router = APIRouter()


@router.get("/brand3-lab")
async def brand3_lab_home(request: Request):
    rows = enrich(list_latest_public(limit=10))
    return templates.TemplateResponse(
        request,
        "brand3_lab.html.j2",
        {
            "model": {
                "title": "Brand3 Lab",
                "intro": "Run full Lab analysis from URL input. This view renders the same report page format as production, with Lab narrative pipeline applied.",
                "latest_analyses": rows,
            }
        },
    )


@router.post("/brand3-lab/analyze")
async def brand3_lab_analyze(request: Request, url: str = Form(...)):
    valid, result = validate_url(url)
    if not valid:
        return templates.TemplateResponse(
            request,
            "error.html.j2",
            {"status_code": 400, "error": f"URL rejected: {result}"},
            status_code=400,
        )

    normalized = result
    token = secrets.token_urlsafe(12)
    slug = slug_from_url(normalized)
    ip = get_client_ip(request)
    is_team = is_team_request(request, create_serializer(settings.cookie_secret))

    insert_request(
        token=token,
        url=normalized,
        brand_slug=slug,
        requester_ip=ip,
        requester_is_team=is_team,
    )
    await get_queue().enqueue(token)
    return RedirectResponse(f"/brand3-lab/r/{token}/status", status_code=303)


@router.get("/brand3-lab/r/{token}/status")
async def brand3_lab_status(request: Request, token: str):
    row = get_request(token)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Brand3 Lab request {token} not found")
    if row["status"] == "ready":
        return RedirectResponse(f"/brand3-lab/r/{token}", status_code=303)

    elapsed = _elapsed(row.get("started_at"))
    phase = _phase(row)
    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {
            "token": token,
            "brand_slug": row["brand_slug"],
            "status": row["status"],
            "elapsed_seconds": elapsed,
            "elapsed_label": _elapsed_label(elapsed),
            "error_message": row["error_message"],
            "phase": phase,
            "phase_label": _PHASE_LABELS.get(phase, "Working"),
            "phase_steps": _phase_steps(phase, row["status"]),
            "ready_href": f"/brand3-lab/r/{token}",
            "back_href": "/brand3-lab",
        },
    )


def _load_snapshot(run_id: int) -> dict | None:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        return store.get_run_snapshot(run_id)
    finally:
        store.close()


def _lab_candidate_row(candidate: dict, dimension: str, data: dict) -> dict:
    payload = {
        "task": f"Generate bounded findings for {candidate.get('case_id')}/{dimension}.",
        "prompt_rules": list(data.get("prompt_constraints") or []),
        "included_evidence": list(data.get("evidence") or []),
    }
    return {
        "case_id": str(candidate.get("case_id") or ""),
        "dimension": dimension,
        "intent": "lab_report_generation",
        "readiness_status": str(data.get("readiness_status") or "abstain"),
        "user": json.dumps(payload, ensure_ascii=False),
    }


def _readiness_state(packet: dict, dimension: str) -> dict:
    readiness = ((packet.get("dimension_readiness") or {}).get(dimension) or {})
    return readiness if isinstance(readiness, dict) else {}


def _reason_codes_text(readiness: dict) -> str:
    codes = [str(code) for code in (readiness.get("reason_codes") or []) if str(code).strip()]
    return ", ".join(codes) if codes else "none"


def _lab_abstention_finding(
    *,
    status: str,
    readiness: dict,
    cause: str,
) -> dict:
    readiness_reason = str(readiness.get("readiness_reason") or "").strip()
    recommended_action = str(readiness.get("recommended_action") or "").strip()
    reason_codes = _reason_codes_text(readiness)
    observation = (
        "Lab did not execute narrative findings for this dimension. "
        f"status={status}; reason_codes={reason_codes}; cause={cause}."
    )
    implication = readiness_reason or "Dimension is not executable under current Lab evidence contract."
    if recommended_action:
        implication = f"{implication} Recommended action: {recommended_action}"
    return {
        "title": f"Lab abstention ({status})",
        "observation": observation,
        "implication": implication,
        "typical_decision": "",
        "evidence_urls": [],
    }


def _lab_generation_unavailable_finding(*, status: str, readiness: dict) -> dict:
    readiness_reason = str(readiness.get("readiness_reason") or "").strip()
    recommended_action = str(readiness.get("recommended_action") or "").strip()
    reason_codes = _reason_codes_text(readiness)
    implication = "Lab attempted bounded generation but no valid findings were produced."
    if readiness_reason:
        implication = f"{implication} {readiness_reason}"
    if recommended_action:
        implication = f"{implication} Recommended action: {recommended_action}"
    return {
        "title": "Lab generation unavailable",
        "observation": (
            "This dimension was executable under Lab gating but produced empty or invalid output. "
            f"status={status}; reason_codes={reason_codes}; cause=llm_output_empty_or_invalid_json."
        ),
        "implication": implication,
        "typical_decision": "",
        "evidence_urls": [],
    }


def _build_lab_report_narrative_payload(snapshot: dict) -> tuple[dict | None, str | None]:
    try:
        packet = build_evidence_packet_v0(snapshot)
        candidate = build_prompt_input_candidate_v0(packet)
    except Exception:
        return None, "lab_packet_or_candidate_build_failed"

    llm = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
    findings_by_dimension: dict[str, list[dict]] = {}
    executed_dimensions: list[str] = []
    abstained_dimensions: list[str] = []

    for dimension, data in (candidate.get("dimensions") or {}).items():
        status = str(data.get("readiness_status") or "abstain")
        readiness = _readiness_state(packet, dimension)
        row = _lab_candidate_row(candidate, dimension, data)
        request, skip = build_shadow_narrative_request(row, model=LLM_PREMIUM_MODEL)
        if not request:
            findings_by_dimension[dimension] = [
                _lab_abstention_finding(
                    status=status,
                    readiness=readiness,
                    cause=str((skip or {}).get("reason") or "status_not_executable_for_shadow_call"),
                )
            ]
            abstained_dimensions.append(dimension)
            continue

        response = llm._call_json(
            system=request["system"],
            user=request["user"],
            max_tokens=int(request["max_tokens"]),
        )
        raw_findings = response.get("findings") if isinstance(response, dict) else None
        parsed: list[dict] = []
        if isinstance(raw_findings, list):
            for item in raw_findings:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "").strip()
                observation = str(item.get("observation") or "").strip()
                if not title or not observation:
                    continue
                parsed.append(
                    {
                        "title": title,
                        "observation": observation,
                        "implication": str(item.get("bounded_interpretation") or "").strip(),
                        "typical_decision": "",
                        "evidence_urls": [
                            str(url) for url in (item.get("evidence_urls") or []) if isinstance(url, str)
                        ],
                    }
                )
        if parsed:
            findings_by_dimension[dimension] = parsed
            executed_dimensions.append(dimension)
        else:
            findings_by_dimension[dimension] = [
                _lab_generation_unavailable_finding(status=status, readiness=readiness)
            ]
            abstained_dimensions.append(dimension)

    if not findings_by_dimension:
        return None, "lab_pipeline_generated_no_findings"

    run = snapshot.get("run") or {}
    executed_label = ", ".join(sorted(executed_dimensions)) if executed_dimensions else "none"
    abstained_label = ", ".join(sorted(abstained_dimensions)) if abstained_dimensions else "none"
    summary = (
        "Lab narrative scope: ready/thin dimensions only. "
        f"Executed: {executed_label}. "
        f"Abstained or unavailable: {abstained_label}."
    )
    payload = {
        "version": 1,
        "source": "report_narrative",
        "generated_at": datetime.utcnow().isoformat(),
        "run_id": run.get("id"),
        "synthesis_prose": summary,
        "summary": summary,
        "tensions_prose": None,
        "findings_by_dimension": findings_by_dimension,
    }
    return payload, None


@router.get("/brand3-lab/r/{token}")
async def brand3_lab_report(
    request: Request,
    token: str,
):
    row = get_request(token)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Brand3 Lab request {token} not found")
    if row["status"] != "ready":
        return RedirectResponse(f"/brand3-lab/r/{token}/status", status_code=303)

    run_id = row.get("run_id")
    if not run_id:
        raise HTTPException(status_code=500, detail="ready state without run_id")
    snapshot = _load_snapshot(int(run_id))
    if snapshot is None:
        raise HTTPException(status_code=500, detail=f"run {run_id} missing from store")

    lab_payload, lab_error = _build_lab_report_narrative_payload(snapshot)
    if lab_payload:
        patched = dict(snapshot)
        patched_raw_inputs = list(snapshot.get("raw_inputs") or [])
        patched_raw_inputs.append(
            {
                "source": "report_narrative",
                "payload": lab_payload,
            }
        )
        patched["raw_inputs"] = patched_raw_inputs
        html = ReportRenderer().render(patched, theme="light", analyzer=_WebLabFallbackAnalyzer())
        return HTMLResponse(content=html)

    # fallback to official report rendering with explicit cause
    snapshot_html = ReportRenderer().render(snapshot, theme="light", analyzer=_WebLabFallbackAnalyzer())
    fallback_banner = (
        "<section style='padding:12px 20px;border-bottom:1px solid #ddd;font-family:monospace;'>"
        f"<strong>Lab fallback active</strong> · cause={lab_error or 'unknown'} · showing official report narrative."
        "</section>"
    )
    return HTMLResponse(content=fallback_banner + snapshot_html)


@router.get("/brand3-lab/experiments/{layer_id}")
async def brand3_lab_experiment(request: Request, layer_id: str):
    model = build_brand3_lab_experiment_model(layer_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Brand3 Lab experiment not found")
    return templates.TemplateResponse(
        request,
        "brand3_lab_experiment.html.j2",
        {"model": model},
    )


@router.get("/brand3-lab/signal-depth/{depth_id}")
async def brand3_lab_signal_depth(request: Request, depth_id: str):
    model = build_brand3_lab_signal_depth_model(depth_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Brand3 Lab signal depth not found")
    return templates.TemplateResponse(
        request,
        "brand3_lab_signal_depth.html.j2",
        {"model": model},
    )


@router.get("/brand3-lab/cases/{case_id}")
async def brand3_lab_case(request: Request, case_id: str):
    model = build_brand3_lab_case_model(case_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Brand3 Lab case not found")
    return templates.TemplateResponse(
        request,
        "brand3_lab_case.html.j2",
        {"model": model},
    )


@router.get("/brand3-lab/cases/run/{run_id}")
async def brand3_lab_audit_case(request: Request, run_id: int):
    model = build_brand3_lab_audit_case_model(run_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Brand3 Lab audit case not found")
    return templates.TemplateResponse(
        request,
        "brand3_lab_audit_case.html.j2",
        {"model": model},
    )


@router.get("/brand3-lab/cases/run/{run_id}/review")
async def brand3_lab_audit_case_review(request: Request, run_id: int):
    model = build_brand3_lab_audit_review_model(run_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Brand3 Lab audit review not found")
    return templates.TemplateResponse(
        request,
        "brand3_lab_audit_review.html.j2",
        {"model": model},
    )


@router.get("/brand3-lab/perceptual-narrative-comparison")
async def perceptual_narrative_comparison(request: Request):
    return templates.TemplateResponse(
        request,
        "perceptual_narrative_comparison.html.j2",
        {"model": build_perceptual_narrative_comparison_model()},
    )


@router.get("/brand3-lab/narrative-shadow-adapter")
async def narrative_shadow_adapter_view(request: Request):
    mode = str(request.query_params.get("source") or "benchmark").strip().lower()
    if mode not in {"benchmark", "run"}:
        mode = "benchmark"
    return templates.TemplateResponse(
        request,
        "brand3_lab_narrative_shadow_adapter.html.j2",
        {"model": build_narrative_shadow_adapter_model(source_mode=mode)},
    )


@router.post("/brand3-lab/narrative-shadow-adapter")
async def narrative_shadow_adapter_run(
    request: Request,
    mode: str = Form("dry"),
    run_id: str = Form(""),
    source_mode: str = Form("benchmark"),
):
    selected_run_id: int | None = None
    run_id_clean = (run_id or "").strip()
    if run_id_clean:
        try:
            selected_run_id = int(run_id_clean)
        except ValueError:
            selected_run_id = None
    selected_source_mode = source_mode if source_mode in {"benchmark", "run"} else "benchmark"
    if selected_source_mode != "run":
        selected_run_id = None
    execute = mode == "execute"
    run_result = run_narrative_shadow_adapter_trial(
        execute=execute,
        run_id=selected_run_id,
        source_mode=selected_source_mode,
    )
    return templates.TemplateResponse(
        request,
        "brand3_lab_narrative_shadow_adapter.html.j2",
        {
            "model": build_narrative_shadow_adapter_model(
                last_run=run_result,
                run_id=selected_run_id,
                source_mode=selected_source_mode,
            )
        },
    )
