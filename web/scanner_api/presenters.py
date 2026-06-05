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
    scan_mode: dict[str, Any] | None = None,
    failure_diagnostics: dict[str, Any] | None = None,
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
        "failure_diagnostics": failure_diagnostics,
        "scanner_readiness": readiness,
        "scan_mode": scan_mode or {},
        "result_available": status == "ready",
        "status_url": f"/api/v1/scanner/{scan_id}",
        "result_url": f"/api/v1/scanner/{scan_id}/result",
        "evidence_url": f"/api/v1/scanner/{scan_id}/evidence",
        "methodology_url": f"/api/v1/scanner/{scan_id}/methodology",
        "audit_url": f"/api/v1/scanner/{scan_id}/audit",
        "ui_url": f"/magnetism-scanner/scan/{scan_id}{lang_query(lang)}" if status == "ready" else None,
    }


def scanner_result_payload(
    row: dict[str, Any],
    model: dict[str, Any],
    *,
    result_metadata: dict[str, Any],
    lang: Lang = "es",
) -> dict[str, Any]:
    scan_id = int(model["id"])
    payload = model["payload"]
    source_run_id = model.get("source_run_id")
    return {
        "id": scan_id,
        "status": row.get("status") or "ready",
        "brand_name": model["brand_name"],
        "url": model["url"],
        "created_at": model["created_at"],
        "scores": {
            "magnetism": model["magnetism_score"],
            "coherence": model["coherence_score"],
            "quadrant": model["quadrant"],
        },
        "result_metadata": result_metadata,
        "scan_mode": model["scan_mode"],
        "audit": {
            "available": bool(source_run_id),
            "source_run_id": source_run_id,
            "api_url": f"/api/v1/scanner/{scan_id}/audit" if source_run_id else None,
        },
        "tldr_brand3": payload.get("tldr_brand3") or {},
        "tldr_strategy": payload.get("tldr_strategy") or {},
        "evidence_api_url": f"/api/v1/scanner/{scan_id}/evidence",
        "methodology_api_url": f"/api/v1/scanner/{scan_id}/methodology",
        "ui_url": f"/magnetism-scanner/scan/{scan_id}{lang_query(lang)}",
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


def scanner_research_evidence_payload(
    payload: dict[str, Any],
    *,
    entity_packet: dict[str, Any],
) -> dict[str, Any]:
    research_pack = payload.get("research_pack") if isinstance(payload.get("research_pack"), dict) else {}
    entity = research_pack.get("resolved_entity") if isinstance(research_pack.get("resolved_entity"), dict) else {}
    source_map = research_pack.get("source_map") if isinstance(research_pack.get("source_map"), dict) else {}
    graph_summary = payload.get("evidence_graph_summary") if isinstance(payload.get("evidence_graph_summary"), dict) else {}
    product_surfaces = list(entity_packet.get("product_surfaces") or [])
    owned_surfaces = list(entity_packet.get("owned_surfaces") or [])
    tldr_blocks = _tldr_blocks(payload)

    block_evidence = []
    for key, block in tldr_blocks.items():
        if not isinstance(block, dict):
            continue
        block_evidence.append(
            {
                "key": key,
                "label": str(key).replace("_", " ").title(),
                "answer": block.get("answer") or block.get("content"),
                "claim_type": block.get("claim_type") or "unknown",
                "confidence": block.get("confidence") or "unknown",
                "evidence_used": block.get("evidence_used") or block.get("evidence") or [],
                "evidence_sources": block.get("evidence_sources") or [],
            }
        )

    source_counts = graph_summary.get("source_counts") or {}
    source_rows = [
        {
            "url": url,
            "source_type": source.get("source_type") or "unknown",
            "surface_role": source.get("surface_role") or "",
            "entity_scope": source.get("entity_scope") or "",
            "title": source.get("title") or source.get("label") or url,
        }
        for url, source in source_map.items()
        if isinstance(source, dict)
    ]
    source_rows.sort(key=lambda item: (item["source_type"], item["url"]))
    if not product_surfaces:
        product_surfaces = [
            {
                "url": item["url"],
                "role": item["surface_role"] or item["source_type"],
                "entity_scope": item["entity_scope"],
                "reason": "Detected from persisted Research Pack source map.",
            }
            for item in source_rows
            if str(item.get("entity_scope") or "").startswith("product:")
        ]
    if not owned_surfaces:
        owned_surfaces = [
            {
                "url": item["url"],
                "role": item["surface_role"] or item["source_type"],
                "entity_scope": item["entity_scope"],
                "reason": "Persisted Research Pack source.",
            }
            for item in source_rows
            if str(item.get("source_type") or "").startswith("owned_")
        ]

    return {
        "entity": entity,
        "entity_packet": entity_packet,
        "research_pack_source": payload.get("research_pack_source") or "legacy_snapshot",
        "tldr_generation_mode": payload.get("tldr_generation_mode") or "unknown",
        "category": research_pack.get("category") or "",
        "offer": research_pack.get("offer") or "",
        "company_summary": research_pack.get("company_summary") or "",
        "product_summary": research_pack.get("product_summary") or "",
        "audience": research_pack.get("audience") or "",
        "outcome": research_pack.get("outcome") or "",
        "declared_mission": research_pack.get("declared_mission") or "",
        "future_direction": research_pack.get("future_direction") or "",
        "owned_surfaces": owned_surfaces,
        "product_surfaces": product_surfaces,
        "source_counts": source_counts,
        "source_rows": source_rows,
        "block_evidence": block_evidence,
        "proof_points": research_pack.get("proof_points") or [],
        "competitive_context": research_pack.get("competitive_context") or [],
        "shadow_sources": _shadow_source_rows(research_pack),
        "noise_rejected": research_pack.get("noise_rejected") or [],
        "entity_boundary_warnings": _entity_boundary_warnings(research_pack),
        "entity_boundary_rejections": _entity_boundary_rejections(research_pack),
        "evidence_gaps": research_pack.get("evidence_gaps") or [],
        "confidence_notes": research_pack.get("confidence_notes") or [],
        "graph_summary": graph_summary,
    }


def _tldr_blocks(payload: dict[str, Any]) -> dict[str, Any]:
    analyst_payload = payload.get("analyst_tldr_validated")
    if isinstance(analyst_payload, dict) and isinstance(analyst_payload.get("tldr_brand3"), dict):
        return analyst_payload["tldr_brand3"]
    tldr_brand3 = payload.get("tldr_brand3")
    return tldr_brand3 if isinstance(tldr_brand3, dict) else {}


def _shadow_source_rows(research_pack: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in research_pack.get("shadow_sources") or []:
        if not isinstance(item, dict):
            continue
        intents = item.get("intents") if isinstance(item.get("intents"), dict) else {}
        intent_rows = []
        result_rows = []
        for name, intent in intents.items():
            if not isinstance(intent, dict):
                continue
            intent_rows.append(
                {
                    "name": str(name),
                    "status": str(intent.get("status") or "unknown"),
                    "result_count": int(intent.get("result_count") or 0),
                    "unique_domains": [str(value) for value in (intent.get("unique_domains") or []) if value],
                }
            )
            for result in intent.get("results") or []:
                if not isinstance(result, dict):
                    continue
                url = str(result.get("url") or "").strip()
                if not url:
                    continue
                result_rows.append(
                    {
                        "intent": str(name),
                        "url": url,
                        "title": str(result.get("title") or url),
                        "excerpt": str(result.get("excerpt") or ""),
                    }
                )
        unique_domains = [str(value) for value in (item.get("unique_domains") or []) if value]
        rows.append(
            {
                "provider": str(item.get("provider") or "parallel"),
                "mode": str(item.get("mode") or ""),
                "status": str(item.get("status") or ""),
                "result_total": int(item.get("result_total") or 0),
                "unique_domain_count": int(item.get("unique_domain_count") or 0),
                "unique_domains": unique_domains,
                "intents": intent_rows,
                "results": result_rows[:10],
                "readout": _shadow_readout(
                    result_total=int(item.get("result_total") or 0),
                    unique_domain_count=int(item.get("unique_domain_count") or 0),
                    unique_domains=unique_domains,
                    intents=intent_rows,
                    results=result_rows,
                ),
                "notes": [str(value) for value in (item.get("notes") or []) if value],
            }
        )
    return rows


def _shadow_readout(
    *,
    result_total: int,
    unique_domain_count: int,
    unique_domains: list[str],
    intents: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    active_intents = [
        {
            "name": str(item.get("name") or ""),
            "label": _shadow_intent_label(str(item.get("name") or "")),
            "result_count": int(item.get("result_count") or 0),
        }
        for item in intents
        if int(item.get("result_count") or 0) > 0
    ]
    top_domains = unique_domains[:5]
    review_candidates = [
        {
            "label": _shadow_intent_label(str(item.get("intent") or "")),
            "url": item.get("url") or "",
            "title": item.get("title") or item.get("url") or "",
            "excerpt": item.get("excerpt") or "",
        }
        for item in results[:5]
    ]
    return {
        "result_total": result_total,
        "unique_domain_count": unique_domain_count,
        "domain_summary": ", ".join(top_domains),
        "signal_types": active_intents,
        "review_candidates": review_candidates,
    }


def _shadow_intent_label(intent: str) -> str:
    labels = {
        "mentions": "mentions / reviews / community",
        "competitors": "competitors / alternatives",
        "news": "news / launches / public updates",
        "ai_visibility": "AI visibility / machine-readable presence",
    }
    return labels.get(intent, intent.replace("_", " ") or "external signal")


def _entity_boundary_warnings(research_pack: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for note in research_pack.get("confidence_notes") or []:
        text = str(note or "").strip()
        if text.startswith("entity_boundary_collision"):
            warnings.append(text)
    return list(dict.fromkeys(warnings))


def _entity_boundary_rejections(research_pack: dict[str, Any]) -> list[dict[str, Any]]:
    rejections: list[dict[str, Any]] = []
    for item in research_pack.get("noise_rejected") or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "")
        topic = str(item.get("topic") or item.get("source_label") or "")
        reason_text = " ".join(
            str(value or "")
            for value in (
                item.get("reason"),
                item.get("noise_reason"),
                item.get("source_label"),
                item.get("topic"),
                item.get("text"),
            )
        )
        if "entity_boundary_collision" not in reason_text:
            continue
        rejections.append(
            {
                "text": text,
                "topic": topic or "entity_boundary_collision",
                "source_url": item.get("source_url") or "",
                "source_type": item.get("source_type") or "",
            }
        )
    return rejections
