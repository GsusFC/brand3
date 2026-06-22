"""Presentation helpers for Evidence vNext batch reports."""

from __future__ import annotations

from typing import Any

from src.research.evidence_vnext_report_debug import print_changed_fields, print_gate_reasons


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
