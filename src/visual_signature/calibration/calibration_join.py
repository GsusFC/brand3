"""Join machine perception claims with human reviewed outcomes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.visual_signature.calibration.calibration_models import (
    AgreementState,
    CalibrationRecord,
    ConfidenceBucket,
    PerceptionClaim,
    ReviewOutcome,
    UncertaintyAlignment,
    confidence_bucket_for_score,
    is_positive_claim_value,
)
from src.visual_signature.phase_zero.models import ReviewRecord


@dataclass(slots=True)
class PhaseOneCaptureSource:
    capture_id: str
    brand_name: str
    website_url: str
    state_record: dict[str, Any] | None
    eligibility_record: dict[str, Any] | None
    transition_records: list[dict[str, Any]]
    mutation_audit_record: dict[str, Any] | None
    record_paths: list[str]


def load_phase_one_capture_sources(phase_one_root: str | Path) -> list[PhaseOneCaptureSource]:
    root = Path(phase_one_root) / "records"
    if not root.exists():
        return []
    sources: list[PhaseOneCaptureSource] = []
    for brand_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        state_record = _load_json(brand_dir / "state.json")
        eligibility_record = _load_json(brand_dir / "dataset_eligibility.json")
        mutation_audit_record = _load_json(brand_dir / "mutation_audit.json")
        transition_records = []
        for transition_path in sorted(brand_dir.glob("transition_*.json")):
            transition_record = _load_json(transition_path)
            if isinstance(transition_record, dict):
                transition_records.append(transition_record)
        brand_name = str(
            (state_record or eligibility_record or {}).get("brand_name")
            or brand_dir.name.replace("-", " ").title()
        )
        website_url = str(
            (state_record or eligibility_record or {}).get("website_url")
            or ""
        )
        record_paths = [str(path) for path in sorted(brand_dir.glob("*.json"))]
        sources.append(
            PhaseOneCaptureSource(
                capture_id=brand_dir.name,
                brand_name=brand_name,
                website_url=website_url,
                state_record=state_record if isinstance(state_record, dict) else None,
                eligibility_record=eligibility_record if isinstance(eligibility_record, dict) else None,
                transition_records=transition_records,
                mutation_audit_record=mutation_audit_record if isinstance(mutation_audit_record, dict) else None,
                record_paths=record_paths,
            )
        )
    return sources


def load_phase_two_review_index(phase_two_root: str | Path) -> dict[str, ReviewRecord]:
    path = Path(phase_two_root) / "reviews" / "review_records.json"
    payload = _load_json(path)
    rows = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    reviews: dict[str, ReviewRecord] = {}
    for row in rows:
        if isinstance(row, dict):
            review = ReviewRecord.model_validate(row)
            reviews[review.capture_id] = review
    return reviews


def load_brand_category_map(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    payload = _load_json(Path(path))
    rows = payload.get("brands") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    mapping: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        category = str(row.get("expected_category") or "uncategorized")
        brand_name = str(row.get("brand_name") or "").strip()
        website_url = str(row.get("website_url") or "").strip()
        if brand_name:
            mapping[brand_name.lower()] = category
        if website_url:
            mapping[website_url.lower()] = category
    return mapping


def load_capture_manifest_index(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    payload = _load_json(Path(path))
    rows = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict):
            key = str(row.get("capture_id") or row.get("brand_name") or "").lower()
            if key:
                index[key] = row
                brand_key = str(row.get("brand_name") or "").lower()
                if brand_key:
                    index[brand_key] = row
    return index


def load_dismissal_audit_index(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    payload = _load_json(Path(path))
    rows = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict):
            key = str(row.get("capture_id") or row.get("brand_name") or "").lower()
            if key:
                index[key] = row
                brand_key = str(row.get("brand_name") or "").lower()
                if brand_key:
                    index[brand_key] = row
    return index


def build_calibration_records(
    *,
    phase_one_root: str | Path,
    phase_two_root: str | Path,
    brand_catalog_path: str | Path | None = None,
    capture_manifest_path: str | Path | None = None,
    dismissal_audit_path: str | Path | None = None,
) -> list[CalibrationRecord]:
    phase_one_sources = load_phase_one_capture_sources(phase_one_root)
    review_index = load_phase_two_review_index(phase_two_root)
    brand_categories = load_brand_category_map(brand_catalog_path)
    capture_manifest_index = load_capture_manifest_index(capture_manifest_path)
    dismissal_audit_index = load_dismissal_audit_index(dismissal_audit_path)

    records: list[CalibrationRecord] = []
    for source in phase_one_sources:
        state_record = source.state_record or {}
        review_record = review_index.get(source.capture_id)
        capture_manifest_row = capture_manifest_index.get(source.capture_id.lower()) or capture_manifest_index.get(source.brand_name.lower())
        dismissal_audit_row = dismissal_audit_index.get(source.capture_id.lower()) or dismissal_audit_index.get(source.brand_name.lower())
        category = _category_for(source.brand_name, source.website_url, brand_categories)
        claim = _build_claim(source, capture_manifest_row=capture_manifest_row, dismissal_audit_row=dismissal_audit_row)
        review_outcome = _build_review_outcome(review_record)
        agreement_state = _agreement_state(claim.claim_value, review_outcome)
        uncertainty_alignment = _uncertainty_alignment(claim.confidence_bucket, agreement_state, review_outcome)
        source_breakdown = _source_breakdown(source, review_record, capture_manifest_row, dismissal_audit_row)
        evidence_refs = _evidence_refs(source, capture_manifest_row, dismissal_audit_row)
        lineage_refs = _lineage_refs(source, review_record, capture_manifest_row, dismissal_audit_row)
        notes = _notes(source, review_outcome, capture_manifest_row, dismissal_audit_row)
        diagnostics = _diagnostics(source, capture_manifest_row, dismissal_audit_row)

        records.append(
            CalibrationRecord(
                schema_version="visual-signature-calibration-record-1",
                taxonomy_version="phase-zero-taxonomy-1",
                record_type="calibration_record",
                calibration_id=f"calibration_{source.capture_id}",
                capture_id=source.capture_id,
                brand_name=source.brand_name,
                website_url=source.website_url,
                category=category,
                claim=claim,
                review_outcome=review_outcome,
                agreement_state=agreement_state,
                confidence_bucket=claim.confidence_bucket,
                uncertainty_alignment=uncertainty_alignment,
                evidence_refs=evidence_refs,
                lineage_refs=lineage_refs,
                source_breakdown=source_breakdown,
                diagnostics=diagnostics,
                notes=notes,
            )
        )
    return records


def _build_claim(
    source: PhaseOneCaptureSource,
    *,
    capture_manifest_row: dict[str, Any] | None,
    dismissal_audit_row: dict[str, Any] | None,
) -> PerceptionClaim:
    state_record = source.state_record or {}
    claim_value = str(state_record.get("perceptual_state") or "UNKNOWN_STATE")
    confidence = _float(state_record.get("confidence"))
    confidence_bucket = confidence_bucket_for_score(confidence)
    evidence_refs = _unique_strings(_evidence_refs(source, capture_manifest_row, dismissal_audit_row))
    lineage_refs = _unique_strings(_lineage_refs(source, None, capture_manifest_row, dismissal_audit_row))
    notes = [f"source_state:{claim_value}"]
    if source.eligibility_record:
        notes.append(f"phase_one_eligible:{bool(source.eligibility_record.get('eligible'))}")
    if source.mutation_audit_record:
        notes.append(f"mutation_attempted:{bool(source.mutation_audit_record.get('attempted'))}")
    return PerceptionClaim(
        schema_version="visual-signature-calibration-claim-1",
        taxonomy_version="phase-zero-taxonomy-1",
        record_type="perception_claim",
        claim_id=f"claim_{source.capture_id}_state",
        claim_kind="capture_state",
        claim_value=claim_value,
        confidence=confidence,
        confidence_bucket=confidence_bucket,
        evidence_refs=evidence_refs,
        lineage_refs=lineage_refs,
        notes=notes,
    )


def _build_review_outcome(review_record: ReviewRecord | None) -> ReviewOutcome | None:
    if review_record is None:
        return None
    return ReviewOutcome(
        schema_version="visual-signature-calibration-review-outcome-1",
        taxonomy_version="phase-zero-taxonomy-1",
        record_type="review_outcome",
        review_id=review_record.review_id,
        capture_id=review_record.capture_id,
        reviewer_id=review_record.reviewer_id,
        reviewed_at=review_record.reviewed_at,
        review_status=review_record.review_status,
        visually_supported=review_record.visually_supported,
        unsupported_inference_present=review_record.unsupported_inference_present,
        uncertainty_accepted=review_record.uncertainty_accepted,
        notes=review_record.notes,
    )


def _agreement_state(claim_value: str, review_outcome: ReviewOutcome | None) -> AgreementState:
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


def _uncertainty_alignment(
    confidence_bucket: ConfidenceBucket,
    agreement_state: AgreementState,
    review_outcome: ReviewOutcome | None,
) -> UncertaintyAlignment:
    if review_outcome is None:
        return "insufficient_data"
    if review_outcome.review_status == "needs_more_evidence":
        return "uncertainty_accepted"
    if agreement_state == "confirmed":
        return "underconfident" if confidence_bucket == "low" else "calibrated"
    if agreement_state == "contradicted":
        return "overconfident" if confidence_bucket == "high" else "underconfident"
    return "insufficient_data"


def _source_breakdown(
    source: PhaseOneCaptureSource,
    review_record: ReviewRecord | None,
    capture_manifest_row: dict[str, Any] | None,
    dismissal_audit_row: dict[str, Any] | None,
) -> dict[str, int]:
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


def _evidence_refs(
    source: PhaseOneCaptureSource,
    capture_manifest_row: dict[str, Any] | None,
    dismissal_audit_row: dict[str, Any] | None,
) -> list[str]:
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
    if capture_manifest_row:
        raw_path = capture_manifest_row.get("raw_screenshot_path")
        if raw_path:
            refs.append(str(raw_path))
    if dismissal_audit_row:
        raw_path = dismissal_audit_row.get("raw_screenshot_path")
        if raw_path:
            refs.append(str(raw_path))
    return _unique_strings([ref for ref in refs if ref])


def _lineage_refs(
    source: PhaseOneCaptureSource,
    review_record: ReviewRecord | None,
    capture_manifest_row: dict[str, Any] | None,
    dismissal_audit_row: dict[str, Any] | None,
) -> list[str]:
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
    return _unique_strings([ref for ref in refs if ref])


def _diagnostics(
    source: PhaseOneCaptureSource,
    capture_manifest_row: dict[str, Any] | None,
    dismissal_audit_row: dict[str, Any] | None,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "state": (source.state_record or {}).get("perceptual_state"),
        "state_confidence": _float((source.state_record or {}).get("confidence")),
        "review_required": bool((source.state_record or {}).get("uncertainty", {}).get("reviewer_required"))
        if isinstance((source.state_record or {}).get("uncertainty"), dict)
        else False,
    }
    if source.mutation_audit_record:
        diagnostics["mutation_audit"] = {
            "attempted": bool(source.mutation_audit_record.get("attempted")),
            "successful": bool(source.mutation_audit_record.get("successful")),
            "risk_level": str(source.mutation_audit_record.get("risk_level") or "unknown"),
        }
    if capture_manifest_row:
        candidate_targets = capture_manifest_row.get("candidate_click_targets") or []
        rejected_targets = capture_manifest_row.get("rejected_click_targets") or []
        safe_clicked = sum(
            1
            for target in candidate_targets
            if isinstance(target, dict) and str(target.get("interaction_policy") or "") == "safe_to_dismiss"
        )
        safe_not_clicked = sum(
            1
            for target in rejected_targets
            if isinstance(target, dict) and str(target.get("interaction_policy") or "") == "safe_to_dismiss"
        )
        unsafe_rejected = sum(
            1
            for target in rejected_targets
            if isinstance(target, dict) and str(target.get("interaction_policy") or "") == "unsafe_to_mutate"
        )
        review_rejected = sum(
            1
            for target in rejected_targets
            if isinstance(target, dict) and str(target.get("interaction_policy") or "") == "requires_human_review"
        )
        diagnostics["capture_manifest"] = {
            "candidate_click_targets": len(candidate_targets),
            "rejected_click_targets": len(rejected_targets),
            "safe_to_dismiss_candidates_clicked": safe_clicked,
            "safe_to_dismiss_candidates_not_clicked": safe_not_clicked,
            "unsafe_to_mutate_candidates_rejected": unsafe_rejected,
            "requires_human_review_candidates_rejected": review_rejected,
            "perceptual_state": capture_manifest_row.get("perceptual_state"),
        }
    if dismissal_audit_row:
        diagnostics["affordance_diagnostics"] = {
            "affordance_category_distribution": dismissal_audit_row.get("affordance_category_distribution") or {},
            "affordance_owner_distribution": dismissal_audit_row.get("affordance_owner_distribution") or {},
            "interaction_policy_distribution": dismissal_audit_row.get("interaction_policy_distribution") or {},
            "safe_to_dismiss_candidates_not_clicked": int(dismissal_audit_row.get("safe_to_dismiss_candidates_not_clicked") or 0),
            "unsafe_to_mutate_candidates_encountered": int(dismissal_audit_row.get("unsafe_to_mutate_candidates_encountered") or 0),
            "requires_human_review_candidates_encountered": int(dismissal_audit_row.get("requires_human_review_candidates_encountered") or 0),
        }
    return diagnostics


def _notes(
    source: PhaseOneCaptureSource,
    review_outcome: ReviewOutcome | None,
    capture_manifest_row: dict[str, Any] | None,
    dismissal_audit_row: dict[str, Any] | None,
) -> list[str]:
    notes: list[str] = []
    state_record = source.state_record or {}
    perceptual_state = state_record.get("perceptual_state")
    if perceptual_state:
        notes.append(f"phase_one_state:{perceptual_state}")
    if source.eligibility_record is not None:
        notes.append(f"phase_one_eligible:{bool(source.eligibility_record.get('eligible'))}")
        if source.eligibility_record.get("blocked_reasons"):
            notes.append(
                "phase_one_blocked_reasons:" + ",".join(str(item) for item in source.eligibility_record.get("blocked_reasons") or [] if item)
            )
    if review_outcome is not None:
        notes.append(f"review_status:{review_outcome.review_status}")
        notes.append(f"visually_supported:{review_outcome.visually_supported}")
        if review_outcome.uncertainty_accepted:
            notes.append("uncertainty_accepted:true")
    if source.mutation_audit_record:
        notes.append(f"mutation_attempted:{bool(source.mutation_audit_record.get('attempted'))}")
        notes.append(f"mutation_successful:{bool(source.mutation_audit_record.get('successful'))}")
    if capture_manifest_row:
        notes.append(f"capture_manifest_targets:{len(capture_manifest_row.get('candidate_click_targets') or []) + len(capture_manifest_row.get('rejected_click_targets') or [])}")
    if dismissal_audit_row:
        notes.append(f"dismissal_owner_types:{len(dismissal_audit_row.get('affordance_owner_distribution') or {})}")
    return _unique_strings([note for note in notes if note])


def _category_for(brand_name: str, website_url: str, brand_categories: dict[str, str]) -> str:
    return (
        brand_categories.get(brand_name.lower())
        or brand_categories.get(website_url.lower())
        or "uncategorized"
    )


def _float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
