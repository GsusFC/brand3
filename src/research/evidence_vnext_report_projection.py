"""Projection, triage, and adjudication helpers for evidence vNext reports."""

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


def _manual_audit_queue_item(
    *,
    comparison: dict[str, Any],
    gate_payload: dict[str, Any],
    promotion: dict[str, Any],
    manual_audit: dict[str, Any],
) -> dict[str, Any]:
    report = _report()
    audit_fields = set(str(field) for field in manual_audit.get("fields") or [])
    changed_material_fields = [
        {
            "field": str(field.get("field") or ""),
            "current_preview": report._preview_text(field.get("legacy_preview"), limit=220),
            "vnext_preview": report._preview_text(field.get("graph_preview"), limit=220),
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
            "classification_reason": report._observation_reason(item),
            "url": str(item.get("url") or ""),
            "text_preview": report._preview_text(item.get("text"), limit=220),
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


def _run_manual_audit_decision(*, comparison: dict[str, Any], promotion: dict[str, Any]) -> dict[str, Any]:
    report = _report()
    changed_material_fields = sorted(
        str(field.get("field") or "")
        for field in comparison.get("fields") or []
        if isinstance(field, dict)
        and field.get("changed")
        and str(field.get("field") or "") in report.MANUAL_AUDIT_MATERIAL_FIELDS
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
from src.research.evidence_vnext_report_projection_queue import (
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
    _material_fields_containing_quote,
    _material_quote_contract_queue_item,
    _promotion_after_manual_audit,
    _provider_contract_is_implemented,
    _quote_material_impact,
    _quote_source_review_queue_item,
    _projected_applied_contracts,
    _projected_gate_summary,
    _removed_review_reason_counts,
    _social_placeholder_auto_cleared_runs,
    _triage_actions,
)
