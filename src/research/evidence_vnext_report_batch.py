from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from src.research.evidence_vnext_report_rendering import render_batch_report_markdown
from src.research.evidence_vnext_acquisition_contracts import (
    accumulate_acquisition_contract_exclusions as _accumulate_acquisition_contract_exclusions,
    accumulate_acquisition_diagnostics as _accumulate_acquisition_diagnostics,
    build_acquisition_matrix as _accumulate_acquisition_matrix,
    build_provider_acquisition_contracts as _provider_acquisition_contracts,
    build_provider_contract_backlog as _provider_contract_backlog,
    finalize_acquisition_diagnostics as _finalize_acquisition_diagnostics,
    finalize_acquisition_matrix as _finalize_acquisition_matrix,
)
from src.research.evidence_vnext_report_decisions import (
    _blocked_evidence_queue_item,
    _contract_projection_row,
    _contract_projection_summary,
    _contract_recommendations,
    _decision_action_counts,
    _decision_queue,
    _is_reserved_or_placeholder_entity,
    _manual_audit_queue_item,
    _material_quote_contract_queue_item,
    _run_manual_audit_decision,
    _run_promotion_decision,
    _triage_actions,
)
from src.research.evidence_vnext_report_projection import (
    _promotion_after_manual_audit,
    _quote_source_review_queue_item,
)
from src.research.evidence_vnext_report_work_orders import (
    _adjudication_intake,
    _intervention_packets,
    _readiness_matrix,
    _shadow_policy_action_counts,
    _shadow_policy_runs,
    _work_orders,
)
from src.research.evidence_vnext_report_helpers import (
    _accumulate_semantic_evidence,
    _accumulate_semantic_llm_comparison,
    _batch_recommendation,
    _changed_material_field_previews,
    _collect_examples,
    _compact_review_observations,
    _context_url_identity,
    _count_dict,
    _dedupe_overlap_items,
    _host,
    _join_unique,
    _merge_counts,
    _normalized_overlap_text,
    _observation_reason,
    _pack_field_text,
    _preview_text,
    _review_material_overlaps,
    _root_domain,
    _text_overlaps_field,
    _top_counts,
    _unique,
    _url_identity,
)


PROMOTION_MAX_LIMITED_REVIEW_COUNT = 3
PROMOTION_MAX_LIMITED_MISSING_URL_COUNT = 2
PROMOTION_BLOCKING_REVIEW_REASONS = {"same_name_different_root_domain"}
MANUAL_AUDIT_MATERIAL_FIELDS = {"proof_points", "founder_or_press_context", "competitive_context"}
RESERVED_OR_PLACEHOLDER_ROOTS = {"example.com", "example.net", "example.org", "example.edu"}
RESERVED_OR_PLACEHOLDER_TLDS = {"example", "invalid", "localhost", "test"}


def build_batch_report(results: list[dict[str, Any]], *, db_path: str = "") -> dict[str, Any]:
    rows = []
    totals = {
        "run_count": len(results),
        "accepted": 0,
        "review_required": 0,
        "rejected": 0,
        "reclassified_to_noise": 0,
        "changed_fields": 0,
        "lost_fields": 0,
        "material_lost_fields": 0,
    }
    status_counts: dict[str, int] = {}
    review_reasons: dict[str, int] = {}
    rejected_reasons: dict[str, int] = {}
    source_classes: dict[str, int] = {}
    review_examples: dict[str, list[dict[str, Any]]] = {}
    rejected_examples: dict[str, list[dict[str, Any]]] = {}
    acquisition_provider_rows: dict[str, dict[str, Any]] = {}
    acquisition_source_class_rows: dict[str, dict[str, Any]] = {}
    acquisition_diagnostics_rows: list[dict[str, Any]] = []
    acquisition_contract_exclusions: dict[str, Any] = {
        "total": 0,
        "by_contract": {},
        "by_surface": {},
        "by_feature": {},
    }
    semantic_evidence: dict[str, Any] = {
        "classifier": "none",
        "accepted_material": 0,
        "accepted_weak": 0,
        "semantic_class_counts": {},
        "materiality_counts": {},
        "entity_fit_counts": {},
        "weak_examples": [],
    }
    semantic_llm: dict[str, Any] = {
        "classifier": "llm_shadow_v0",
        "status_counts": {},
        "models": {},
        "semantic_class_disagreement_count": 0,
        "materiality_disagreement_count": 0,
        "rows": [],
    }
    promotion_counts: dict[str, int] = {}
    manual_audit_counts: dict[str, int] = {"required": 0, "not_required": 0}
    manual_audit_verdict_counts: dict[str, int] = {}
    manual_audit_queue: list[dict[str, Any]] = []
    blocked_evidence_queue: list[dict[str, Any]] = []
    material_quote_contract_queue: list[dict[str, Any]] = []
    quote_source_review_queue: list[dict[str, Any]] = []
    quote_source_material_impact_counts: dict[str, int] = {}
    contract_projection_rows: list[dict[str, Any]] = []

    for result in results:
        comparison = result["vnext_comparison"]
        summary = comparison["summary"]
        gate = result["vnext_gate"]["summary"]
        gate_payload = result["vnext_gate"]
        scorecard = summary["scorecard"]
        status = str(scorecard.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        promotion = _run_promotion_decision(
            summary=summary,
            gate=gate,
            comparison=comparison,
            gate_payload=gate_payload,
            vnext_pack=result.get("vnext_pack") if isinstance(result.get("vnext_pack"), dict) else {},
        )
        manual_audit = _run_manual_audit_decision(comparison=comparison, promotion=promotion)
        promotion = _promotion_after_manual_audit(promotion=promotion, manual_audit=manual_audit)
        promotion_counts[promotion["status"]] = promotion_counts.get(promotion["status"], 0) + 1
        manual_audit_counts["required" if manual_audit["required"] else "not_required"] += 1
        if manual_audit["required"]:
            queue_item = _manual_audit_queue_item(
                comparison=comparison,
                gate_payload=gate_payload,
                promotion=promotion,
                manual_audit=manual_audit,
            )
            manual_audit_queue.append(queue_item)
            audit_verdict = str(queue_item.get("audit_verdict") or "unknown")
            manual_audit_verdict_counts[audit_verdict] = manual_audit_verdict_counts.get(audit_verdict, 0) + 1
        if promotion["status"] == "blocked" and promotion.get("material_overlaps"):
            blocked_evidence_queue.append(
                _blocked_evidence_queue_item(
                    comparison=comparison,
                    promotion=promotion,
                )
            )
        quote_contract_item = _material_quote_contract_queue_item(comparison=comparison, promotion=promotion)
        if quote_contract_item["violations"]:
            material_quote_contract_queue.append(quote_contract_item)
        quote_review_item = _quote_source_review_queue_item(
            comparison=comparison,
            gate_payload=gate_payload,
            promotion=promotion,
            manual_audit=manual_audit,
            current_pack=result.get("current_graph_pack") if isinstance(result.get("current_graph_pack"), dict) else {},
            vnext_pack=result.get("vnext_pack") if isinstance(result.get("vnext_pack"), dict) else {},
        )
        if quote_review_item["observations"]:
            quote_source_review_queue.append(quote_review_item)
            for observation in quote_review_item["observations"]:
                impact = str(observation.get("material_impact") or "unknown")
                quote_source_material_impact_counts[impact] = quote_source_material_impact_counts.get(impact, 0) + 1
        contract_projection = _contract_projection_row(
            comparison=comparison,
            summary=summary,
            gate=gate,
            gate_payload=gate_payload,
            current_promotion=promotion,
            current_manual_audit=manual_audit,
            vnext_pack=result.get("vnext_pack") if isinstance(result.get("vnext_pack"), dict) else {},
        )
        contract_projection_rows.append(contract_projection)

        totals["accepted"] += int(gate.get("accepted_count") or 0)
        totals["review_required"] += int(gate.get("review_required_count") or 0)
        totals["rejected"] += int(gate.get("rejected_count") or 0)
        totals["reclassified_to_noise"] += int(summary.get("reclassified_to_noise_count") or 0)
        totals["changed_fields"] += int(summary.get("changed_count") or 0)
        totals["lost_fields"] += int(summary.get("lost_count") or 0)
        totals["material_lost_fields"] += int(summary.get("material_lost_count") or 0)

        _merge_counts(review_reasons, gate.get("review_reason_counts") or {})
        _merge_counts(rejected_reasons, gate.get("rejected_reason_counts") or {})
        _merge_counts(source_classes, gate.get("source_class_counts") or {})
        _collect_examples(
            review_examples,
            gate_payload.get("review_required") or [],
            run_id=comparison.get("run_id"),
            brand_name=comparison.get("brand_name") or "",
        )
        _collect_examples(
            rejected_examples,
            gate_payload.get("rejected") or [],
            run_id=comparison.get("run_id"),
            brand_name=comparison.get("brand_name") or "",
        )
        _accumulate_acquisition_matrix(
            provider_rows=acquisition_provider_rows,
            source_class_rows=acquisition_source_class_rows,
            gate_payload=gate_payload,
        )
        _accumulate_acquisition_contract_exclusions(
            target=acquisition_contract_exclusions,
            payload=result.get("vnext_acquisition_contracts") if isinstance(result.get("vnext_acquisition_contracts"), dict) else {},
        )
        _accumulate_acquisition_diagnostics(
            target=acquisition_diagnostics_rows,
            payload=result.get("vnext_acquisition_diagnostics")
            if isinstance(result.get("vnext_acquisition_diagnostics"), dict)
            else {},
            run_id=comparison.get("run_id"),
            brand_name=comparison.get("brand_name") or "",
        )
        _accumulate_semantic_evidence(
            target=semantic_evidence,
            payload=result.get("vnext_semantic_assessment") if isinstance(result.get("vnext_semantic_assessment"), dict) else {},
            run_id=comparison.get("run_id"),
            brand_name=comparison.get("brand_name") or "",
        )
        _accumulate_semantic_llm_comparison(
            target=semantic_llm,
            heuristic=result.get("vnext_semantic_assessment") if isinstance(result.get("vnext_semantic_assessment"), dict) else {},
            llm=result.get("vnext_semantic_llm_assessment") if isinstance(result.get("vnext_semantic_llm_assessment"), dict) else {},
            run_id=comparison.get("run_id"),
            brand_name=comparison.get("brand_name") or "",
        )

        rows.append(
            {
                "run_id": comparison.get("run_id"),
                "brand_name": comparison.get("brand_name") or "",
                "url": comparison.get("url") or "",
                "status": status,
                "accepted": int(gate.get("accepted_count") or 0),
                "review_required": int(gate.get("review_required_count") or 0),
                "rejected": int(gate.get("rejected_count") or 0),
                "reclassified_to_noise": int(summary.get("reclassified_to_noise_count") or 0),
                "changed_fields": int(summary.get("changed_count") or 0),
                "lost_fields": int(summary.get("lost_count") or 0),
                "material_lost_fields": int(summary.get("material_lost_count") or 0),
                "scorecard_reason_codes": list(scorecard.get("reason_codes") or []),
                "promotion_status": promotion["status"],
                "promotion_reason_codes": list(promotion["reason_codes"]),
                "manual_audit_required": manual_audit["required"],
                "manual_audit_reason_codes": list(manual_audit["reason_codes"]),
                "manual_audit_fields": list(manual_audit["fields"]),
                "review_material_overlaps": list(promotion.get("material_overlaps") or []),
                "material_lost_field_names": list(summary.get("material_lost_fields") or []),
                "non_material_lost_field_names": list(summary.get("non_material_lost_fields") or []),
            }
        )

    contract_recommendations = _contract_recommendations(
        quote_source_review_queue=quote_source_review_queue,
        quote_source_material_impact_counts=quote_source_material_impact_counts,
    )
    contract_projection = _contract_projection_summary(contract_projection_rows)
    acquisition_matrix = _finalize_acquisition_matrix(
        provider_rows=acquisition_provider_rows,
        source_class_rows=acquisition_source_class_rows,
    )
    acquisition_diagnostics = _finalize_acquisition_diagnostics(acquisition_diagnostics_rows)
    provider_acquisition_contracts = _provider_acquisition_contracts(acquisition_matrix)
    provider_contract_backlog = _provider_contract_backlog(provider_acquisition_contracts)
    decision_queue = _decision_queue(
        contract_recommendations=contract_recommendations,
        provider_acquisition_contracts=provider_acquisition_contracts,
        contract_projection=contract_projection,
        manual_audit_queue=manual_audit_queue,
    )
    shadow_policy_runs = _shadow_policy_runs(contract_projection.get("rows") or [])
    readiness_matrix = _readiness_matrix(shadow_policy_runs)
    intervention_packets = _intervention_packets(readiness_matrix.get("rows") or [])
    work_orders = _work_orders(intervention_packets)
    adjudication_intake = _adjudication_intake(work_orders)

    return {
        "version": "evidence_vnext_batch_report_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "db_path": db_path,
        "totals": totals,
        "status_counts": dict(sorted(status_counts.items())),
        "promotion_counts": dict(sorted(promotion_counts.items())),
        "manual_audit_counts": dict(sorted(manual_audit_counts.items())),
        "manual_audit_verdict_counts": dict(sorted(manual_audit_verdict_counts.items())),
        "promotion_thresholds": {
            "max_limited_review_count": PROMOTION_MAX_LIMITED_REVIEW_COUNT,
            "max_limited_missing_evidence_url_count": PROMOTION_MAX_LIMITED_MISSING_URL_COUNT,
            "blocking_review_reasons": sorted(PROMOTION_BLOCKING_REVIEW_REASONS),
        },
        "top_review_reasons": _count_dict(_top_counts(review_reasons, limit=10)),
        "top_rejected_reasons": _count_dict(_top_counts(rejected_reasons, limit=10)),
        "review_examples_by_reason": review_examples,
        "rejected_examples_by_reason": rejected_examples,
        "acquisition_matrix": acquisition_matrix,
        "acquisition_diagnostics": acquisition_diagnostics,
        "acquisition_contract_exclusions": acquisition_contract_exclusions,
        "semantic_evidence": semantic_evidence,
        "semantic_llm": semantic_llm,
        "provider_acquisition_contracts": provider_acquisition_contracts,
        "provider_contract_backlog": provider_contract_backlog,
        "manual_audit_queue": manual_audit_queue,
        "blocked_evidence_queue": blocked_evidence_queue,
        "material_quote_contract_queue": material_quote_contract_queue,
        "quote_source_review_queue": quote_source_review_queue,
        "quote_source_material_impact_counts": dict(sorted(quote_source_material_impact_counts.items())),
        "contract_recommendations": contract_recommendations,
        "contract_projection": contract_projection,
        "decision_queue": decision_queue,
        "decision_action_counts": _decision_action_counts(decision_queue),
        "evidence_contract": {
            "policy": "strict_tone_consistency_source_url",
            "runtime_effect": False,
            "prompt_effect": False,
            "runs": shadow_policy_runs,
            "next_action_counts": _shadow_policy_action_counts(shadow_policy_runs),
        },
        "shadow_policy": {
            "policy": "strict_tone_consistency_source_url",
            "runtime_effect": False,
            "prompt_effect": False,
            "deprecated": True,
            "replacement": "evidence_contract",
            "runs": shadow_policy_runs,
            "next_action_counts": _shadow_policy_action_counts(shadow_policy_runs),
        },
        "readiness_matrix": readiness_matrix,
        "intervention_packets": intervention_packets,
        "work_orders": work_orders,
        "adjudication_intake": adjudication_intake,
        "source_class_counts": dict(sorted(source_classes.items())),
        "rows": rows,
        "recommendation": _batch_recommendation(totals, status_counts, review_reasons),
    }
