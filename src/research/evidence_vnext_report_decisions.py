"""Decision, projection, and adjudication helpers for vNext batch reports."""

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
    report = _report()
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


def _work_order_context(run: dict[str, Any]) -> dict[str, Any]:
    report = _report()
    review_examples = list(run.get("remaining_review_examples") or [])
    material_overlaps = list(run.get("projected_material_overlaps") or [])
    changed_material_fields = list(run.get("changed_material_fields") or [])
    profile_urls = [
        report._context_url_identity(item.get("url"))
        for item in (*review_examples, *material_overlaps)
        if str(item.get("classification_reason") or "")
        in {"same_name_external_profile_not_alias", "same_name_external_profile_material_source"}
    ]
    review_urls = [report._context_url_identity(item.get("url")) for item in review_examples if str(item.get("url") or "")]
    affected_material_fields = [
        str(item.get("field") or "")
        for item in material_overlaps
        if str(item.get("field") or "") in report.MANUAL_AUDIT_MATERIAL_FIELDS
    ]
    changed_material_field_names = [
        str(item.get("field") or "")
        for item in changed_material_fields
        if str(item.get("field") or "") in report.MANUAL_AUDIT_MATERIAL_FIELDS
    ]
    return {
        "remaining_review_examples": review_examples,
        "projected_material_overlaps": material_overlaps,
        "changed_material_fields": changed_material_fields,
        "profile_urls": report._unique([url for url in profile_urls if url]),
        "review_urls": report._unique([url for url in review_urls if url]),
        "affected_material_fields": report._unique(affected_material_fields or changed_material_field_names),
        "changed_material_field_names": report._unique(changed_material_field_names),
    }


def _decision_record_template(
    *,
    run_id: Any,
    work_order_id: str,
    packet: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    report = _report()
    template: dict[str, Any] = {
        "work_order_id": work_order_id,
        "run_id": run_id,
        "decision": "",
        "reviewer": "",
        "rationale": "",
    }
    for field in packet.get("decision_required_fields") or []:
        template.setdefault(str(field), "")
    if "profile_url" in template:
        template["profile_url"] = report._join_unique(context.get("profile_urls") or [])
    if "affected_material_fields" in template:
        template["affected_material_fields"] = report._join_unique(context.get("affected_material_fields") or [])
    if "approved_material_fields" in template:
        template["approved_material_fields"] = report._join_unique(context.get("changed_material_field_names") or [])
    if "quarantined_source_urls" in template:
        template["quarantined_source_urls"] = report._join_unique(context.get("review_urls") or [])
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

