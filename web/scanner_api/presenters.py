"""Pure response presenters for the public Brand3 Scanner API."""

from __future__ import annotations

from typing import Any, Literal


Lang = Literal["es", "en"]


def lang_query(lang: Lang) -> str:
    return f"?lang={lang}"


def scanner_status_payload(
    row: dict[str, Any],
    *,
    phase: str,
    readiness: dict[str, Any],
    lang: Lang = "es",
) -> dict[str, Any]:
    scan_id = int(row.get("id") or 0)
    status = str(row.get("status") or "queued")
    return {
        "id": scan_id,
        "status": status,
        "phase": phase,
        "brand_name": row.get("brand_name"),
        "url": row.get("url"),
        "source_run_id": row.get("source_run_id"),
        "created_at": row.get("created_at"),
        "started_at": row.get("started_at"),
        "completed_at": row.get("completed_at"),
        "error_message": row.get("error_message"),
        "scanner_readiness": readiness,
        "result_available": status == "ready",
        "status_url": f"/api/v1/scanner/{scan_id}",
        "result_url": f"/api/v1/scanner/{scan_id}/result",
        "evidence_url": f"/api/v1/scanner/{scan_id}/evidence",
        "methodology_url": f"/api/v1/scanner/{scan_id}/methodology",
        "audit_url": f"/api/v1/scanner/{scan_id}/audit",
        "ui_url": f"/magnetism-scanner/scan/{scan_id}{lang_query(lang)}" if status == "ready" else None,
    }


def scanner_result_metadata(
    payload: dict[str, Any],
    *,
    scanner_readiness: dict[str, Any],
    publication_decision: dict[str, Any],
) -> dict[str, Any]:
    research_pack = payload.get("research_pack") if isinstance(payload.get("research_pack"), dict) else {}
    quality = payload.get("research_pack_quality") if isinstance(payload.get("research_pack_quality"), dict) else {}
    graph_summary = payload.get("evidence_graph_summary") if isinstance(payload.get("evidence_graph_summary"), dict) else {}
    shadow_sources = research_pack.get("shadow_sources") if isinstance(research_pack.get("shadow_sources"), list) else []
    tldr_mode = str(payload.get("tldr_generation_mode") or "")
    pack_source = str(payload.get("research_pack_source") or "")
    generated_with = {
        "audit_snapshot": bool(payload.get("source_run_id")),
        "research_pack": bool(research_pack),
        "evidence_graph": pack_source == "evidence_graph" or bool(graph_summary),
        "analyst_pass": tldr_mode == "analyst_pass_validated" or bool(payload.get("analyst_tldr_validated")),
        "research_pack_quality": bool(quality),
        "parallel_shadow": bool(shadow_sources),
    }
    freshness_requirements = (
        generated_with["research_pack"],
        generated_with["evidence_graph"],
        generated_with["analyst_pass"],
        generated_with["research_pack_quality"],
    )
    return {
        "result_version": "scanner_result_v1",
        "pipeline_version": "brand3_scanner_pipeline_2026_06_03",
        "generated_with": generated_with,
        "scanner_readiness": scanner_readiness,
        "publication_decision": publication_decision,
        "stale_against_current_pipeline": not all(freshness_requirements),
    }


def scanner_methodology_payload(
    payload: dict[str, Any],
    *,
    result_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "result_metadata": result_metadata,
        "tldr_generation_mode": payload.get("tldr_generation_mode") or "unknown",
        "research_pack_source": payload.get("research_pack_source") or "legacy_snapshot",
        "analysis_error": payload.get("analyst_tldr_analysis_error"),
        "strategy": payload.get("tldr_strategy") or {},
        "magenta_circle": payload.get("magenta_circle") or {},
        "metrics": payload.get("metrics") or {},
        "score_breakdown": payload.get("score_breakdown") or {},
        "evidence_packet_summary": payload.get("evidence_packet_summary") or {},
        "content_distillation_summary": payload.get("content_distillation_summary") or {},
        "extraction_mode": payload.get("extraction_mode") or "unknown",
        "source": payload.get("source") or "direct_scan",
        "canonical_evidence_source": payload.get("canonical_evidence_source"),
        "direct_source_provider": payload.get("direct_source_provider"),
        "limitations": payload.get("limitations") or [],
        "warnings": payload.get("warnings") or [],
        "research_pack": payload.get("research_pack") or {},
    }
