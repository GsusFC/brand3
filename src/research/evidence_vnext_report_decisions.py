"""Decision helpers for vNext batch reports."""

from __future__ import annotations

from importlib import import_module
from typing import Any


def _report():
    return import_module("src.research.evidence_vnext_report")


def _run_promotion_decision(
    *,
    summary: dict[str, Any],
    gate: dict[str, Any],
    comparison: dict[str, Any],
    gate_payload: dict[str, Any] | None = None,
    vnext_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = _report()
    review_reasons = {str(key): int(value or 0) for key, value in (gate.get("review_reason_counts") or {}).items()}
    review_count = int(gate.get("review_required_count") or 0)
    material_lost_count = int(summary.get("material_lost_count") or 0)
    missing_url_count = int(review_reasons.get("missing_evidence_url") or 0)
    placeholder_entity = report._is_reserved_or_placeholder_entity(comparison)
    material_overlaps = report._review_material_overlaps(
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
        reason for reason in report.PROMOTION_BLOCKING_REVIEW_REASONS if review_reasons.get(reason, 0) > 0
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
    if missing_url_count > report.PROMOTION_MAX_LIMITED_MISSING_URL_COUNT:
        reason_codes.append("missing_evidence_url_above_threshold")
    if review_count > report.PROMOTION_MAX_LIMITED_REVIEW_COUNT:
        reason_codes.append("review_count_above_threshold")

    if (
        material_lost_count
        or placeholder_entity
        or blocking_review_reasons
        or entity_profile_material_overlaps
        or missing_url_material_overlaps
    ):
        status = "blocked"
    elif missing_url_count > report.PROMOTION_MAX_LIMITED_MISSING_URL_COUNT or review_count > report.PROMOTION_MAX_LIMITED_REVIEW_COUNT:
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
    report = _report()
    host = report._host(comparison.get("url") or "")
    brand = str(comparison.get("brand_name") or "").strip().lower().removeprefix("www.")
    root = report._root_domain(host or brand)
    tld = root.rsplit(".", 1)[-1] if "." in root else root
    return root in report.RESERVED_OR_PLACEHOLDER_ROOTS or tld in report.RESERVED_OR_PLACEHOLDER_TLDS


from src.research.evidence_vnext_report_projection import (
    _append_projected_reason_decision,
    _blocked_evidence_queue_item,
    _contract_projection_row,
    _contract_projection_summary,
    _contract_recommendations,
    _decision_action_counts,
    _decision_queue,
    _is_projected_contract_filtered_observation,
    _is_projected_missing_url_contract_observation,
    _is_projected_social_placeholder_contract_observation,
    _manual_audit_profile,
    _manual_audit_queue_item,
    _material_quote_contract_queue_item,
    _promotion_after_manual_audit,
    _provider_contract_is_implemented,
    _quote_material_impact,
    _quote_source_review_queue_item,
    _projected_applied_contracts,
    _projected_gate_summary,
    _removed_review_reason_counts,
    _run_manual_audit_decision,
    _social_placeholder_auto_cleared_runs,
    _triage_actions,
)
