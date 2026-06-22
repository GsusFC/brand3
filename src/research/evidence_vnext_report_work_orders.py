"""Shadow-policy readiness, intervention packets, and work-order helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any


def _report():
    return import_module("src.research.evidence_vnext_report")


from src.research.evidence_vnext_report_work_orders_adjudication import (
    _adjudication_intake,
    _decision_record_template,
    _work_order_context,
)


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
                "remaining_review_examples": list(row.get("remaining_review_examples") or []),
                "projected_material_overlaps": list(row.get("projected_material_overlaps") or []),
                "changed_material_fields": list(row.get("changed_material_fields") or []),
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
        readiness_status = "ready_after_contract"
    elif projected_status == "audit_required":
        readiness_status = "needs_manual_audit"
    elif projected_status == "blocked":
        readiness_status = "blocked_after_contract"
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
        "remaining_review_examples": list(shadow_run.get("remaining_review_examples") or []),
        "projected_material_overlaps": list(shadow_run.get("projected_material_overlaps") or []),
        "changed_material_fields": list(shadow_run.get("changed_material_fields") or []),
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
                "remaining_review_examples": list(row.get("remaining_review_examples") or []),
                "projected_material_overlaps": list(row.get("projected_material_overlaps") or []),
                "changed_material_fields": list(row.get("changed_material_fields") or []),
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
