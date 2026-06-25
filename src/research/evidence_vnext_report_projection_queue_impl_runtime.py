"""Projection queue, contract, and triage helpers for evidence vNext reports."""

from __future__ import annotations

from importlib import import_module
from typing import Any


def _report():
    return import_module("src.research.evidence_vnext_report")


def _decisions():
    return import_module("src.research.evidence_vnext_report_decisions")


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
    report = _report()
    observations = [
        {
            "feature_name": str(item.get("feature_name") or ""),
            "provider": str(item.get("provider") or ""),
            "source_class": str(item.get("source_class") or ""),
            "eligibility": str(item.get("eligibility") or ""),
            "text_preview": report._preview_text(item.get("text"), limit=220),
            **_quote_material_impact(item.get("text"), current_pack=current_pack, vnext_pack=vnext_pack),
        }
        for item in gate_payload.get("review_required") or []
        if isinstance(item, dict) and report._observation_reason(item) == "missing_evidence_url"
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
    report = _report()
    quote = report._normalized_overlap_text(text)
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
    report = _report()
    fields: list[str] = []
    for field in report.MANUAL_AUDIT_MATERIAL_FIELDS:
        field_text = report._pack_field_text(pack.get(field))
        if field_text and report._text_overlaps_field(quote, field_text):
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
    report = _report()
    material_overlaps = report._review_material_overlaps(
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
    decisions = _decisions()
    projected_promotion = decisions._run_promotion_decision(
        summary=summary,
        gate=projected_gate,
        comparison=comparison,
        gate_payload=projected_gate_payload,
        vnext_pack=vnext_pack,
    )
    projected_manual_audit = decisions._run_manual_audit_decision(comparison=comparison, promotion=projected_promotion)
    projected_promotion = _promotion_after_manual_audit(
        promotion=projected_promotion,
        manual_audit=projected_manual_audit,
    )
    projected_material_overlaps = report._review_material_overlaps(
        gate_payload=projected_gate_payload,
        vnext_pack=vnext_pack,
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
        "remaining_review_examples": report._compact_review_observations(filtered_review_required, limit=5),
        "projected_material_overlaps": projected_material_overlaps,
        "changed_material_fields": report._changed_material_field_previews(comparison),
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
    report = _report()
    return (
        report._observation_reason(item) == "missing_evidence_url"
        and str(item.get("feature_name") or "") == "tone_consistency"
        and not str(item.get("url") or "").strip()
    )


def _is_projected_social_placeholder_contract_observation(
    item: dict[str, Any],
    *,
    material_overlaps: list[dict[str, Any]],
) -> bool:
    report = _report()
    if report._observation_reason(item) != "same_name_external_profile_not_alias":
        return False
    if str(item.get("provider") or "") != "social_scrape":
        return False
    text = str(item.get("text") or item.get("text_preview") or "").strip().lower()
    if "profile candidate" not in text:
        return False
    item_url = str(item.get("url") or "").strip()
    if not item_url:
        return False
    item_url_key = report._url_identity(item_url)
    for overlap in material_overlaps:
        if report._observation_reason(overlap) not in {
            "same_name_external_profile_not_alias",
            "same_name_external_profile_material_source",
        }:
            continue
        if item_url_key and report._url_identity(str(overlap.get("url") or "")) == item_url_key:
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
    report = _report()
    counts: dict[str, int] = {}
    for item in removed_review:
        reason = report._observation_reason(item)
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
    projected_rows = list(contract_projection.get("rows") or [])
    social_placeholder_auto_cleared_runs = _social_placeholder_auto_cleared_runs(projected_rows)
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
        if _provider_contract_is_implemented(item):
            continue
        if (
            str(item.get("contract") or "") == "social_scrape.alias_confirmation"
            and social_placeholder_auto_cleared_runs
            and int(item.get("affected_observation_count") or 0) <= len(social_placeholder_auto_cleared_runs)
        ):
            continue
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
        and int(item.get("run_id")) not in social_placeholder_auto_cleared_runs
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


def _social_placeholder_auto_cleared_runs(projected_rows: list[dict[str, Any]]) -> set[int]:
    runs: set[int] = set()
    for row in projected_rows:
        if "social_scrape.placeholder_profile_non_material" not in set(row.get("applied_contracts") or []):
            continue
        if row.get("projected_manual_audit_required"):
            continue
        if row.get("remaining_review_examples"):
            continue
        if row.get("run_id") is not None:
            runs.add(int(row["run_id"]))
    return runs


def _provider_contract_is_implemented(item: dict[str, Any]) -> bool:
    return str(item.get("implementation_status") or "") in {"vnext_gate_enforced", "upstream_enforced"}


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


def _triage_actions(
    *,
    promotion_status: str,
    promotion_reason_codes: list[str],
    review_examples: list[dict[str, Any]],
    review_material_overlaps: list[dict[str, Any]],
    changed_material_fields: list[dict[str, Any]],
) -> list[str]:
    report = _report()
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
    return report._unique(actions)


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
