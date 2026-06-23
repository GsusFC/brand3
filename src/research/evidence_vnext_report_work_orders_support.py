"""Support helpers for vNext shadow-policy work orders."""

from __future__ import annotations

from typing import Any

from src.research.evidence_vnext_report_work_orders_adjudication import (
    _decision_record_template,
    _work_order_context,
)


def _dominant_count_key(counts: dict[str, int]) -> str:
    if not counts:
        return "unknown"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


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


def _work_orders(intervention_packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    for packet in intervention_packets:
        if not packet.get("human_required"):
            continue
        for run in packet.get("runs") or []:
            run_id = run.get("run_id")
            if run_id is None:
                continue
            context = _work_order_context(run)
            work_order_id = f"workorder:{packet.get('intervention_type') or 'unknown'}:{run_id}"
            orders.append(
                {
                    "work_order_id": work_order_id,
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
                        work_order_id=work_order_id,
                        packet=packet,
                        context=context,
                    ),
                    "context": context,
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
