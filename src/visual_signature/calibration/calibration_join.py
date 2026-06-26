"""Join machine perception claims with human reviewed outcomes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.visual_signature.calibration.calibration_loaders import (
    PhaseOneCaptureSource,
    load_brand_category_map,
    load_capture_manifest_index,
    load_dismissal_audit_index,
    load_json as _load_json,
    load_phase_one_capture_sources,
    load_phase_two_review_index,
)
from src.visual_signature.calibration.calibration_models import (
    CalibrationRecord,
    PerceptionClaim,
    ReviewOutcome,
    confidence_bucket_for_score,
)
from src.visual_signature.calibration.calibration_support import (
    agreement_state as _agreement_state,
    category_for as _category_for,
    clamp_float as _float,
    diagnostics as _diagnostics,
    evidence_refs as _evidence_refs,
    lineage_refs as _lineage_refs,
    notes as _notes,
    source_breakdown as _source_breakdown,
    uncertainty_alignment as _uncertainty_alignment,
    unique_strings as _unique_strings,
)
from src.visual_signature.phase_zero.models import ReviewRecord


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

