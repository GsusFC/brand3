"""Pydantic models for Visual Signature calibration evidence."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.visual_signature.phase_zero.models import PHASE_ZERO_TAXONOMY_VERSION


CALIBRATION_CLAIM_SCHEMA_VERSION = "visual-signature-calibration-claim-1"
CALIBRATION_GENERATED_FILE_SCHEMA_VERSION = "visual-signature-calibration-generated-file-1"
CALIBRATION_REVIEW_OUTCOME_SCHEMA_VERSION = "visual-signature-calibration-review-outcome-1"
CALIBRATION_RECORD_SCHEMA_VERSION = "visual-signature-calibration-record-1"
CALIBRATION_RECORDS_FILE_SCHEMA_VERSION = "visual-signature-calibration-records-1"
CALIBRATION_MANIFEST_SCHEMA_VERSION = "visual-signature-calibration-manifest-1"
CALIBRATION_SUMMARY_SCHEMA_VERSION = "visual-signature-calibration-summary-1"

AgreementState = Literal["confirmed", "contradicted", "unresolved", "insufficient_review"]
ConfidenceBucket = Literal["low", "medium", "high", "unknown"]
UncertaintyAlignment = Literal["calibrated", "overconfident", "underconfident", "uncertainty_accepted", "insufficient_data"]
ReviewStatus = Literal["approved", "rejected", "needs_more_evidence"]
VisuallySupported = Literal["yes", "partial", "no"]

ConfidenceScore = Annotated[float, Field(ge=0.0, le=1.0)]
NonEmptyString = Annotated[str, Field(min_length=1)]


class CalibrationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PerceptionClaim(CalibrationModel):
    schema_version: Literal[CALIBRATION_CLAIM_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["perception_claim"]
    claim_id: NonEmptyString
    claim_kind: NonEmptyString
    claim_value: NonEmptyString
    confidence: ConfidenceScore
    confidence_bucket: ConfidenceBucket
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    lineage_refs: list[NonEmptyString] = Field(default_factory=list)
    notes: list[NonEmptyString] = Field(default_factory=list)


class ReviewOutcome(CalibrationModel):
    schema_version: Literal[CALIBRATION_REVIEW_OUTCOME_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["review_outcome"]
    review_id: NonEmptyString | None = None
    capture_id: NonEmptyString
    reviewer_id: NonEmptyString | None = None
    reviewed_at: datetime | None = None
    review_status: ReviewStatus
    visually_supported: VisuallySupported
    unsupported_inference_present: bool
    uncertainty_accepted: bool
    notes: list[NonEmptyString] = Field(default_factory=list)


class CalibrationRecord(CalibrationModel):
    schema_version: Literal[CALIBRATION_RECORD_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["calibration_record"]
    calibration_id: NonEmptyString
    capture_id: NonEmptyString
    brand_name: NonEmptyString
    website_url: NonEmptyString
    category: NonEmptyString
    claim: PerceptionClaim
    review_outcome: ReviewOutcome | None = None
    agreement_state: AgreementState
    confidence_bucket: ConfidenceBucket
    uncertainty_alignment: UncertaintyAlignment
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    lineage_refs: list[NonEmptyString] = Field(default_factory=list)
    source_breakdown: dict[str, int] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    notes: list[NonEmptyString] = Field(default_factory=list)


class CalibrationRecordsFile(CalibrationModel):
    schema_version: Literal[CALIBRATION_RECORDS_FILE_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["calibration_records"]
    calibration_run_id: NonEmptyString
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_phase_one_root: NonEmptyString
    source_phase_two_root: NonEmptyString
    source_capture_manifest_path: NonEmptyString | None = None
    source_dismissal_audit_path: NonEmptyString | None = None
    source_brand_catalog_path: NonEmptyString | None = None
    source_artifact_refs: list[NonEmptyString] = Field(default_factory=list)
    source_artifact_hashes: dict[NonEmptyString, NonEmptyString] = Field(default_factory=dict)
    record_count: int
    schema_versions: dict[NonEmptyString, NonEmptyString] = Field(default_factory=dict)
    records: list[CalibrationRecord]


class CalibrationSummary(CalibrationModel):
    schema_version: Literal[CALIBRATION_SUMMARY_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["calibration_summary"]
    calibration_run_id: NonEmptyString
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_phase_one_root: NonEmptyString
    source_phase_two_root: NonEmptyString
    source_capture_manifest_path: NonEmptyString | None = None
    source_dismissal_audit_path: NonEmptyString | None = None
    source_brand_catalog_path: NonEmptyString | None = None
    source_artifact_refs: list[NonEmptyString] = Field(default_factory=list)
    source_artifact_hashes: dict[NonEmptyString, NonEmptyString] = Field(default_factory=dict)
    record_count: int
    summary_count_consistency: bool
    schema_versions: dict[NonEmptyString, NonEmptyString] = Field(default_factory=dict)
    total_claims: int
    reviewed_claims: int
    confirmed_count: int
    confirmed_rate: float
    contradicted_count: int
    contradicted_rate: float
    unresolved_count: int
    unresolved_rate: float
    insufficient_review_count: int
    insufficient_review_rate: float
    high_confidence_contradiction_count: int
    overconfidence_rate: float
    uncertainty_accepted_count: int
    uncertainty_accepted_rate: float
    agreement_distribution: dict[str, int] = Field(default_factory=dict)
    confidence_bucket_distribution: dict[str, int] = Field(default_factory=dict)
    category_breakdown: dict[str, dict[str, Any]] = Field(default_factory=dict)
    claim_kind_breakdown: dict[str, dict[str, Any]] = Field(default_factory=dict)
    source_breakdown: dict[str, dict[str, Any]] = Field(default_factory=dict)
    review_status_distribution: dict[str, int] = Field(default_factory=dict)
    notes: list[NonEmptyString] = Field(default_factory=list)


class GeneratedFile(CalibrationModel):
    schema_version: Literal[CALIBRATION_GENERATED_FILE_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["generated_file"]
    path: NonEmptyString
    sha256: NonEmptyString
    size_bytes: int


class CalibrationManifest(CalibrationModel):
    schema_version: Literal[CALIBRATION_MANIFEST_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["calibration_manifest"]
    calibration_run_id: NonEmptyString
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_phase_one_root: NonEmptyString
    source_phase_two_root: NonEmptyString
    source_capture_manifest_path: NonEmptyString | None = None
    source_dismissal_audit_path: NonEmptyString | None = None
    source_brand_catalog_path: NonEmptyString | None = None
    source_artifact_refs: list[NonEmptyString] = Field(default_factory=list)
    source_artifact_hashes: dict[NonEmptyString, NonEmptyString] = Field(default_factory=dict)
    record_count: int
    summary_count_consistency: bool
    schema_versions: dict[NonEmptyString, NonEmptyString] = Field(default_factory=dict)
    generated_files: list[GeneratedFile] = Field(default_factory=list)
    validation_status: Literal["valid", "invalid"]
    validation_errors: list[NonEmptyString] = Field(default_factory=list)
    notes: list[NonEmptyString] = Field(default_factory=list)


def confidence_bucket_for_score(score: float | None) -> ConfidenceBucket:
    if score is None:
        return "unknown"
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    if score > 0:
        return "low"
    return "low"


def validate_calibration_record(record: dict[str, Any]) -> list[str]:
    try:
        CalibrationRecord.model_validate(record)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []


def validate_calibration_summary(summary: dict[str, Any]) -> list[str]:
    try:
        CalibrationSummary.model_validate(summary)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []


def validate_calibration_manifest(manifest: dict[str, Any]) -> list[str]:
    try:
        CalibrationManifest.model_validate(manifest)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []


def is_positive_claim_value(value: str) -> bool:
    return value in {"RAW_STATE", "ELIGIBLE_FOR_SAFE_INTERVENTION", "MINIMALLY_MUTATED_STATE"}


def agreement_distribution(records: list[CalibrationRecord]) -> dict[str, int]:
    return dict(sorted(Counter(record.agreement_state for record in records).items()))
