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
from src.research.evidence_vnext_report_work_orders_support import (
    _dominant_count_key,
    _intervention_profile,
    _work_orders,
    _work_order_expected_output,
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
