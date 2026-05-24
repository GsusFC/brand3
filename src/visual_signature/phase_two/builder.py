"""Build reviewed Phase Zero eligibility records from Phase One plus review."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from src.visual_signature.phase_one.types import PhaseOneCaptureBundle
from src.visual_signature.phase_two.types import PhaseTwoCaptureBundle
from src.visual_signature.phase_zero.eligibility import evaluate_dataset_eligibility
from src.visual_signature.phase_zero.models import ReviewRecord
from src.visual_signature.phase_zero.validation import validate_record_schema


def build_phase_two_bundle(
    phase_one_eligibility_record: dict[str, Any],
    review_record: ReviewRecord | None,
) -> PhaseTwoCaptureBundle:
    reviewed_eligibility_record = build_reviewed_dataset_eligibility_record(phase_one_eligibility_record, review_record)
    validation_errors = []
    validation_errors.extend(validate_record_schema(phase_one_eligibility_record))
    if review_record is not None:
        validation_errors.extend(validate_record_schema(review_record.model_dump(mode="json")))
    validation_errors.extend(validate_record_schema(reviewed_eligibility_record))
    return PhaseTwoCaptureBundle(
        capture_id=str(phase_one_eligibility_record.get("capture_id") or ""),
        brand_name=str(phase_one_eligibility_record.get("brand_name") or ""),
        phase_one_eligibility_record=phase_one_eligibility_record,
        review_record=review_record.model_dump(mode="json") if review_record else None,
        reviewed_eligibility_record=reviewed_eligibility_record,
        validation_errors=validation_errors,
    )


def join_phase_one_and_reviews(
    phase_one_eligibility_records: list[dict[str, Any]],
    review_records: list[ReviewRecord],
) -> list[PhaseTwoCaptureBundle]:
    review_by_capture = {record.capture_id: record for record in review_records}
    return [build_phase_two_bundle(record, review_by_capture.get(str(record.get("capture_id") or ""))) for record in phase_one_eligibility_records]


def build_reviewed_dataset_eligibility_record(
    phase_one_eligibility_record: dict[str, Any],
    review_record: ReviewRecord | None,
) -> dict[str, Any]:
    candidate = deepcopy(phase_one_eligibility_record)
    candidate["record_id"] = f"{candidate.get('record_id')}_reviewed"
    candidate["created_at"] = _created_at()
    candidate["review_required"] = bool(candidate.get("review_required", False) or review_record is not None)
    candidate["review_completed"] = False
    candidate["eligible"] = False
    candidate["unsupported_inference_found"] = bool(candidate.get("unsupported_inference_found", False))
    uncertainty_below_threshold = bool(candidate.get("uncertainty_below_threshold", True))
    phase_one_review_required = bool(candidate.get("review_required", False))

    lineage_refs = [str(item) for item in candidate.get("lineage_refs", []) if item]
    lineage_refs.append(f"phase_one_eligibility:{phase_one_eligibility_record.get('record_id')}")

    blocked_reasons: list[str] = []
    if review_record is None:
        if phase_one_review_required:
            blocked_reasons.append("missing_review_record")
    else:
        lineage_refs.append(f"review:{review_record.review_id}")
        candidate["review_required"] = True
        review_completed = (
            review_record.review_status == "approved"
            and review_record.visually_supported in {"yes", "partial"}
            and not review_record.unsupported_inference_present
            and (review_record.uncertainty_accepted if not uncertainty_below_threshold else True)
        )
        candidate["review_completed"] = review_completed
        candidate["unsupported_inference_found"] = bool(candidate["unsupported_inference_found"] or review_record.unsupported_inference_present)
        if review_record.review_status == "rejected":
            blocked_reasons.append("review_rejected")
        elif review_record.review_status == "needs_more_evidence":
            blocked_reasons.append("needs_more_evidence")
        if review_record.visually_supported == "no":
            blocked_reasons.append("visually_not_supported")
        if review_record.unsupported_inference_present:
            blocked_reasons.append("unsupported_inference_present")
        if not uncertainty_below_threshold and review_record.review_status == "approved" and not review_record.uncertainty_accepted:
            blocked_reasons.append("uncertainty_not_accepted")

    candidate["lineage_refs"] = lineage_refs
    result = evaluate_dataset_eligibility(candidate).model_dump(mode="json")
    if blocked_reasons:
        result["blocked_reasons"] = _dedupe([*result.get("blocked_reasons", []), *blocked_reasons])
        result["eligible"] = False
    return result


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _created_at() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
