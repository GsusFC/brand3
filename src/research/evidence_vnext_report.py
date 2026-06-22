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
    _adjudication_intake,
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
    _shadow_policy_action_counts,
    _shadow_policy_runs,
    _triage_actions,
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


def render_batch_report_markdown(report: dict[str, Any]) -> str:
    totals = report.get("totals") or {}
    recommendation = report.get("recommendation") or {}
    lines = [
        "# Evidence vNext Batch Report",
        "",
        "## Summary",
        "",
        f"- Runs: `{totals.get('run_count', 0)}`",
        f"- Status: `{recommendation.get('status', 'unknown')}`",
        f"- Accepted: `{totals.get('accepted', 0)}`",
        f"- Review required: `{totals.get('review_required', 0)}`",
        f"- Rejected: `{totals.get('rejected', 0)}`",
        f"- Reclassified to noise: `{totals.get('reclassified_to_noise', 0)}`",
        f"- Material lost fields: `{totals.get('material_lost_fields', 0)}`",
        "",
    ]
    acquisition = report.get("acquisition_matrix") or {}
    provider_rows = acquisition.get("provider_rows") or []
    lines.extend(["## Acquisition Matrix", ""])
    if provider_rows:
        lines.extend(["| Provider | Accepted | Review | Rejected | Top reasons |", "| --- | ---: | ---: | ---: | --- |"])
        for row in provider_rows:
            reasons = ", ".join(f"{key}={value}" for key, value in (row.get("reason_counts") or {}).items())
            lines.append(
                "| {provider} | {accepted} | {review} | {rejected} | {reasons} |".format(
                    provider=row.get("provider") or "unknown_provider",
                    accepted=row.get("accepted") or 0,
                    review=row.get("review_required") or 0,
                    rejected=row.get("rejected") or 0,
                    reasons=reasons or "-",
                )
            )
    else:
        lines.append("- None")
    semantic = report.get("semantic_evidence") or {}
    lines.extend(["", "## Semantic Evidence Shadow", ""])
    lines.append(f"- Classifier: `{semantic.get('classifier') or 'none'}`")
    lines.append(f"- Accepted material: `{semantic.get('accepted_material', 0)}`")
    lines.append(f"- Accepted weak: `{semantic.get('accepted_weak', 0)}`")
    class_counts = semantic.get("semantic_class_counts") or {}
    if class_counts:
        lines.extend(["", "| Semantic class | Count |", "| --- | ---: |"])
        for key, value in class_counts.items():
            lines.append(f"| {key} | {value} |")
    weak_examples = semantic.get("weak_examples") or []
    if weak_examples:
        lines.extend(["", "Weak accepted examples:"])
        for item in weak_examples[:10]:
            lines.append(
                "- run `{run_id}` `{brand_name}` · `{semantic_class}` `{url}`: {text_preview}".format(
                    run_id=item.get("run_id"),
                    brand_name=item.get("brand_name") or "",
                    semantic_class=item.get("semantic_class") or "",
                    url=item.get("url") or "-",
                    text_preview=item.get("text_preview") or "-",
                )
            )
    semantic_llm = report.get("semantic_llm") or {}
    lines.extend(["", "## Semantic LLM Shadow", ""])
    lines.append(f"- Status counts: `{semantic_llm.get('status_counts') or {}}`")
    lines.append(f"- Models: `{semantic_llm.get('models') or {}}`")
    lines.append(
        f"- Semantic class disagreements: `{semantic_llm.get('semantic_class_disagreement_count', 0)}`"
    )
    lines.append(
        f"- Materiality disagreements: `{semantic_llm.get('materiality_disagreement_count', 0)}`"
    )
    for item in (semantic_llm.get("rows") or [])[:10]:
        lines.append(
            "- run `{run_id}` `{brand_name}` · status `{status}` · model `{model}` · class_delta `{class_delta}` · materiality_delta `{materiality_delta}`".format(
                run_id=item.get("run_id"),
                brand_name=item.get("brand_name") or "",
                status=item.get("status") or "",
                model=item.get("model") or "",
                class_delta=item.get("semantic_class_disagreement_count") or 0,
                materiality_delta=item.get("materiality_disagreement_count") or 0,
            )
        )
    exclusions = report.get("acquisition_contract_exclusions") or {}
    lines.extend(["", "## Acquisition Contract Exclusions", ""])
    lines.append(f"- Shadow exclusions: `{exclusions.get('total', 0)}`")
    by_contract = exclusions.get("by_contract") or {}
    if by_contract:
        lines.extend(["", "| Contract | Excluded |", "| --- | ---: |"])
        for key, value in by_contract.items():
            lines.append(f"| {key} | {value} |")
    else:
        lines.append("- None")
    lines.extend(["", "## Status Counts", ""])
    for key, value in (report.get("status_counts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Promotion Counts", ""])
    for key, value in (report.get("promotion_counts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Manual Audit Counts", ""])
    for key, value in (report.get("manual_audit_counts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Manual Audit Verdict Counts", ""])
    verdict_counts = report.get("manual_audit_verdict_counts") or {}
    if not verdict_counts:
        lines.append("- None")
    for key, value in verdict_counts.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Manual Audit Queue", ""])
    queue = report.get("manual_audit_queue") or []
    if not queue:
        lines.append("- None")
    for item in queue:
        lines.append(
            "- run `{run_id}` `{brand_name}` · promotion `{promotion_status}` · fields `{fields}`".format(
                run_id=item.get("run_id"),
                brand_name=item.get("brand_name") or "",
                promotion_status=item.get("promotion_status") or "",
                fields=", ".join(str(field.get("field") or "") for field in item.get("changed_material_fields") or []),
            )
        )
        lines.append(f"  - audit `{item.get('audit_verdict') or 'unknown'}`")
        for reason in item.get("audit_reason_codes") or []:
            lines.append(f"  - audit reason `{reason}`")
        for reason in item.get("review_reason_codes") or []:
            lines.append(f"  - review `{reason}`")
        for action in item.get("triage_actions") or []:
            lines.append(f"  - action `{action}`")
        for field in item.get("changed_material_fields") or []:
            lines.append(
                "  - `{field}` current: {current_preview} / vNext: {vnext_preview}".format(
                    field=field.get("field") or "",
                    current_preview=field.get("current_preview") or "-",
                    vnext_preview=field.get("vnext_preview") or "-",
                )
            )
        for observation in item.get("review_examples") or []:
            lines.append(
                "  - `{feature_name}` `{reason}` `{url}`: {text_preview}".format(
                    feature_name=observation.get("feature_name") or "",
                    reason=observation.get("classification_reason") or "",
                    url=observation.get("url") or "-",
                    text_preview=observation.get("text_preview") or "-",
                )
            )
        for overlap in item.get("review_material_overlaps") or []:
            lines.append(
                "  - overlap `{field}` `{feature_name}` `{reason}`: {text_preview}".format(
                    field=overlap.get("field") or "",
                    feature_name=overlap.get("feature_name") or "",
                    reason=overlap.get("classification_reason") or "",
                    text_preview=overlap.get("text_preview") or "-",
                )
            )
    lines.extend(["", "## Blocked Evidence Queue", ""])
    blocked_queue = report.get("blocked_evidence_queue") or []
    if not blocked_queue:
        lines.append("- None")
    for item in blocked_queue:
        lines.append(
            "- run `{run_id}` `{brand_name}` · reasons `{reasons}`".format(
                run_id=item.get("run_id"),
                brand_name=item.get("brand_name") or "",
                reasons=", ".join(str(reason) for reason in item.get("promotion_reason_codes") or []),
            )
        )
        for action in item.get("triage_actions") or []:
            lines.append(f"  - action `{action}`")
        for overlap in item.get("review_material_overlaps") or []:
            lines.append(
                "  - overlap `{field}` `{feature_name}` `{reason}` `{url}`: {text_preview}".format(
                    field=overlap.get("field") or "",
                    feature_name=overlap.get("feature_name") or "",
                    reason=overlap.get("classification_reason") or "",
                    url=overlap.get("url") or "-",
                    text_preview=overlap.get("text_preview") or "-",
                )
            )
    lines.extend(["", "## Material Quote Contract Queue", ""])
    contract_queue = report.get("material_quote_contract_queue") or []
    if not contract_queue:
        lines.append("- None")
    for item in contract_queue:
        lines.append(
            "- run `{run_id}` `{brand_name}` · promotion `{promotion_status}`".format(
                run_id=item.get("run_id"),
                brand_name=item.get("brand_name") or "",
                promotion_status=item.get("promotion_status") or "",
            )
        )
        for action in item.get("triage_actions") or []:
            lines.append(f"  - action `{action}`")
        for violation in item.get("violations") or []:
            lines.append(
                "  - `{field}` `{feature_name}`: {text_preview}".format(
                    field=violation.get("field") or "",
                    feature_name=violation.get("feature_name") or "",
                    text_preview=violation.get("text_preview") or "-",
                )
            )
    lines.extend(["", "## Quote Source Review Queue", ""])
    quote_review_queue = report.get("quote_source_review_queue") or []
    if not quote_review_queue:
        lines.append("- None")
    for item in quote_review_queue:
        lines.append(
            "- run `{run_id}` `{brand_name}` · promotion `{promotion_status}` · audit `{audit}`".format(
                run_id=item.get("run_id"),
                brand_name=item.get("brand_name") or "",
                promotion_status=item.get("promotion_status") or "",
                audit="yes" if item.get("manual_audit_required") else "no",
            )
        )
        for observation in item.get("observations") or []:
            lines.append(
                "  - `{feature_name}` `{provider}` · impact `{impact}`: {text_preview}".format(
                    feature_name=observation.get("feature_name") or "",
                    provider=observation.get("provider") or "",
                    impact=observation.get("material_impact") or "unknown",
                    text_preview=observation.get("text_preview") or "-",
                )
            )
    lines.extend(["", "## Quote Source Material Impact Counts", ""])
    impact_counts = report.get("quote_source_material_impact_counts") or {}
    if not impact_counts:
        lines.append("- None")
    for key, value in impact_counts.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Provider Acquisition Contracts", ""])
    provider_contracts = report.get("provider_acquisition_contracts") or []
    if not provider_contracts:
        lines.append("- None")
    for item in provider_contracts:
        lines.append(
            "- `{contract}` · provider `{provider}` · severity `{severity}` · affected `{affected}`".format(
                contract=item.get("contract") or "",
                provider=item.get("provider") or "",
                severity=item.get("severity") or "",
                affected=item.get("affected_observation_count") or 0,
            )
        )
        lines.append(f"  - action `{item.get('recommended_action') or ''}`")
        lines.append(f"  - enforcement `{item.get('enforcement_point') or ''}`")
        lines.append(f"  - status `{item.get('implementation_status') or ''}`")
        lines.append(f"  - next: {item.get('next_step') or ''}")
        for reason in item.get("reason_codes") or []:
            lines.append(f"  - reason `{reason}`")
        for criterion in item.get("acceptance_criteria") or []:
            lines.append(f"  - acceptance: {criterion}")
        for test_name in item.get("proposed_tests") or []:
            lines.append(f"  - test `{test_name}`")
    backlog = report.get("provider_contract_backlog") or {}
    lines.extend(["", "## Provider Contract Backlog", ""])
    if not backlog.get("rows"):
        lines.append("- None")
    else:
        lines.append("| Contract | Status | Lane | Affected | Next step |")
        lines.append("| --- | --- | --- | ---: | --- |")
        for item in backlog.get("rows") or []:
            lines.append(
                "| {contract} | {status} | {lane} | {affected} | {next_step} |".format(
                    contract=item.get("contract") or "",
                    status=item.get("implementation_status") or "",
                    lane=item.get("implementation_lane") or "",
                    affected=item.get("affected_observation_count") or 0,
                    next_step=item.get("next_step") or "",
                )
            )
    lines.extend(["", "## Contract Recommendations", ""])
    contract_recommendations = report.get("contract_recommendations") or []
    if not contract_recommendations:
        lines.append("- None")
    for item in contract_recommendations:
        lines.append(
            "- `{contract}` · severity `{severity}` · affected `{affected}`".format(
                contract=item.get("contract") or "",
                severity=item.get("severity") or "",
                affected=item.get("affected_observation_count") or 0,
            )
        )
        lines.append(f"  - action `{item.get('recommended_action') or ''}`")
        for reason in item.get("reason_codes") or []:
            lines.append(f"  - reason `{reason}`")
    lines.extend(["", "## Contract Projection", ""])
    projection = report.get("contract_projection") or {}
    if not projection:
        lines.append("- None")
    else:
        lines.append(f"- Applied contracts: `{', '.join(projection.get('applied_contracts') or [])}`")
        lines.append(f"- Removed review observations: `{projection.get('removed_review_observation_count', 0)}`")
        lines.append("- Projected promotion counts:")
        for key, value in (projection.get("projected_promotion_counts") or {}).items():
            lines.append(f"  - `{key}`: `{value}`")
        transitions = projection.get("status_transitions") or []
        if transitions:
            lines.append("- Status transitions:")
            for item in transitions:
                lines.append(
                    "  - run `{run_id}` `{brand_name}`: `{current}` -> `{projected}`".format(
                        run_id=item.get("run_id"),
                        brand_name=item.get("brand_name") or "",
                        current=item.get("current_promotion_status") or "",
                        projected=item.get("projected_promotion_status") or "",
                    )
                )
    lines.extend(["", "## Decision Queue", ""])
    decision_queue = report.get("decision_queue") or []
    if not decision_queue:
        lines.append("- None")
    for item in decision_queue:
        affected_runs = list(item.get("affected_runs") or [])
        affected_label = ", ".join(str(run_id) for run_id in affected_runs)
        if not affected_label and item.get("affected_observation_count") is not None:
            affected_label = f"{int(item.get('affected_observation_count') or 0)} observations"
        lines.append(
            "- `{action}` · priority `{priority}` · scope `{scope}`".format(
                action=item.get("action") or "",
                priority=item.get("priority") or "",
                scope=affected_label,
            )
        )
        for reason in item.get("reason_codes") or []:
            lines.append(f"  - reason `{reason}`")
    lines.extend(["", "## Shadow Policy", ""])
    shadow_policy = report.get("shadow_policy") or {}
    shadow_runs = shadow_policy.get("runs") or []
    if not shadow_runs:
        lines.append("- None")
    else:
        lines.append(f"- Policy: `{shadow_policy.get('policy') or ''}`")
        lines.append(f"- Runtime effect: `{str(bool(shadow_policy.get('runtime_effect'))).lower()}`")
        lines.append("- Next action counts:")
        for key, value in (shadow_policy.get("next_action_counts") or {}).items():
            lines.append(f"  - `{key}`: `{value}`")
        for item in shadow_runs:
            transition = "yes" if item.get("status_transition") else "no"
            lines.append(
                "- run `{run_id}` `{brand_name}`: `{current}` -> `{projected}` · transition `{transition}` · next `{next_action}`".format(
                    run_id=item.get("run_id"),
                    brand_name=item.get("brand_name") or "",
                    current=item.get("current_promotion_status") or "",
                    projected=item.get("projected_promotion_status") or "",
                    transition=transition,
                    next_action=item.get("next_action") or "",
                )
            )
            for reason in item.get("remaining_reason_codes") or []:
                lines.append(f"  - remaining `{reason}`")
    lines.extend(["", "## Readiness Matrix", ""])
    readiness = report.get("readiness_matrix") or {}
    readiness_rows = readiness.get("rows") or []
    if not readiness_rows:
        lines.append("- None")
    else:
        lines.append("- Counts:")
        for key, value in (readiness.get("counts") or {}).items():
            lines.append(f"  - `{key}`: `{value}`")
        lines.append("")
        lines.append("| Run | Brand | Readiness | Intervention | Automation | Human |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in readiness_rows:
            lines.append(
                "| {run_id} | {brand_name} | {readiness_status} | {intervention_type} | {automation_lane} | {human_required} |".format(
                    run_id=item.get("run_id"),
                    brand_name=item.get("brand_name") or "",
                    readiness_status=item.get("readiness_status") or "",
                    intervention_type=item.get("intervention_type") or "",
                    automation_lane=item.get("automation_lane") or "",
                    human_required="yes" if item.get("human_required") else "no",
                )
            )
    lines.extend(["", "## Intervention Packets", ""])
    packets = report.get("intervention_packets") or []
    if not packets:
        lines.append("- None")
    for packet in packets:
        lines.append(
            "- `{packet_id}` · priority `{priority}` · runs `{runs}`".format(
                packet_id=packet.get("packet_id") or "",
                priority=packet.get("priority") or "",
                runs=", ".join(str(run_id) for run_id in packet.get("affected_runs") or []),
            )
        )
        lines.append(f"  - title: {packet.get('title') or ''}")
        lines.append(f"  - automation: `{packet.get('automation_lane') or ''}`")
        lines.append(f"  - closure: {packet.get('closure_criteria') or ''}")
        for reason in packet.get("dominant_reason_codes") or []:
            lines.append(f"  - reason `{reason}`")
    lines.extend(["", "## Work Orders", ""])
    work_orders = report.get("work_orders") or []
    if not work_orders:
        lines.append("- None")
    for item in work_orders:
        lines.append(
            "- `{work_order_id}` · `{brand_name}` · packet `{packet_id}`".format(
                work_order_id=item.get("work_order_id") or "",
                brand_name=item.get("brand_name") or "",
                packet_id=item.get("packet_id") or "",
            )
        )
        lines.append(f"  - task: {item.get('task') or ''}")
        lines.append(f"  - expected output: `{item.get('expected_output') or ''}`")
        lines.append(f"  - recompute: `{'yes' if item.get('requires_recompute') else 'no'}`")
        decisions = ", ".join(f"`{decision}`" for decision in item.get("allowed_decisions") or [])
        lines.append(f"  - decisions: {decisions}")
        for step in item.get("checklist") or []:
            lines.append(f"  - checklist: {step}")
    lines.extend(["", "## Adjudication Intake", ""])
    intake = report.get("adjudication_intake") or {}
    records = intake.get("records") or []
    if not records:
        lines.append("- None")
    else:
        lines.append(f"- Pending records: `{intake.get('pending_count', 0)}`")
        for key, value in (intake.get("expected_output_counts") or {}).items():
            lines.append(f"- `{key}`: `{value}`")
        for record in records[:10]:
            decisions = ", ".join(f"`{decision}`" for decision in record.get("allowed_decisions") or [])
            required = ", ".join(f"`{field}`" for field in record.get("required_fields") or [])
            lines.append(
                "- `{work_order_id}` · run `{run_id}` · decisions {decisions}".format(
                    work_order_id=record.get("work_order_id") or "",
                    run_id=record.get("run_id"),
                    decisions=decisions,
                )
            )
            lines.append(f"  - required: {required}")
    lines.extend(["", "## Top Review Reasons", ""])
    for key, value in (report.get("top_review_reasons") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Review Examples", ""])
    for reason, examples in (report.get("review_examples_by_reason") or {}).items():
        lines.append(f"### `{reason}`")
        for example in examples:
            lines.append(
                "- run `{run_id}` `{brand_name}` · `{feature_name}` · `{source_class}`: {text_preview}".format(
                    **example
                )
            )
        lines.append("")
    lines.extend(["", "## Top Rejected Reasons", ""])
    for key, value in (report.get("top_rejected_reasons") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Rejected Examples", ""])
    for reason, examples in (report.get("rejected_examples_by_reason") or {}).items():
        lines.append(f"### `{reason}`")
        for example in examples:
            lines.append(
                "- run `{run_id}` `{brand_name}` · `{feature_name}` · `{source_class}`: {text_preview}".format(
                    **example
                )
            )
        lines.append("")
    lines.extend(["", "## Runs", ""])
    lines.append("| Run | Brand | Status | Promotion | Audit | Accepted | Review | Rejected | Reclassified | Material Lost |")
    lines.append("| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for row in report.get("rows") or []:
        audit = "yes" if row.get("manual_audit_required") else "no"
        lines.append(
            "| {run_id} | {brand_name} | {status} | {promotion_status} | {audit} | {accepted} | {review_required} | {rejected} | {reclassified_to_noise} | {material_lost_fields} |".format(
                audit=audit,
                **row
            )
        )
    lines.extend(["", "## Recommendation", ""])
    for reason in recommendation.get("reason_codes") or []:
        lines.append(f"- `{reason}`")
    return "\n".join(lines).rstrip() + "\n"


def _print_changed_fields(comparison: dict[str, Any]) -> None:
    for field in comparison.get("fields") or []:
        if not field.get("changed"):
            continue
        name = field.get("field")
        if name not in {"offer", "audience", "outcome", "proof_points", "founder_or_press_context", "noise_rejected"}:
            continue
        print(f"  {name}:")
        print(f"    current: {field.get('legacy_preview') or '-'}")
        print(f"    vnext  : {field.get('graph_preview') or '-'}")


def _print_gate_reasons(gate: dict[str, Any]) -> None:
    review = _top_counts(gate.get("review_reason_counts") or {})
    rejected = _top_counts(gate.get("rejected_reason_counts") or {})
    if review:
        print("  review reasons:", ", ".join(f"{key}={value}" for key, value in review))
    if rejected:
        print("  rejected reasons:", ", ".join(f"{key}={value}" for key, value in rejected))


from src.research.evidence_vnext_report_workflow import (
    MANUAL_AUDIT_MATERIAL_FIELDS,
    PROMOTION_BLOCKING_REVIEW_REASONS,
    PROMOTION_MAX_LIMITED_MISSING_URL_COUNT,
    PROMOTION_MAX_LIMITED_REVIEW_COUNT,
    RESERVED_OR_PLACEHOLDER_ROOTS,
    RESERVED_OR_PLACEHOLDER_TLDS,
    _append_projected_reason_decision,
    _blocked_evidence_queue_item,
    _changed_material_field_previews,
    _compact_review_observations,
    _contract_projection_row,
    _contract_projection_summary,
    _contract_recommendations,
    _decision_action_counts,
    _decision_queue,
    _dominant_count_key,
    _is_projected_contract_filtered_observation,
    _is_projected_missing_url_contract_observation,
    _is_projected_social_placeholder_contract_observation,
    _intervention_packet,
    _intervention_packets,
    _intervention_profile,
    _manual_audit_profile,
    _manual_audit_queue_item,
    _material_quote_contract_queue_item,
    _observation_reason,
    _projected_applied_contracts,
    _projected_gate_summary,
    _provider_contract_is_implemented,
    _quote_material_impact,
    _quote_source_review_queue_item,
    _readiness_intervention_type,
    _readiness_matrix,
    _readiness_row,
    _removed_review_reason_counts,
    _review_material_overlaps,
    _run_manual_audit_decision,
    _run_promotion_decision,
    _shadow_policy_action_counts,
    _shadow_policy_next_action,
    _shadow_policy_runs,
    _social_placeholder_auto_cleared_runs,
    _promotion_after_manual_audit,
    _top_counts,
    _triage_actions,
    _unique,
    _work_order_expected_output,
    _work_orders,
)
