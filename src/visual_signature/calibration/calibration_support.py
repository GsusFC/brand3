"""Support helpers for building calibration records."""

from __future__ import annotations

from typing import Any

from src.visual_signature.calibration.calibration_models import (
    AgreementState,
    ConfidenceBucket,
    ReviewOutcome,
    UncertaintyAlignment,
    is_positive_claim_value,
)
from src.visual_signature.calibration.calibration_loaders import PhaseOneCaptureSource
from src.visual_signature.phase_zero.models import ReviewRecord


def agreement_state(claim_value: str, review_outcome: ReviewOutcome | None) -> AgreementState:
    if review_outcome is None:
        return "insufficient_review"
    if review_outcome.review_status == "needs_more_evidence":
        return "unresolved"
    if not claim_value or claim_value == "UNKNOWN_STATE":
        return "unresolved"
    claim_positive = is_positive_claim_value(claim_value)
    review_positive = review_outcome.review_status == "approved"
    if claim_positive == review_positive:
        return "confirmed"
    return "contradicted"


def uncertainty_alignment(confidence_bucket: ConfidenceBucket, agreement_state_value: AgreementState, review_outcome: ReviewOutcome | None) -> UncertaintyAlignment:
    if review_outcome is None:
        return "insufficient_data"
    if review_outcome.review_status == "needs_more_evidence":
        return "uncertainty_accepted"
    if agreement_state_value == "confirmed":
        return "underconfident" if confidence_bucket == "low" else "calibrated"
    if agreement_state_value == "contradicted":
        return "overconfident" if confidence_bucket == "high" else "underconfident"
    return "insufficient_data"


def source_breakdown(source: PhaseOneCaptureSource, review_record: ReviewRecord | None, capture_manifest_row: dict[str, Any] | None, dismissal_audit_row: dict[str, Any] | None) -> dict[str, int]:
    transition_count = len(source.transition_records)
    affordance_count = 0
    if capture_manifest_row:
        affordance_count = len(capture_manifest_row.get("candidate_click_targets") or []) + len(capture_manifest_row.get("rejected_click_targets") or [])
    return {
        "phase_one_state": 1 if source.state_record else 0,
        "phase_one_eligibility": 1 if source.eligibility_record else 0,
        "phase_one_transition_records": transition_count,
        "phase_one_mutation_audit": 1 if source.mutation_audit_record else 0,
        "phase_two_review": 1 if review_record is not None else 0,
        "capture_manifest": 1 if capture_manifest_row else 0,
        "dismissal_audit": 1 if dismissal_audit_row else 0,
        "affordance_targets": affordance_count,
    }


def evidence_refs(source: PhaseOneCaptureSource, capture_manifest_row: dict[str, Any] | None, dismissal_audit_row: dict[str, Any] | None) -> list[str]:
    refs: list[str] = []
    state_record = source.state_record or {}
    reasoning_trace = state_record.get("reasoning_trace") if isinstance(state_record.get("reasoning_trace"), dict) else {}
    statements = reasoning_trace.get("statements") if isinstance(reasoning_trace.get("statements"), list) else []
    if statements:
        first = statements[0]
        if isinstance(first, dict):
            refs.extend(str(item) for item in first.get("evidence_refs") or [] if item)
    if source.eligibility_record:
        refs.extend(str(item) for item in source.eligibility_record.get("evidence_refs") or [] if item)
    if source.mutation_audit_record:
        refs.append(str(source.mutation_audit_record.get("before_artifact_ref") or ""))
        after_ref = source.mutation_audit_record.get("after_artifact_ref")
        if after_ref:
            refs.append(str(after_ref))
    if capture_manifest_row and capture_manifest_row.get("raw_screenshot_path"):
        refs.append(str(capture_manifest_row.get("raw_screenshot_path")))
    if dismissal_audit_row and dismissal_audit_row.get("raw_screenshot_path"):
        refs.append(str(dismissal_audit_row.get("raw_screenshot_path")))
    return unique_strings([ref for ref in refs if ref])


def lineage_refs(source: PhaseOneCaptureSource, review_record: ReviewRecord | None, capture_manifest_row: dict[str, Any] | None, dismissal_audit_row: dict[str, Any] | None) -> list[str]:
    refs: list[str] = []
    state_record = source.state_record or {}
    refs.extend(str(item) for item in state_record.get("lineage_refs") or [] if item)
    if source.eligibility_record:
        refs.extend(str(item) for item in source.eligibility_record.get("lineage_refs") or [] if item)
    if source.mutation_audit_record:
        refs.extend(str(item) for item in source.mutation_audit_record.get("lineage_refs") or [] if item)
        mutation_id = source.mutation_audit_record.get("mutation_id")
        if mutation_id:
            refs.append(f"mutation:{mutation_id}")
    if review_record is not None:
        refs.append(f"review:{review_record.review_id}")
    if capture_manifest_row:
        refs.append("capture_manifest:examples/visual_signature/screenshots/capture_manifest.json")
    if dismissal_audit_row:
        refs.append("dismissal_audit:examples/visual_signature/screenshots/dismissal_audit.json")
    return unique_strings([ref for ref in refs if ref])


def diagnostics(source: PhaseOneCaptureSource, capture_manifest_row: dict[str, Any] | None, dismissal_audit_row: dict[str, Any] | None) -> dict[str, Any]:
    diagnostics_payload: dict[str, Any] = {
        "state": (source.state_record or {}).get("perceptual_state"),
        "state_confidence": clamp_float((source.state_record or {}).get("confidence")),
        "review_required": bool((source.state_record or {}).get("uncertainty", {}).get("reviewer_required")) if isinstance((source.state_record or {}).get("uncertainty"), dict) else False,
    }
    if source.mutation_audit_record:
        diagnostics_payload["mutation_audit"] = {
            "attempted": bool(source.mutation_audit_record.get("attempted")),
            "successful": bool(source.mutation_audit_record.get("successful")),
            "risk_level": str(source.mutation_audit_record.get("risk_level") or "unknown"),
        }
    if capture_manifest_row:
        candidate_targets = capture_manifest_row.get("candidate_click_targets") or []
        rejected_targets = capture_manifest_row.get("rejected_click_targets") or []
        diagnostics_payload["capture_manifest"] = {
            "candidate_click_targets": len(candidate_targets),
            "rejected_click_targets": len(rejected_targets),
            "safe_to_dismiss_candidates_clicked": count_targets(candidate_targets, "safe_to_dismiss"),
            "safe_to_dismiss_candidates_not_clicked": count_targets(rejected_targets, "safe_to_dismiss"),
            "unsafe_to_mutate_candidates_rejected": count_targets(rejected_targets, "unsafe_to_mutate"),
            "requires_human_review_candidates_rejected": count_targets(rejected_targets, "requires_human_review"),
            "perceptual_state": capture_manifest_row.get("perceptual_state"),
        }
    if dismissal_audit_row:
        diagnostics_payload["affordance_diagnostics"] = {
            "affordance_category_distribution": dismissal_audit_row.get("affordance_category_distribution") or {},
            "affordance_owner_distribution": dismissal_audit_row.get("affordance_owner_distribution") or {},
            "interaction_policy_distribution": dismissal_audit_row.get("interaction_policy_distribution") or {},
            "safe_to_dismiss_candidates_not_clicked": int(dismissal_audit_row.get("safe_to_dismiss_candidates_not_clicked") or 0),
            "unsafe_to_mutate_candidates_encountered": int(dismissal_audit_row.get("unsafe_to_mutate_candidates_encountered") or 0),
            "requires_human_review_candidates_encountered": int(dismissal_audit_row.get("requires_human_review_candidates_encountered") or 0),
        }
    return diagnostics_payload


def notes(source: PhaseOneCaptureSource, review_outcome: ReviewOutcome | None, capture_manifest_row: dict[str, Any] | None, dismissal_audit_row: dict[str, Any] | None) -> list[str]:
    notes_list: list[str] = []
    state_record = source.state_record or {}
    perceptual_state = state_record.get("perceptual_state")
    if perceptual_state:
        notes_list.append(f"phase_one_state:{perceptual_state}")
    if source.eligibility_record is not None:
        notes_list.append(f"phase_one_eligible:{bool(source.eligibility_record.get('eligible'))}")
        if source.eligibility_record.get("blocked_reasons"):
            notes_list.append("phase_one_blocked_reasons:" + ",".join(str(item) for item in source.eligibility_record.get("blocked_reasons") or [] if item))
    if review_outcome is not None:
        notes_list.append(f"review_status:{review_outcome.review_status}")
        notes_list.append(f"visually_supported:{review_outcome.visually_supported}")
        if review_outcome.uncertainty_accepted:
            notes_list.append("uncertainty_accepted:true")
    if source.mutation_audit_record:
        notes_list.append(f"mutation_attempted:{bool(source.mutation_audit_record.get('attempted'))}")
        notes_list.append(f"mutation_successful:{bool(source.mutation_audit_record.get('successful'))}")
    if capture_manifest_row:
        notes_list.append(f"capture_manifest_targets:{len(capture_manifest_row.get('candidate_click_targets') or []) + len(capture_manifest_row.get('rejected_click_targets') or [])}")
    if dismissal_audit_row:
        notes_list.append(f"dismissal_owner_types:{len(dismissal_audit_row.get('affordance_owner_distribution') or {})}")
    return unique_strings([note for note in notes_list if note])


def category_for(brand_name: str, website_url: str, brand_categories: dict[str, str]) -> str:
    return brand_categories.get(brand_name.lower()) or brand_categories.get(website_url.lower()) or "uncategorized"


def clamp_float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def count_targets(rows: list[Any], interaction_policy: str) -> int:
    return sum(1 for target in rows if isinstance(target, dict) and str(target.get("interaction_policy") or "") == interaction_policy)
