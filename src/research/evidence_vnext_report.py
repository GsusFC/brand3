from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


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
        "shadow_policy": {
            "policy": "strict_tone_consistency_source_url",
            "runtime_effect": False,
            "prompt_effect": False,
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


def _top_counts(counts: dict[str, Any], limit: int = 3) -> list[tuple[str, int]]:
    pairs = [(str(key), int(value or 0)) for key, value in counts.items()]
    return sorted(pairs, key=lambda item: (-item[1], item[0]))[:limit]


def _merge_counts(target: dict[str, int], source: dict[str, Any]) -> None:
    for key, value in source.items():
        target[str(key)] = target.get(str(key), 0) + int(value or 0)


def _run_promotion_decision(
    *,
    summary: dict[str, Any],
    gate: dict[str, Any],
    comparison: dict[str, Any],
    gate_payload: dict[str, Any] | None = None,
    vnext_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    review_reasons = {str(key): int(value or 0) for key, value in (gate.get("review_reason_counts") or {}).items()}
    review_count = int(gate.get("review_required_count") or 0)
    material_lost_count = int(summary.get("material_lost_count") or 0)
    missing_url_count = int(review_reasons.get("missing_evidence_url") or 0)
    placeholder_entity = _is_reserved_or_placeholder_entity(comparison)
    material_overlaps = _review_material_overlaps(
        gate_payload=gate_payload or {},
        vnext_pack=vnext_pack or {},
    )
    entity_profile_material_overlaps = [
        item
        for item in material_overlaps
        if item.get("classification_reason")
        in {"same_name_external_profile_not_alias", "same_name_external_profile_material_source"}
    ]
    missing_url_material_overlaps = [
        item
        for item in material_overlaps
        if item.get("classification_reason") == "missing_evidence_url"
    ]
    blocking_review_reasons = sorted(
        reason for reason in PROMOTION_BLOCKING_REVIEW_REASONS if review_reasons.get(reason, 0) > 0
    )
    reason_codes: list[str] = []

    if material_lost_count:
        reason_codes.append("material_lost_blocks_promotion")
    if placeholder_entity:
        reason_codes.append("reserved_or_placeholder_entity_blocks_promotion")
    if blocking_review_reasons:
        reason_codes.append("entity_boundary_review_blocks_promotion")
    if entity_profile_material_overlaps:
        reason_codes.append("entity_profile_review_in_material_fields_blocks_promotion")
    if missing_url_material_overlaps:
        reason_codes.append("material_quote_without_source_blocks_promotion")
    if missing_url_count > PROMOTION_MAX_LIMITED_MISSING_URL_COUNT:
        reason_codes.append("missing_evidence_url_above_threshold")
    if review_count > PROMOTION_MAX_LIMITED_REVIEW_COUNT:
        reason_codes.append("review_count_above_threshold")

    if (
        material_lost_count
        or placeholder_entity
        or blocking_review_reasons
        or entity_profile_material_overlaps
        or missing_url_material_overlaps
    ):
        status = "blocked"
    elif missing_url_count > PROMOTION_MAX_LIMITED_MISSING_URL_COUNT or review_count > PROMOTION_MAX_LIMITED_REVIEW_COUNT:
        status = "review_required"
    elif review_count:
        status = "limited_candidate"
        reason_codes.append("limited_review_pressure_present")
    else:
        status = "candidate"
        reason_codes.append("no_promotion_blockers_detected")

    return {
        "status": status,
        "reason_codes": reason_codes,
        "review_count": review_count,
        "missing_evidence_url_count": missing_url_count,
        "blocking_review_reasons": blocking_review_reasons,
        "material_overlaps": material_overlaps,
    }


def _is_reserved_or_placeholder_entity(comparison: dict[str, Any]) -> bool:
    host = _host(comparison.get("url") or "")
    brand = str(comparison.get("brand_name") or "").strip().lower().removeprefix("www.")
    root = _root_domain(host or brand)
    tld = root.rsplit(".", 1)[-1] if "." in root else root
    return root in RESERVED_OR_PLACEHOLDER_ROOTS or tld in RESERVED_OR_PLACEHOLDER_TLDS


def _run_manual_audit_decision(*, comparison: dict[str, Any], promotion: dict[str, Any]) -> dict[str, Any]:
    changed_material_fields = sorted(
        str(field.get("field") or "")
        for field in comparison.get("fields") or []
        if isinstance(field, dict)
        and field.get("changed")
        and str(field.get("field") or "") in MANUAL_AUDIT_MATERIAL_FIELDS
    )
    reason_codes: list[str] = []
    if promotion.get("status") == "limited_candidate" and changed_material_fields:
        reason_codes.append("limited_candidate_material_fields_changed")
    if promotion.get("status") == "limited_candidate" and promotion.get("review_count", 0):
        reason_codes.append("limited_candidate_review_pressure_present")
    if promotion.get("status") == "limited_candidate" and promotion.get("material_overlaps"):
        reason_codes.append("review_observations_overlap_material_fields")
    return {
        "required": bool(reason_codes),
        "reason_codes": reason_codes,
        "fields": changed_material_fields,
    }


def _manual_audit_queue_item(
    *,
    comparison: dict[str, Any],
    gate_payload: dict[str, Any],
    promotion: dict[str, Any],
    manual_audit: dict[str, Any],
) -> dict[str, Any]:
    audit_fields = set(str(field) for field in manual_audit.get("fields") or [])
    changed_material_fields = [
        {
            "field": str(field.get("field") or ""),
            "current_preview": _preview_text(field.get("legacy_preview"), limit=220),
            "vnext_preview": _preview_text(field.get("graph_preview"), limit=220),
        }
        for field in comparison.get("fields") or []
        if isinstance(field, dict) and str(field.get("field") or "") in audit_fields
    ]
    review_examples = [
        {
            "feature_name": str(item.get("feature_name") or ""),
            "provider": str(item.get("provider") or ""),
            "source_class": str(item.get("source_class") or ""),
            "eligibility": str(item.get("eligibility") or ""),
            "classification_reason": _observation_reason(item),
            "url": str(item.get("url") or ""),
            "text_preview": _preview_text(item.get("text"), limit=220),
        }
        for item in (gate_payload.get("review_required") or [])[:5]
        if isinstance(item, dict)
    ]
    triage_actions = _triage_actions(
        promotion_status=str(promotion.get("status") or ""),
        promotion_reason_codes=list(promotion.get("reason_codes") or []),
        review_examples=review_examples,
        review_material_overlaps=list(promotion.get("material_overlaps") or []),
        changed_material_fields=changed_material_fields,
    )
    audit_profile = _manual_audit_profile(
        review_examples=review_examples,
        review_material_overlaps=list(promotion.get("material_overlaps") or []),
        changed_material_fields=changed_material_fields,
    )
    return {
        "run_id": comparison.get("run_id"),
        "brand_name": comparison.get("brand_name") or "",
        "url": comparison.get("url") or "",
        "promotion_status": promotion.get("status") or "",
        "promotion_reason_codes": list(promotion.get("reason_codes") or []),
        "manual_audit_reason_codes": list(manual_audit.get("reason_codes") or []),
        "audit_verdict": audit_profile["verdict"],
        "audit_reason_codes": audit_profile["reason_codes"],
        "review_reason_codes": sorted(
            {
                item.get("classification_reason") or "unknown"
                for item in review_examples
                if isinstance(item, dict)
            }
        ),
        "review_material_overlaps": list(promotion.get("material_overlaps") or []),
        "changed_material_fields": changed_material_fields,
        "review_examples": review_examples,
        "triage_actions": triage_actions,
    }


def _manual_audit_profile(
    *,
    review_examples: list[dict[str, Any]],
    review_material_overlaps: list[dict[str, Any]],
    changed_material_fields: list[dict[str, Any]],
) -> dict[str, Any]:
    review_reasons = {str(item.get("classification_reason") or "") for item in review_examples}
    overlap_reasons = {str(item.get("classification_reason") or "") for item in review_material_overlaps}
    reason_codes: list[str] = []
    if changed_material_fields:
        reason_codes.append("material_fields_changed")
    if "missing_evidence_url" in review_reasons:
        reason_codes.append("url_less_quote_review_present")
    if "same_name_external_profile_not_alias" in review_reasons:
        reason_codes.append("external_profile_alias_review_present")
    if overlap_reasons:
        reason_codes.append("review_evidence_material_overlap_present")

    if "missing_evidence_url" in overlap_reasons:
        verdict = "blocked_material_quote_source"
    elif overlap_reasons.intersection({"same_name_external_profile_not_alias", "same_name_external_profile_material_source"}):
        verdict = "blocked_entity_alias_material_overlap"
    elif {"missing_evidence_url", "same_name_external_profile_not_alias"}.issubset(review_reasons):
        verdict = "quote_source_and_alias_review"
    elif "missing_evidence_url" in review_reasons:
        verdict = "quote_source_review"
    elif "same_name_external_profile_not_alias" in review_reasons:
        verdict = "alias_confirmation_review"
    elif changed_material_fields:
        verdict = "material_change_review"
    else:
        verdict = "no_manual_audit_needed"

    return {
        "verdict": verdict,
        "reason_codes": reason_codes or ["no_manual_audit_reasons_detected"],
    }


def _blocked_evidence_queue_item(*, comparison: dict[str, Any], promotion: dict[str, Any]) -> dict[str, Any]:
    overlaps = list(promotion.get("material_overlaps") or [])
    reason_codes = list(promotion.get("reason_codes") or [])
    return {
        "run_id": comparison.get("run_id"),
        "brand_name": comparison.get("brand_name") or "",
        "url": comparison.get("url") or "",
        "promotion_status": promotion.get("status") or "",
        "promotion_reason_codes": reason_codes,
        "review_material_overlaps": overlaps,
        "triage_actions": _triage_actions(
            promotion_status=str(promotion.get("status") or ""),
            promotion_reason_codes=reason_codes,
            review_examples=[],
            review_material_overlaps=overlaps,
            changed_material_fields=[],
        ),
    }


def _material_quote_contract_queue_item(*, comparison: dict[str, Any], promotion: dict[str, Any]) -> dict[str, Any]:
    violations = [
        item
        for item in promotion.get("material_overlaps") or []
        if item.get("classification_reason") == "missing_evidence_url"
    ]
    return {
        "run_id": comparison.get("run_id"),
        "brand_name": comparison.get("brand_name") or "",
        "url": comparison.get("url") or "",
        "promotion_status": promotion.get("status") or "",
        "violations": violations,
        "triage_actions": _triage_actions(
            promotion_status=str(promotion.get("status") or ""),
            promotion_reason_codes=list(promotion.get("reason_codes") or []),
            review_examples=[],
            review_material_overlaps=violations,
            changed_material_fields=[],
        ),
    }


def _quote_source_review_queue_item(
    *,
    comparison: dict[str, Any],
    gate_payload: dict[str, Any],
    promotion: dict[str, Any],
    manual_audit: dict[str, Any],
    current_pack: dict[str, Any],
    vnext_pack: dict[str, Any],
) -> dict[str, Any]:
    observations = [
        {
            "feature_name": str(item.get("feature_name") or ""),
            "provider": str(item.get("provider") or ""),
            "source_class": str(item.get("source_class") or ""),
            "eligibility": str(item.get("eligibility") or ""),
            "text_preview": _preview_text(item.get("text"), limit=220),
            **_quote_material_impact(item.get("text"), current_pack=current_pack, vnext_pack=vnext_pack),
        }
        for item in gate_payload.get("review_required") or []
        if isinstance(item, dict) and _observation_reason(item) == "missing_evidence_url"
    ]
    return {
        "run_id": comparison.get("run_id"),
        "brand_name": comparison.get("brand_name") or "",
        "url": comparison.get("url") or "",
        "promotion_status": promotion.get("status") or "",
        "manual_audit_required": bool(manual_audit.get("required")),
        "observations": observations,
    }


def _quote_material_impact(
    text: Any,
    *,
    current_pack: dict[str, Any],
    vnext_pack: dict[str, Any],
) -> dict[str, Any]:
    quote = _normalized_overlap_text(text)
    if len(quote) < 16:
        return {
            "material_impact": "unknown_short_quote",
            "current_material_fields": [],
            "vnext_material_fields": [],
        }
    current_fields = _material_fields_containing_quote(quote, current_pack)
    vnext_fields = _material_fields_containing_quote(quote, vnext_pack)
    if current_fields and not vnext_fields:
        impact = "removed_from_material_by_vnext"
    elif current_fields and vnext_fields:
        impact = "still_in_material"
    elif not current_fields and vnext_fields:
        impact = "added_to_vnext_material"
    else:
        impact = "review_only_not_material"
    return {
        "material_impact": impact,
        "current_material_fields": current_fields,
        "vnext_material_fields": vnext_fields,
    }


def _material_fields_containing_quote(quote: str, pack: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for field in MANUAL_AUDIT_MATERIAL_FIELDS:
        field_text = _pack_field_text(pack.get(field))
        if field_text and _text_overlaps_field(quote, field_text):
            fields.append(field)
    return sorted(fields)


def _contract_recommendations(
    *,
    quote_source_review_queue: list[dict[str, Any]],
    quote_source_material_impact_counts: dict[str, int],
) -> list[dict[str, Any]]:
    material_impacts = {
        "removed_from_material_by_vnext",
        "still_in_material",
        "added_to_vnext_material",
    }
    observations_by_feature: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in quote_source_review_queue:
        for observation in item.get("observations") or []:
            if not isinstance(observation, dict):
                continue
            if observation.get("material_impact") not in material_impacts:
                continue
            key = (
                str(observation.get("feature_name") or "unknown_feature"),
                str(observation.get("provider") or "unknown_provider"),
            )
            observations_by_feature.setdefault(key, []).append(
                {
                    "run_id": item.get("run_id"),
                    "brand_name": item.get("brand_name") or "",
                    "promotion_status": item.get("promotion_status") or "",
                    "text_preview": observation.get("text_preview") or "",
                    "material_impact": observation.get("material_impact") or "",
                    "current_material_fields": list(observation.get("current_material_fields") or []),
                    "vnext_material_fields": list(observation.get("vnext_material_fields") or []),
                }
            )
    recommendations: list[dict[str, Any]] = []
    removed_count = int(quote_source_material_impact_counts.get("removed_from_material_by_vnext") or 0)
    still_count = int(quote_source_material_impact_counts.get("still_in_material") or 0)
    for (feature_name, provider), observations in sorted(observations_by_feature.items()):
        reason_codes = ["missing_source_url_in_material_quote"]
        if removed_count:
            reason_codes.append("vnext_removed_unsourced_quote_from_material_fields")
        if still_count:
            reason_codes.append("unsourced_quote_still_in_material_fields")
        severity = "high" if still_count or removed_count else "medium"
        recommendations.append(
            {
                "contract": f"{feature_name}.source_url",
                "feature_name": feature_name,
                "provider": provider,
                "severity": severity,
                "recommended_action": "require_source_url_or_exclude_from_material_evidence",
                "reason_codes": reason_codes,
                "affected_observation_count": len(observations),
                "affected_runs": sorted(
                    {int(item["run_id"]) for item in observations if item.get("run_id") is not None},
                    reverse=True,
                ),
                "examples": observations[:5],
            }
        )
    return recommendations


def _contract_projection_row(
    *,
    comparison: dict[str, Any],
    summary: dict[str, Any],
    gate: dict[str, Any],
    gate_payload: dict[str, Any],
    current_promotion: dict[str, Any],
    current_manual_audit: dict[str, Any],
    vnext_pack: dict[str, Any],
) -> dict[str, Any]:
    material_overlaps = _review_material_overlaps(
        gate_payload=gate_payload or {},
        vnext_pack=vnext_pack or {},
    )
    removed_review = [
        item
        for item in gate_payload.get("review_required") or []
        if isinstance(item, dict)
        and _is_projected_contract_filtered_observation(item, material_overlaps=material_overlaps)
    ]
    filtered_review_required = [
        item
        for item in gate_payload.get("review_required") or []
        if not (
            isinstance(item, dict)
            and _is_projected_contract_filtered_observation(item, material_overlaps=material_overlaps)
        )
    ]
    projected_gate_payload = {
        **gate_payload,
        "review_required": filtered_review_required,
    }
    projected_gate = _projected_gate_summary(gate, removed_review)
    projected_promotion = _run_promotion_decision(
        summary=summary,
        gate=projected_gate,
        comparison=comparison,
        gate_payload=projected_gate_payload,
        vnext_pack=vnext_pack,
    )
    projected_manual_audit = _run_manual_audit_decision(comparison=comparison, promotion=projected_promotion)
    projected_promotion = _promotion_after_manual_audit(
        promotion=projected_promotion,
        manual_audit=projected_manual_audit,
    )
    return {
        "run_id": comparison.get("run_id"),
        "brand_name": comparison.get("brand_name") or "",
        "url": comparison.get("url") or "",
        "applied_contracts": _projected_applied_contracts(removed_review),
        "removed_review_observation_count": len(removed_review),
        "removed_review_reason_counts": _removed_review_reason_counts(removed_review),
        "current_promotion_status": current_promotion.get("status") or "",
        "projected_promotion_status": projected_promotion.get("status") or "",
        "current_manual_audit_required": bool(current_manual_audit.get("required")),
        "projected_manual_audit_required": bool(projected_manual_audit.get("required")),
        "projected_promotion_reason_codes": list(projected_promotion.get("reason_codes") or []),
        "projected_manual_audit_reason_codes": list(projected_manual_audit.get("reason_codes") or []),
    }


def _contract_projection_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    projected_promotion_counts: dict[str, int] = {}
    projected_manual_audit_counts: dict[str, int] = {"required": 0, "not_required": 0}
    applied_contracts: set[str] = set()
    removed_count = 0
    transitions: list[dict[str, Any]] = []
    for row in rows:
        status = str(row.get("projected_promotion_status") or "unknown")
        projected_promotion_counts[status] = projected_promotion_counts.get(status, 0) + 1
        projected_manual_audit_counts["required" if row.get("projected_manual_audit_required") else "not_required"] += 1
        removed_count += int(row.get("removed_review_observation_count") or 0)
        applied_contracts.update(str(item) for item in row.get("applied_contracts") or [])
        if row.get("current_promotion_status") != row.get("projected_promotion_status"):
            transitions.append(row)
    return {
        "applied_contracts": sorted(applied_contracts),
        "removed_review_observation_count": removed_count,
        "projected_promotion_counts": dict(sorted(projected_promotion_counts.items())),
        "projected_manual_audit_counts": dict(sorted(projected_manual_audit_counts.items())),
        "status_transitions": transitions,
        "rows": rows,
    }


def _is_projected_contract_filtered_observation(
    item: dict[str, Any],
    *,
    material_overlaps: list[dict[str, Any]],
) -> bool:
    return _is_projected_missing_url_contract_observation(item) or _is_projected_social_placeholder_contract_observation(
        item,
        material_overlaps=material_overlaps,
    )


def _is_projected_missing_url_contract_observation(item: dict[str, Any]) -> bool:
    return (
        _observation_reason(item) == "missing_evidence_url"
        and str(item.get("feature_name") or "") == "tone_consistency"
        and not str(item.get("url") or "").strip()
    )


def _is_projected_social_placeholder_contract_observation(
    item: dict[str, Any],
    *,
    material_overlaps: list[dict[str, Any]],
) -> bool:
    if _observation_reason(item) != "same_name_external_profile_not_alias":
        return False
    if str(item.get("provider") or "") != "social_scrape":
        return False
    text = str(item.get("text") or item.get("text_preview") or "").strip().lower()
    if "profile candidate" not in text:
        return False
    item_url = str(item.get("url") or "").strip()
    if not item_url:
        return False
    item_url_key = _url_identity(item_url)
    for overlap in material_overlaps:
        if _observation_reason(overlap) != "same_name_external_profile_not_alias":
            continue
        if item_url_key and _url_identity(str(overlap.get("url") or "")) == item_url_key:
            return False
    return True


def _projected_applied_contracts(removed_review: list[dict[str, Any]]) -> list[str]:
    contracts: set[str] = set()
    for item in removed_review:
        if _is_projected_missing_url_contract_observation(item):
            contracts.add("tone_consistency.source_url")
        elif _is_projected_social_placeholder_contract_observation(item, material_overlaps=[]):
            contracts.add("social_scrape.placeholder_profile_non_material")
    return sorted(contracts)


def _projected_gate_summary(gate: dict[str, Any], removed_review: list[dict[str, Any]]) -> dict[str, Any]:
    projected = dict(gate)
    projected["review_required_count"] = max(0, int(gate.get("review_required_count") or 0) - len(removed_review))
    review_reason_counts = {str(key): int(value or 0) for key, value in (gate.get("review_reason_counts") or {}).items()}
    for reason, count in _removed_review_reason_counts(removed_review).items():
        next_count = review_reason_counts.get(reason, 0) - count
        if next_count > 0:
            review_reason_counts[reason] = next_count
        else:
            review_reason_counts.pop(reason, None)
    projected["review_reason_counts"] = dict(sorted(review_reason_counts.items()))
    return projected


def _removed_review_reason_counts(removed_review: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in removed_review:
        reason = _observation_reason(item)
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _decision_queue(
    *,
    contract_recommendations: list[dict[str, Any]],
    provider_acquisition_contracts: list[dict[str, Any]],
    contract_projection: dict[str, Any],
    manual_audit_queue: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for item in contract_recommendations:
        decisions.append(
            {
                "action": "implement_contract_recommendation",
                "priority": str(item.get("severity") or "medium"),
                "affected_runs": list(item.get("affected_runs") or []),
                "contract": item.get("contract") or "",
                "reason_codes": list(item.get("reason_codes") or []),
                "recommended_action": item.get("recommended_action") or "",
            }
        )
    for item in provider_acquisition_contracts:
        decisions.append(
            {
                "action": "implement_provider_acquisition_contract",
                "priority": str(item.get("severity") or "medium"),
                "affected_runs": [],
                "contract": item.get("contract") or "",
                "provider": item.get("provider") or "",
                "affected_observation_count": int(item.get("affected_observation_count") or 0),
                "reason_codes": list(item.get("reason_codes") or []),
                "recommended_action": item.get("recommended_action") or "",
            }
        )

    projected_rows = list(contract_projection.get("rows") or [])
    projected_manual_runs = [
        int(row.get("run_id"))
        for row in projected_rows
        if row.get("run_id") is not None and row.get("projected_manual_audit_required")
    ]
    if projected_manual_runs:
        decisions.append(
            {
                "action": "manual_audit_projected_material_changes",
                "priority": "high",
                "affected_runs": sorted(set(projected_manual_runs), reverse=True),
                "reason_codes": ["projected_manual_audit_required"],
            }
        )

    _append_projected_reason_decision(
        decisions,
        projected_rows,
        reason_code="entity_boundary_review_blocks_promotion",
        action="resolve_entity_boundary_before_promotion",
        priority="high",
    )
    _append_projected_reason_decision(
        decisions,
        projected_rows,
        reason_code="reserved_or_placeholder_entity_blocks_promotion",
        action="exclude_placeholder_entity_from_promotion",
        priority="high",
    )
    _append_projected_reason_decision(
        decisions,
        projected_rows,
        reason_code="entity_profile_review_in_material_fields_blocks_promotion",
        action="confirm_entity_alias_before_promotion",
        priority="high",
    )

    alias_audit_runs = [
        int(item.get("run_id"))
        for item in manual_audit_queue
        if item.get("run_id") is not None and "confirm_external_profile_alias" in set(item.get("triage_actions") or [])
    ]
    if alias_audit_runs:
        decisions.append(
            {
                "action": "confirm_external_profile_alias_for_audit_runs",
                "priority": "medium",
                "affected_runs": sorted(set(alias_audit_runs), reverse=True),
                "reason_codes": ["external_profile_alias_review_present"],
            }
        )

    return decisions


def _append_projected_reason_decision(
    decisions: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    reason_code: str,
    action: str,
    priority: str,
) -> None:
    affected_runs = [
        int(row.get("run_id"))
        for row in rows
        if row.get("run_id") is not None and reason_code in set(row.get("projected_promotion_reason_codes") or [])
    ]
    if not affected_runs:
        return
    decisions.append(
        {
            "action": action,
            "priority": priority,
            "affected_runs": sorted(set(affected_runs), reverse=True),
            "reason_codes": [reason_code],
        }
    )


def _decision_action_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in decisions:
        action = str(item.get("action") or "unknown")
        affected_runs = list(item.get("affected_runs") or [])
        count = len(affected_runs)
        if count == 0:
            count = int(item.get("affected_observation_count") or 0)
        counts[action] = counts.get(action, 0) + count
    return dict(sorted(counts.items()))


def _shadow_policy_runs(projected_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for row in projected_rows:
        remaining_reason_codes = list(row.get("projected_promotion_reason_codes") or [])
        next_action = _shadow_policy_next_action(
            projected_status=str(row.get("projected_promotion_status") or ""),
            projected_manual_audit_required=bool(row.get("projected_manual_audit_required")),
            remaining_reason_codes=remaining_reason_codes,
        )
        removed_review_count = int(row.get("removed_review_observation_count") or 0)
        runs.append(
            {
                "run_id": row.get("run_id"),
                "brand_name": row.get("brand_name") or "",
                "url": row.get("url") or "",
                "contract_effect": "removes_review_observations" if removed_review_count else "no_direct_contract_effect",
                "removed_review_observation_count": removed_review_count,
                "current_promotion_status": row.get("current_promotion_status") or "",
                "projected_promotion_status": row.get("projected_promotion_status") or "",
                "status_transition": row.get("current_promotion_status") != row.get("projected_promotion_status"),
                "projected_manual_audit_required": bool(row.get("projected_manual_audit_required")),
                "projected_manual_audit_reason_codes": list(row.get("projected_manual_audit_reason_codes") or []),
                "remaining_reason_codes": remaining_reason_codes,
                "next_action": next_action,
                "human_required": next_action
                not in {"candidate_after_contract", "candidate_without_contract_effect"},
            }
        )
    return runs


def _shadow_policy_next_action(
    *,
    projected_status: str,
    projected_manual_audit_required: bool,
    remaining_reason_codes: list[str],
) -> str:
    reasons = set(remaining_reason_codes)
    if "entity_boundary_review_blocks_promotion" in reasons:
        return "resolve_entity_boundary_before_promotion"
    if "reserved_or_placeholder_entity_blocks_promotion" in reasons:
        return "exclude_placeholder_entity_from_promotion"
    if "entity_profile_review_in_material_fields_blocks_promotion" in reasons:
        return "confirm_entity_alias_before_promotion"
    if "material_quote_without_source_blocks_promotion" in reasons:
        return "add_source_url_or_remove_material_quote"
    if "material_lost_blocks_promotion" in reasons:
        return "review_material_loss_before_promotion"
    if projected_manual_audit_required:
        return "manual_audit_projected_material_changes"
    if projected_status == "review_required":
        return "reduce_review_pressure_before_promotion"
    if projected_status == "candidate":
        return "candidate_after_contract"
    return "candidate_without_contract_effect"


def _shadow_policy_action_counts(runs: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in runs:
        action = str(item.get("next_action") or "unknown")
        counts[action] = counts.get(action, 0) + 1
    return dict(sorted(counts.items()))


def _readiness_matrix(shadow_policy_runs: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_readiness_row(item) for item in shadow_policy_runs]
    counts: dict[str, int] = {}
    for row in rows:
        for key in {
            f"readiness:{row['readiness_status']}",
            f"intervention:{row['intervention_type']}",
            f"automation:{row['automation_lane']}",
        }:
            counts[key] = counts.get(key, 0) + 1
    return {
        "counts": dict(sorted(counts.items())),
        "rows": rows,
    }


def _readiness_row(shadow_run: dict[str, Any]) -> dict[str, Any]:
    projected_status = str(shadow_run.get("projected_promotion_status") or "unknown")
    next_action = str(shadow_run.get("next_action") or "unknown")
    contract_effect = str(shadow_run.get("contract_effect") or "")
    human_required = bool(shadow_run.get("human_required"))
    intervention_type = _readiness_intervention_type(next_action)
    if projected_status == "candidate" and not human_required:
        readiness_status = "ready_after_shadow_policy"
    elif projected_status == "audit_required":
        readiness_status = "needs_manual_audit"
    elif projected_status == "blocked":
        readiness_status = "blocked_after_shadow_policy"
    else:
        readiness_status = "needs_review"
    if not human_required and contract_effect == "removes_review_observations":
        automation_lane = "contract_can_auto_clear"
    elif not human_required:
        automation_lane = "no_action_needed"
    elif contract_effect == "removes_review_observations":
        automation_lane = "contract_then_human_review"
    else:
        automation_lane = "human_review_only"
    return {
        "run_id": shadow_run.get("run_id"),
        "brand_name": shadow_run.get("brand_name") or "",
        "url": shadow_run.get("url") or "",
        "current_promotion_status": shadow_run.get("current_promotion_status") or "",
        "projected_promotion_status": projected_status,
        "readiness_status": readiness_status,
        "intervention_type": intervention_type,
        "automation_lane": automation_lane,
        "contract_effect": contract_effect,
        "status_transition": bool(shadow_run.get("status_transition")),
        "human_required": human_required,
        "next_action": next_action,
        "remaining_reason_codes": list(shadow_run.get("remaining_reason_codes") or []),
    }


def _readiness_intervention_type(next_action: str) -> str:
    if next_action == "manual_audit_projected_material_changes":
        return "material_audit"
    if next_action == "resolve_entity_boundary_before_promotion":
        return "entity_boundary"
    if next_action == "exclude_placeholder_entity_from_promotion":
        return "placeholder_exclusion"
    if next_action == "confirm_entity_alias_before_promotion":
        return "entity_alias_confirmation"
    if next_action == "add_source_url_or_remove_material_quote":
        return "quote_source_contract"
    if next_action == "review_material_loss_before_promotion":
        return "material_loss_review"
    if next_action == "reduce_review_pressure_before_promotion":
        return "review_pressure_reduction"
    if next_action in {"candidate_after_contract", "candidate_without_contract_effect"}:
        return "none"
    return "unknown"


def _intervention_packets(readiness_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in readiness_rows:
        grouped.setdefault(str(row.get("intervention_type") or "unknown"), []).append(row)
    packets = [_intervention_packet(kind, rows) for kind, rows in grouped.items()]
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        packets,
        key=lambda item: (
            priority_order.get(str(item.get("priority") or "low"), 9),
            str(item.get("packet_id") or ""),
        ),
    )


def _intervention_packet(intervention_type: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    profile = _intervention_profile(intervention_type)
    reason_counts: dict[str, int] = {}
    automation_lanes: dict[str, int] = {}
    for row in rows:
        automation = str(row.get("automation_lane") or "unknown")
        automation_lanes[automation] = automation_lanes.get(automation, 0) + 1
        for reason in row.get("remaining_reason_codes") or []:
            reason_key = str(reason)
            reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1
    affected_runs = sorted(
        {int(row["run_id"]) for row in rows if row.get("run_id") is not None},
        reverse=True,
    )
    dominant_lane = _dominant_count_key(automation_lanes)
    return {
        "packet_id": f"intervention:{intervention_type}",
        "title": profile["title"],
        "priority": profile["priority"],
        "intervention_type": intervention_type,
        "affected_runs": affected_runs,
        "affected_run_count": len(affected_runs),
        "automation_lane": dominant_lane,
        "automation_lane_counts": dict(sorted(automation_lanes.items())),
        "dominant_reason_codes": [
            reason for reason, _count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        ],
        "closure_criteria": profile["closure_criteria"],
        "checklist": list(profile.get("checklist") or []),
        "allowed_decisions": list(profile.get("allowed_decisions") or []),
        "decision_required_fields": list(profile.get("decision_required_fields") or []),
        "promotion_after_closure": profile["promotion_after_closure"],
        "human_required": any(bool(row.get("human_required")) for row in rows),
        "runs": [
            {
                "run_id": row.get("run_id"),
                "brand_name": row.get("brand_name") or "",
                "current_promotion_status": row.get("current_promotion_status") or "",
                "projected_promotion_status": row.get("projected_promotion_status") or "",
                "automation_lane": row.get("automation_lane") or "",
                "next_action": row.get("next_action") or "",
            }
            for row in rows
        ],
    }


def _intervention_profile(intervention_type: str) -> dict[str, Any]:
    profiles = {
        "material_audit": {
            "title": "Review changed material evidence after strict source contract",
            "priority": "high",
            "closure_criteria": "Approve vNext material fields or mark the run for evidence correction.",
            "promotion_after_closure": "candidate_if_no_new_blockers",
            "checklist": [
                "Review changed proof/context fields against accepted vNext evidence.",
                "Confirm no unresolved profile or URL-less quote remains in material fields.",
                "Record approve_vnext_material or send_back_for_evidence_correction.",
            ],
            "allowed_decisions": ["approve_vnext_material", "send_back_for_evidence_correction"],
            "decision_required_fields": ["decision", "reviewer", "rationale", "approved_material_fields"],
        },
        "entity_boundary": {
            "title": "Resolve same-name or different-root entity boundary",
            "priority": "high",
            "closure_criteria": "Confirm the external evidence belongs to the audited entity or quarantine it.",
            "promotion_after_closure": "recompute_required",
            "checklist": [
                "Compare audited root, external root, company name, and source context.",
                "Mark evidence as entity_alias_confirmed or quarantine_related_unresolved.",
                "Recompute promotion state after adjudication.",
            ],
            "allowed_decisions": ["entity_alias_confirmed", "quarantine_related_unresolved"],
            "decision_required_fields": [
                "decision",
                "reviewer",
                "rationale",
                "confirmed_entity_root",
                "quarantined_source_urls",
            ],
        },
        "placeholder_exclusion": {
            "title": "Exclude reserved or placeholder entities from promotion",
            "priority": "high",
            "closure_criteria": "Confirm the run target is a placeholder/reserved domain and keep it non-promotable.",
            "promotion_after_closure": "blocked_by_policy",
            "checklist": [
                "Confirm target root is reserved, placeholder, or invalid for promotion.",
                "Keep run non-promotable regardless of accepted evidence volume.",
                "Record exclusion reason for audit trail.",
            ],
            "allowed_decisions": ["confirm_policy_exclusion"],
            "decision_required_fields": ["decision", "reviewer", "rationale", "policy_reason"],
        },
        "entity_alias_confirmation": {
            "title": "Confirm unresolved external profile alias in material evidence",
            "priority": "high",
            "closure_criteria": "Confirm alias ownership or remove/quarantine material claims sourced from the profile.",
            "promotion_after_closure": "recompute_required",
            "checklist": [
                "Verify external profile ownership against audited entity identity.",
                "If unconfirmed, remove or quarantine material claims sourced from that profile.",
                "Recompute promotion state after profile adjudication.",
            ],
            "allowed_decisions": ["external_profile_alias_confirmed", "quarantine_profile_material_claims"],
            "decision_required_fields": [
                "decision",
                "reviewer",
                "rationale",
                "profile_url",
                "affected_material_fields",
            ],
        },
        "quote_source_contract": {
            "title": "Attach source URL or remove material quote",
            "priority": "high",
            "closure_criteria": "Every material quote has a source URL or is excluded from material evidence.",
            "promotion_after_closure": "recompute_required",
            "checklist": [
                "Attach a source URL to each material quote or remove it from material fields.",
                "Reject inferred quote sources when multiple roots could match.",
                "Recompute promotion state after quote cleanup.",
            ],
            "allowed_decisions": ["source_url_attached", "exclude_unsourced_quote"],
            "decision_required_fields": ["decision", "reviewer", "rationale", "quote_text", "source_url"],
        },
        "review_pressure_reduction": {
            "title": "Reduce residual review pressure",
            "priority": "medium",
            "closure_criteria": "Review-required observations fall within limited-candidate thresholds.",
            "promotion_after_closure": "candidate_if_no_new_blockers",
            "checklist": [
                "Resolve or quarantine review-required observations above threshold.",
                "Confirm no material blockers remain.",
                "Recompute readiness after review pressure drops.",
            ],
            "allowed_decisions": ["review_observations_resolved", "keep_review_required"],
            "decision_required_fields": ["decision", "reviewer", "rationale", "resolved_reason_codes"],
        },
        "none": {
            "title": "No intervention required",
            "priority": "low",
            "closure_criteria": "No blockers detected under the shadow policy.",
            "promotion_after_closure": "candidate",
            "checklist": [
                "No manual work required.",
            ],
            "allowed_decisions": ["no_action_required"],
            "decision_required_fields": ["decision"],
        },
    }
    return profiles.get(
        intervention_type,
        {
            "title": "Unknown intervention",
            "priority": "medium",
            "closure_criteria": "Classify the unresolved intervention before promotion.",
            "promotion_after_closure": "recompute_required",
            "checklist": [
                "Classify unresolved intervention type.",
                "Define closure criteria before promotion.",
            ],
            "allowed_decisions": ["classify_intervention"],
            "decision_required_fields": ["decision", "reviewer", "rationale"],
        },
    )


def _dominant_count_key(counts: dict[str, int]) -> str:
    if not counts:
        return "unknown"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _work_orders(intervention_packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    for packet in intervention_packets:
        if not packet.get("human_required"):
            continue
        for run in packet.get("runs") or []:
            run_id = run.get("run_id")
            if run_id is None:
                continue
            orders.append(
                {
                    "work_order_id": f"workorder:{packet.get('intervention_type') or 'unknown'}:{run_id}",
                    "packet_id": packet.get("packet_id") or "",
                    "run_id": run_id,
                    "brand_name": run.get("brand_name") or "",
                    "task": packet.get("title") or "",
                    "priority": packet.get("priority") or "",
                    "automation_lane": run.get("automation_lane") or packet.get("automation_lane") or "",
                    "current_promotion_status": run.get("current_promotion_status") or "",
                    "projected_promotion_status": run.get("projected_promotion_status") or "",
                    "next_action": run.get("next_action") or "",
                    "closure_criteria": packet.get("closure_criteria") or "",
                    "checklist": list(packet.get("checklist") or []),
                    "allowed_decisions": list(packet.get("allowed_decisions") or []),
                    "decision_required_fields": list(packet.get("decision_required_fields") or []),
                    "decision_record_template": _decision_record_template(
                        run_id=run_id,
                        work_order_id=f"workorder:{packet.get('intervention_type') or 'unknown'}:{run_id}",
                        packet=packet,
                    ),
                    "expected_output": _work_order_expected_output(str(packet.get("promotion_after_closure") or "")),
                    "requires_recompute": packet.get("promotion_after_closure") == "recompute_required",
                    "promotion_after_closure": packet.get("promotion_after_closure") or "",
                }
            )
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        orders,
        key=lambda item: (
            priority_order.get(str(item.get("priority") or "low"), 9),
            str(item.get("packet_id") or ""),
            -int(item.get("run_id") or 0),
        ),
    )


def _work_order_expected_output(promotion_after_closure: str) -> str:
    if promotion_after_closure == "candidate_if_no_new_blockers":
        return "manual_decision"
    if promotion_after_closure == "blocked_by_policy":
        return "policy_exclusion"
    if promotion_after_closure == "candidate":
        return "candidate"
    if promotion_after_closure == "recompute_required":
        return "adjudication_then_recompute"
    return "manual_decision"


def _decision_record_template(*, run_id: Any, work_order_id: str, packet: dict[str, Any]) -> dict[str, Any]:
    template: dict[str, Any] = {
        "work_order_id": work_order_id,
        "run_id": run_id,
        "decision": "",
        "reviewer": "",
        "rationale": "",
    }
    for field in packet.get("decision_required_fields") or []:
        template.setdefault(str(field), "")
    return template


def _adjudication_intake(work_orders: list[dict[str, Any]]) -> dict[str, Any]:
    records = [_adjudication_record(order) for order in work_orders]
    expected_output_counts: dict[str, int] = {}
    packet_counts: dict[str, int] = {}
    for record in records:
        expected = str(record.get("expected_output") or "unknown")
        expected_output_counts[expected] = expected_output_counts.get(expected, 0) + 1
        packet = str(record.get("packet_id") or "unknown")
        packet_counts[packet] = packet_counts.get(packet, 0) + 1
    return {
        "status": "pending_decisions" if records else "empty",
        "pending_count": len(records),
        "expected_output_counts": dict(sorted(expected_output_counts.items())),
        "packet_counts": dict(sorted(packet_counts.items())),
        "records": records,
    }


def _adjudication_record(work_order: dict[str, Any]) -> dict[str, Any]:
    return {
        "work_order_id": work_order.get("work_order_id") or "",
        "packet_id": work_order.get("packet_id") or "",
        "run_id": work_order.get("run_id"),
        "brand_name": work_order.get("brand_name") or "",
        "status": "pending_decision",
        "expected_output": work_order.get("expected_output") or "",
        "requires_recompute": bool(work_order.get("requires_recompute")),
        "allowed_decisions": list(work_order.get("allowed_decisions") or []),
        "required_fields": list(work_order.get("decision_required_fields") or []),
        "record": dict(work_order.get("decision_record_template") or {}),
    }


def _triage_actions(
    *,
    promotion_status: str,
    promotion_reason_codes: list[str],
    review_examples: list[dict[str, Any]],
    review_material_overlaps: list[dict[str, Any]],
    changed_material_fields: list[dict[str, Any]],
) -> list[str]:
    actions: list[str] = []
    overlap_reasons = {str(item.get("classification_reason") or "") for item in review_material_overlaps}
    review_reasons = {str(item.get("classification_reason") or "") for item in review_examples}
    reason_codes = set(str(reason) for reason in promotion_reason_codes)
    if changed_material_fields:
        actions.append("review_material_field_changes")
    if "missing_evidence_url" in overlap_reasons:
        actions.append("add_source_url_or_remove_material_quote")
    elif "missing_evidence_url" in review_reasons:
        actions.append("add_source_url_or_keep_quote_review_gated")
    if overlap_reasons.intersection({"same_name_external_profile_not_alias", "same_name_external_profile_material_source"}):
        actions.append("confirm_entity_alias_before_promotion")
    elif "same_name_external_profile_not_alias" in review_reasons:
        actions.append("confirm_external_profile_alias")
    if "entity_boundary_review_blocks_promotion" in reason_codes:
        actions.append("resolve_entity_boundary_before_promotion")
    if "reserved_or_placeholder_entity_blocks_promotion" in reason_codes:
        actions.append("exclude_placeholder_entity_from_promotion")
    if promotion_status == "blocked":
        actions.append("keep_blocked_until_triage_resolved")
    return _unique(actions)


def _promotion_after_manual_audit(*, promotion: dict[str, Any], manual_audit: dict[str, Any]) -> dict[str, Any]:
    if promotion.get("status") != "limited_candidate" or not manual_audit.get("required"):
        return promotion
    reason_codes = list(promotion.get("reason_codes") or [])
    reason_codes.append("manual_audit_required_for_material_field_changes")
    return {
        **promotion,
        "status": "audit_required",
        "reason_codes": reason_codes,
    }


def _accumulate_acquisition_matrix(
    *,
    provider_rows: dict[str, dict[str, Any]],
    source_class_rows: dict[str, dict[str, Any]],
    gate_payload: dict[str, Any],
) -> None:
    for status_key in ("accepted", "review_required", "rejected"):
        observations = gate_payload.get(status_key) or []
        if not isinstance(observations, list):
            continue
        for item in observations:
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider") or "unknown_provider")
            source_class = str(item.get("source_class") or "unknown_source")
            reason = _observation_reason(item) if status_key != "accepted" else "accepted"
            _increment_acquisition_row(
                rows=provider_rows,
                key=provider,
                key_field="provider",
                status_key=status_key,
                reason=reason,
                peer_field="source_classes",
                peer_value=source_class,
            )
            _increment_acquisition_row(
                rows=source_class_rows,
                key=source_class,
                key_field="source_class",
                status_key=status_key,
                reason=reason,
                peer_field="providers",
                peer_value=provider,
            )


def _accumulate_acquisition_contract_exclusions(*, target: dict[str, Any], payload: dict[str, Any]) -> None:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    target["total"] = int(target.get("total") or 0) + int(summary.get("excluded_count") or 0)
    for source_key, target_key in (
        ("exclusion_counts_by_contract", "by_contract"),
        ("exclusion_counts_by_surface", "by_surface"),
        ("exclusion_counts_by_feature", "by_feature"),
    ):
        counts = summary.get(source_key) if isinstance(summary.get(source_key), dict) else {}
        bucket = target.setdefault(target_key, {})
        for key, value in counts.items():
            bucket[str(key)] = int(bucket.get(str(key)) or 0) + int(value or 0)
        target[target_key] = dict(sorted(bucket.items()))


def _accumulate_semantic_evidence(
    *,
    target: dict[str, Any],
    payload: dict[str, Any],
    run_id: int | None,
    brand_name: str,
) -> None:
    if not payload:
        return
    classifier = str(payload.get("classifier") or "")
    if classifier:
        target["classifier"] = classifier
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    target["accepted_material"] = int(target.get("accepted_material") or 0) + int(
        summary.get("accepted_material_count") or 0
    )
    target["accepted_weak"] = int(target.get("accepted_weak") or 0) + int(summary.get("accepted_weak_count") or 0)
    for source_key, target_key in (
        ("semantic_class_counts", "semantic_class_counts"),
        ("materiality_counts", "materiality_counts"),
        ("entity_fit_counts", "entity_fit_counts"),
    ):
        counts = summary.get(source_key) if isinstance(summary.get(source_key), dict) else {}
        bucket = target.setdefault(target_key, {})
        for key, value in counts.items():
            bucket[str(key)] = int(bucket.get(str(key)) or 0) + int(value or 0)
        target[target_key] = dict(sorted(bucket.items()))
    weak_examples = target.setdefault("weak_examples", [])
    for item in payload.get("assessments") or []:
        if not isinstance(item, dict):
            continue
        if item.get("gate_status") != "accepted" or item.get("materiality") != "low":
            continue
        weak_examples.append(
            {
                "run_id": run_id,
                "brand_name": brand_name,
                "semantic_class": item.get("semantic_class") or "",
                "entity_fit": item.get("entity_fit") or "",
                "url": item.get("url") or "",
                "text_preview": item.get("text_preview") or "",
                "reason_codes": list(item.get("reason_codes") or []),
            }
        )
    target["weak_examples"] = weak_examples[:20]


def _accumulate_semantic_llm_comparison(
    *,
    target: dict[str, Any],
    heuristic: dict[str, Any],
    llm: dict[str, Any],
    run_id: int | None,
    brand_name: str,
) -> None:
    status = str(llm.get("status") or "missing")
    status_counts = target.setdefault("status_counts", {})
    status_counts[status] = int(status_counts.get(status) or 0) + 1
    target["status_counts"] = dict(sorted(status_counts.items()))
    model = str(llm.get("model") or "")
    if model:
        models = target.setdefault("models", {})
        models[model] = int(models.get(model) or 0) + 1
        target["models"] = dict(sorted(models.items()))

    heuristic_by_id = {
        str(item.get("observation_id") or ""): item
        for item in heuristic.get("assessments") or []
        if isinstance(item, dict)
    }
    llm_rows = [item for item in llm.get("assessments") or [] if isinstance(item, dict)]
    semantic_disagreements = 0
    materiality_disagreements = 0
    examples: list[dict[str, Any]] = []
    for item in llm_rows:
        observation_id = str(item.get("observation_id") or "")
        baseline = heuristic_by_id.get(observation_id)
        if not baseline:
            continue
        class_changed = item.get("semantic_class") != baseline.get("semantic_class")
        materiality_changed = item.get("materiality") != baseline.get("materiality")
        if class_changed:
            semantic_disagreements += 1
        if materiality_changed:
            materiality_disagreements += 1
        if class_changed or materiality_changed:
            examples.append(
                {
                    "observation_id": observation_id,
                    "heuristic_class": baseline.get("semantic_class") or "",
                    "llm_class": item.get("semantic_class") or "",
                    "heuristic_materiality": baseline.get("materiality") or "",
                    "llm_materiality": item.get("materiality") or "",
                    "llm_reason_codes": list(item.get("reason_codes") or []),
                }
            )
    target["semantic_class_disagreement_count"] = int(target.get("semantic_class_disagreement_count") or 0) + semantic_disagreements
    target["materiality_disagreement_count"] = int(target.get("materiality_disagreement_count") or 0) + materiality_disagreements
    rows = target.setdefault("rows", [])
    rows.append(
        {
            "run_id": run_id,
            "brand_name": brand_name,
            "status": status,
            "model": model,
            "assessment_count": len(llm_rows),
            "semantic_class_disagreement_count": semantic_disagreements,
            "materiality_disagreement_count": materiality_disagreements,
            "examples": examples[:5],
            "reason": llm.get("reason") or "",
        }
    )
    target["rows"] = rows


def _increment_acquisition_row(
    *,
    rows: dict[str, dict[str, Any]],
    key: str,
    key_field: str,
    status_key: str,
    reason: str,
    peer_field: str,
    peer_value: str,
) -> None:
    row = rows.setdefault(
        key,
        {
            key_field: key,
            "accepted": 0,
            "review_required": 0,
            "rejected": 0,
            "total": 0,
            "reason_counts": {},
            peer_field: {},
        },
    )
    row[status_key] = int(row.get(status_key) or 0) + 1
    row["total"] = int(row.get("total") or 0) + 1
    _increment_count(row["reason_counts"], reason)
    _increment_count(row[peer_field], peer_value)


def _finalize_acquisition_matrix(
    *,
    provider_rows: dict[str, dict[str, Any]],
    source_class_rows: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "provider_rows": _finalize_acquisition_rows(provider_rows, key_field="provider"),
        "source_class_rows": _finalize_acquisition_rows(source_class_rows, key_field="source_class"),
    }


def _finalize_acquisition_rows(rows: dict[str, dict[str, Any]], *, key_field: str) -> list[dict[str, Any]]:
    result = []
    for row in rows.values():
        normalized = dict(row)
        normalized["reason_counts"] = _count_dict(_top_counts(normalized.get("reason_counts") or {}, limit=5))
        if key_field == "provider":
            normalized["source_classes"] = _count_dict(_top_counts(normalized.get("source_classes") or {}, limit=5))
        else:
            normalized["providers"] = _count_dict(_top_counts(normalized.get("providers") or {}, limit=5))
        result.append(normalized)
    return sorted(result, key=lambda item: (-int(item.get("total") or 0), str(item.get(key_field) or "")))


def _increment_count(counts: dict[str, int], key: str) -> None:
    counts[str(key or "unknown")] = counts.get(str(key or "unknown"), 0) + 1


def _provider_acquisition_contracts(acquisition_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = {
        str(row.get("provider") or ""): row
        for row in acquisition_matrix.get("provider_rows") or []
        if isinstance(row, dict)
    }
    contracts: list[dict[str, Any]] = []

    exa = rows.get("exa") or {}
    exa_reasons = exa.get("reason_counts") or {}
    if int(exa_reasons.get("empty_text_evidence_blocked") or 0):
        contracts.append(
            _provider_contract(
                contract="exa.non_empty_text",
                provider="exa",
                severity="high",
                recommended_action="reject_empty_text_results_before_feature_evidence",
                reason_codes=["empty_text_evidence_blocked"],
                affected_observation_count=int(exa_reasons.get("empty_text_evidence_blocked") or 0),
                current_counts=exa,
            )
        )
    exa_boundary_count = int(exa_reasons.get("same_name_external_profile_not_alias") or 0) + int(
        exa_reasons.get("same_name_different_root_domain") or 0
    )
    if exa_boundary_count:
        contracts.append(
            _provider_contract(
                contract="exa.entity_boundary_review",
                provider="exa",
                severity="high",
                recommended_action="preserve_same_name_or_different_root_results_as_review_only",
                reason_codes=["same_name_external_profile_not_alias", "same_name_different_root_domain"],
                affected_observation_count=exa_boundary_count,
                current_counts=exa,
            )
        )

    llm = rows.get("llm") or {}
    llm_reasons = llm.get("reason_counts") or {}
    if int(llm_reasons.get("missing_evidence_url") or 0):
        contracts.append(
            _provider_contract(
                contract="llm.material_quote_source_url",
                provider="llm",
                severity="high",
                recommended_action="require_source_url_for_material_quotes_or_keep_review_gated",
                reason_codes=["missing_evidence_url"],
                affected_observation_count=int(llm_reasons.get("missing_evidence_url") or 0),
                current_counts=llm,
            )
        )

    for provider, reason_code, contract_name, action in (
        (
            "content_analysis",
            "internal_analysis_not_market_evidence",
            "content_analysis.diagnostic_only",
            "keep_internal_analysis_out_of_market_narrative_evidence",
        ),
        (
            "visual_analysis",
            "visual_or_internal_analysis_not_market_evidence",
            "visual_analysis.diagnostic_only",
            "keep_visual_analysis_out_of_market_narrative_evidence",
        ),
        (
            "context",
            "technical_context_not_brand_narrative_evidence",
            "context.technical_only",
            "keep_technical_context_out_of_brand_narrative_evidence",
        ),
    ):
        row = rows.get(provider) or {}
        count = int((row.get("reason_counts") or {}).get(reason_code) or 0)
        if count:
            contracts.append(
                _provider_contract(
                    contract=contract_name,
                    provider=provider,
                    severity="medium",
                    recommended_action=action,
                    reason_codes=[reason_code],
                    affected_observation_count=count,
                    current_counts=row,
                )
            )

    social = rows.get("social_scrape") or {}
    social_reasons = social.get("reason_counts") or {}
    if int(social_reasons.get("same_name_external_profile_not_alias") or 0):
        contracts.append(
            _provider_contract(
                contract="social_scrape.alias_confirmation",
                provider="social_scrape",
                severity="high",
                recommended_action="require_alias_confirmation_before_material_or_promotion_use",
                reason_codes=["same_name_external_profile_not_alias"],
                affected_observation_count=int(social_reasons.get("same_name_external_profile_not_alias") or 0),
                current_counts=social,
            )
        )

    return contracts


def _provider_contract(
    *,
    contract: str,
    provider: str,
    severity: str,
    recommended_action: str,
    reason_codes: list[str],
    affected_observation_count: int,
    current_counts: dict[str, Any],
) -> dict[str, Any]:
    implementation = _provider_contract_implementation(contract)
    return {
        "contract": contract,
        "provider": provider,
        "severity": severity,
        "recommended_action": recommended_action,
        "reason_codes": reason_codes,
        "affected_observation_count": affected_observation_count,
        "current_counts": {
            "accepted": int(current_counts.get("accepted") or 0),
            "review_required": int(current_counts.get("review_required") or 0),
            "rejected": int(current_counts.get("rejected") or 0),
            "total": int(current_counts.get("total") or 0),
        },
        "runtime_effect": False,
        "prompt_effect": False,
        "enforcement_point": implementation["enforcement_point"],
        "implementation_status": implementation["implementation_status"],
        "implementation_lane": implementation["implementation_lane"],
        "next_step": implementation["next_step"],
        "acceptance_criteria": implementation["acceptance_criteria"],
        "proposed_tests": implementation["proposed_tests"],
    }


def _provider_contract_implementation(contract: str) -> dict[str, Any]:
    specs = {
        "exa.non_empty_text": {
            "enforcement_point": "exa_raw_result_normalization",
            "implementation_status": "upstream_needed",
            "implementation_lane": "collector_normalization",
            "next_step": "Add Exa raw-result text completeness filtering before feature evidence construction.",
            "acceptance_criteria": [
                "Exa results with URL but empty title, summary, text, and markdown are excluded before feature evidence construction.",
                "Excluded empty Exa results remain visible as diagnostic rejects, not material claims.",
            ],
            "proposed_tests": [
                "test_exa_empty_text_result_is_rejected_before_material_evidence",
                "test_exa_non_empty_result_can_still_be_accepted",
            ],
        },
        "exa.entity_boundary_review": {
            "enforcement_point": "exa_entity_classification",
            "implementation_status": "vnext_gate_enforced",
            "implementation_lane": "evidence_gate",
            "next_step": "Keep the vNext entity-boundary gate and later decide whether to move it upstream.",
            "acceptance_criteria": [
                "Same-name or different-root Exa records are preserved as review_required with entity-boundary reason codes.",
                "Entity-boundary Exa records cannot enter material fields before alias confirmation.",
            ],
            "proposed_tests": [
                "test_exa_same_name_different_root_is_review_required",
                "test_exa_entity_boundary_record_is_excluded_from_material_fields",
            ],
        },
        "llm.material_quote_source_url": {
            "enforcement_point": "llm_material_quote_contract",
            "implementation_status": "prompt_contract_needed",
            "implementation_lane": "llm_output_contract",
            "next_step": "Require source_url for material quote/tone outputs or keep them review-gated.",
            "acceptance_criteria": [
                "LLM tone or quote outputs need source_url before entering proof/context fields.",
                "Unsourced LLM material quotes remain review-gated or are excluded from material evidence.",
            ],
            "proposed_tests": [
                "test_llm_material_quote_requires_source_url",
                "test_unsourced_llm_quote_stays_out_of_material_fields",
            ],
        },
        "content_analysis.diagnostic_only": {
            "enforcement_point": "internal_analysis_evidence_gate",
            "implementation_status": "vnext_gate_enforced",
            "implementation_lane": "evidence_gate",
            "next_step": "Keep content-analysis outputs diagnostic-only in vNext and avoid promotion into material evidence.",
            "acceptance_criteria": [
                "Content-analysis observations remain available for diagnostics.",
                "Content-analysis observations cannot become market narrative evidence.",
            ],
            "proposed_tests": [
                "test_content_analysis_is_diagnostic_only",
                "test_content_analysis_does_not_populate_material_fields",
            ],
        },
        "visual_analysis.diagnostic_only": {
            "enforcement_point": "visual_analysis_evidence_gate",
            "implementation_status": "vnext_gate_enforced",
            "implementation_lane": "evidence_gate",
            "next_step": "Keep visual-analysis outputs diagnostic-only in vNext and avoid promotion into narrative proof.",
            "acceptance_criteria": [
                "Visual-analysis observations remain diagnostic.",
                "Visual-analysis observations cannot become narrative proof points.",
            ],
            "proposed_tests": [
                "test_visual_analysis_is_diagnostic_only",
                "test_visual_analysis_does_not_populate_material_fields",
            ],
        },
        "context.technical_only": {
            "enforcement_point": "technical_context_evidence_gate",
            "implementation_status": "vnext_gate_enforced",
            "implementation_lane": "evidence_gate",
            "next_step": "Keep technical context diagnostic-only and outside Brand3 narrative evidence.",
            "acceptance_criteria": [
                "Technical context remains available for debugging and methodology.",
                "Technical context does not become brand narrative evidence.",
            ],
            "proposed_tests": [
                "test_context_technical_signal_is_rejected_as_narrative_evidence",
                "test_context_technical_signal_remains_diagnostic",
            ],
        },
        "social_scrape.alias_confirmation": {
            "enforcement_point": "social_profile_entity_gate",
            "implementation_status": "policy_confirmation_needed",
            "implementation_lane": "entity_adjudication_policy",
            "next_step": "Define alias-confirmation policy before social profiles can affect material fields or promotion.",
            "acceptance_criteria": [
                "Same-name social profiles require alias confirmation before material or promotion use.",
                "Unconfirmed social profiles remain review-gated with entity-boundary reason codes.",
            ],
            "proposed_tests": [
                "test_social_profile_requires_alias_confirmation",
                "test_unconfirmed_social_profile_does_not_enter_material_fields",
            ],
        },
    }
    return specs.get(
        contract,
        {
            "enforcement_point": "unknown",
            "implementation_status": "unknown",
            "implementation_lane": "unknown",
            "next_step": "",
            "acceptance_criteria": [],
            "proposed_tests": [],
        },
    )


def _provider_contract_backlog(provider_contracts: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    counts: dict[str, int] = {}
    observation_counts: dict[str, int] = {}
    for item in provider_contracts:
        status = str(item.get("implementation_status") or "unknown")
        affected = int(item.get("affected_observation_count") or 0)
        counts[status] = counts.get(status, 0) + 1
        observation_counts[status] = observation_counts.get(status, 0) + affected
        rows.append(
            {
                "contract": item.get("contract") or "",
                "provider": item.get("provider") or "",
                "implementation_status": status,
                "implementation_lane": item.get("implementation_lane") or "",
                "affected_observation_count": affected,
                "next_step": item.get("next_step") or "",
                "proposed_tests": list(item.get("proposed_tests") or []),
            }
        )
    return {
        "counts": dict(sorted(counts.items())),
        "observation_counts": dict(sorted(observation_counts.items())),
        "rows": sorted(
            rows,
            key=lambda item: (
                str(item.get("implementation_status") or ""),
                -int(item.get("affected_observation_count") or 0),
                str(item.get("contract") or ""),
            ),
        ),
    }


def _collect_examples(
    target: dict[str, list[dict[str, Any]]],
    observations: list[dict[str, Any]],
    *,
    run_id: Any,
    brand_name: str,
    limit_per_reason: int = 3,
) -> None:
    for item in observations:
        if not isinstance(item, dict):
            continue
        reason = _observation_reason(item)
        examples = target.setdefault(reason, [])
        if len(examples) >= limit_per_reason:
            continue
        examples.append(
            {
                "run_id": run_id,
                "brand_name": brand_name,
                "feature_name": str(item.get("feature_name") or ""),
                "provider": str(item.get("provider") or ""),
                "source_class": str(item.get("source_class") or ""),
                "eligibility": str(item.get("eligibility") or ""),
                "url": str(item.get("url") or ""),
                "text_preview": _preview_text(item.get("text"), limit=160),
            }
        )


def _review_material_overlaps(*, gate_payload: dict[str, Any], vnext_pack: dict[str, Any]) -> list[dict[str, str]]:
    material_text_by_field = {
        field: _pack_field_text(vnext_pack.get(field))
        for field in MANUAL_AUDIT_MATERIAL_FIELDS
        if _pack_field_text(vnext_pack.get(field))
    }
    overlaps: list[dict[str, str]] = []
    for item in gate_payload.get("review_required") or []:
        if not isinstance(item, dict):
            continue
        observation_text = _normalized_overlap_text(item.get("text"))
        if len(observation_text) < 24:
            continue
        for field, field_text in material_text_by_field.items():
            if _text_overlaps_field(observation_text, field_text):
                overlaps.append(
                    {
                        "field": field,
                        "feature_name": str(item.get("feature_name") or ""),
                        "classification_reason": _observation_reason(item),
                        "url": str(item.get("url") or ""),
                        "text_preview": _preview_text(item.get("text"), limit=160),
                    }
                )
    overlaps.extend(_material_profile_source_overlaps(gate_payload=gate_payload, vnext_pack=vnext_pack))
    return _dedupe_overlap_items(overlaps)


def _material_profile_source_overlaps(*, gate_payload: dict[str, Any], vnext_pack: dict[str, Any]) -> list[dict[str, str]]:
    unresolved_profile_urls = {
        _url_identity(item.get("url"))
        for item in gate_payload.get("review_required") or []
        if isinstance(item, dict)
        and _observation_reason(item) == "same_name_external_profile_not_alias"
        and _url_identity(item.get("url"))
    }
    if not unresolved_profile_urls:
        return []
    overlaps: list[dict[str, str]] = []
    for field in MANUAL_AUDIT_MATERIAL_FIELDS:
        value = vnext_pack.get(field)
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict):
                continue
            source_url = str(item.get("source_url") or "").strip()
            if _url_identity(source_url) not in unresolved_profile_urls:
                continue
            overlaps.append(
                {
                    "field": field,
                    "feature_name": "material_source_url",
                    "classification_reason": "same_name_external_profile_material_source",
                    "url": source_url,
                    "text_preview": _preview_text(item.get("text"), limit=160),
                }
            )
    return overlaps


def _dedupe_overlap_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for item in items:
        key = (
            str(item.get("field") or ""),
            str(item.get("feature_name") or ""),
            str(item.get("classification_reason") or ""),
            str(item.get("url") or ""),
            str(item.get("text_preview") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _pack_field_text(value: Any) -> str:
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
            else:
                parts.append(str(item or ""))
        return _normalized_overlap_text(" ".join(parts))
    return _normalized_overlap_text(value)


def _text_overlaps_field(observation_text: str, field_text: str) -> bool:
    if observation_text in field_text:
        return True
    words = observation_text.split()
    if len(words) < 5:
        return False
    head = " ".join(words[:8])
    tail = " ".join(words[-8:])
    return (len(head) >= 24 and head in field_text) or (len(tail) >= 24 and tail in field_text)


def _normalized_overlap_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _observation_reason(item: dict[str, Any]) -> str:
    return (
        str(item.get("classification_reason") or "").strip()
        or str(item.get("eligibility") or "").strip()
        or str(item.get("source_class") or "").strip()
        or "unknown"
    )


def _preview_text(value: Any, *, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit] if text else "-"


def _host(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    return (parsed.netloc or parsed.path).strip("/").removeprefix("www.")


def _url_identity(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.netloc or parsed.path).strip("/").removeprefix("www.")
    path = parsed.path.strip("/")
    if not parsed.netloc and "/" in parsed.path:
        host, _, path = parsed.path.partition("/")
        host = host.strip("/").removeprefix("www.")
        path = path.strip("/")
    return f"{host}/{path}".rstrip("/")


def _root_domain(host: str) -> str:
    parts = [part for part in str(host or "").split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return str(host or "")


def _count_dict(pairs: list[tuple[str, int]]) -> dict[str, int]:
    return {key: value for key, value in pairs}


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _batch_recommendation(
    totals: dict[str, int],
    status_counts: dict[str, int],
    review_reasons: dict[str, int],
) -> dict[str, Any]:
    reason_codes: list[str] = []
    if totals.get("material_lost_fields", 0) > 0:
        reason_codes.append("material_regressions_present")
    if status_counts.get("blocked", 0) > 0:
        reason_codes.append("blocked_runs_present")
    if totals.get("review_required", 0) > 0:
        reason_codes.append("review_required_evidence_present")
    if review_reasons.get("missing_evidence_url", 0) > 0:
        reason_codes.append("missing_evidence_url_needs_source_propagation")
    if totals.get("reclassified_to_noise", 0) > 0:
        reason_codes.append("reclassified_noise_should_be_reviewed")

    if totals.get("material_lost_fields", 0) > 0 or status_counts.get("blocked", 0) > 0:
        status = "blocked"
    elif totals.get("review_required", 0) > 0:
        status = "review_required"
    else:
        status = "promising"

    return {
        "status": status,
        "reason_codes": reason_codes or ["no_batch_blockers_detected"],
    }
