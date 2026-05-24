"""Pydantic models for the Visual Signature corpus expansion pilot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.visual_signature.calibration.readiness_models import ReadinessScope


CORPUS_EXPANSION_QUEUE_ITEM_SCHEMA_VERSION = "visual-signature-corpus-expansion-queue-item-1"
CORPUS_EXPANSION_REVIEW_QUEUE_SCHEMA_VERSION = "visual-signature-corpus-expansion-review-queue-1"
CORPUS_EXPANSION_METRICS_SCHEMA_VERSION = "visual-signature-corpus-expansion-metrics-1"
CORPUS_EXPANSION_MANIFEST_SCHEMA_VERSION = "visual-signature-corpus-expansion-manifest-1"
CORPUS_EXPANSION_READINESS_SCHEMA_VERSION = "visual-signature-corpus-expansion-readiness-1"

CorpusExpansionQueueState = Literal["queued", "reviewed", "unresolved", "needs_additional_evidence"]
CorpusExpansionReviewOutcome = Literal["confirmed", "contradicted", "unresolved", "insufficient_review"]
CorpusExpansionReadinessStatus = Literal["ready", "not_ready"]
ConfidenceBucket = Literal["low", "medium", "high", "unknown"]

NonEmptyString = Annotated[str, Field(min_length=1)]
Percentage = Annotated[float, Field(ge=0.0, le=1.0)]


class CorpusExpansionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CorpusExpansionQueueItem(CorpusExpansionModel):
    schema_version: Literal[CORPUS_EXPANSION_QUEUE_ITEM_SCHEMA_VERSION]
    record_type: Literal["corpus_expansion_queue_item"]
    queue_id: NonEmptyString
    capture_id: NonEmptyString
    brand_name: NonEmptyString
    website_url: NonEmptyString
    category: NonEmptyString
    queue_state: CorpusExpansionQueueState
    review_outcome: CorpusExpansionReviewOutcome | None = None
    confidence_bucket: ConfidenceBucket = "unknown"
    reviewer_id: NonEmptyString | None = None
    reviewed_at: datetime | None = None
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    notes: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_state_alignment(self) -> "CorpusExpansionQueueItem":
        if self.queue_state == "queued":
            if self.review_outcome is not None:
                raise ValueError("queued items must not include review_outcome")
            if self.reviewer_id is not None or self.reviewed_at is not None:
                raise ValueError("queued items must not include reviewer metadata")
        elif self.queue_state == "reviewed":
            if self.review_outcome not in {"confirmed", "contradicted"}:
                raise ValueError("reviewed items require confirmed or contradicted review_outcome")
            if self.reviewer_id is None or self.reviewed_at is None:
                raise ValueError("reviewed items require reviewer_id and reviewed_at")
        elif self.queue_state == "unresolved":
            if self.review_outcome != "unresolved":
                raise ValueError("unresolved items require unresolved review_outcome")
        elif self.queue_state == "needs_additional_evidence":
            if self.review_outcome not in {None, "insufficient_review"}:
                raise ValueError("needs_additional_evidence items cannot be confirmed or contradicted")
        return self


class CorpusExpansionReviewQueue(CorpusExpansionModel):
    schema_version: Literal[CORPUS_EXPANSION_REVIEW_QUEUE_SCHEMA_VERSION]
    record_type: Literal["corpus_expansion_review_queue"]
    pilot_run_id: NonEmptyString
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_capture_count: int = Field(ge=0)
    current_capture_count: int = Field(ge=0)
    reviewed_capture_count: int = Field(ge=0)
    category_distribution: dict[str, int] = Field(default_factory=dict)
    confidence_distribution: dict[str, int] = Field(default_factory=dict)
    queue_state_distribution: dict[str, int] = Field(default_factory=dict)
    queue_items: list[CorpusExpansionQueueItem] = Field(default_factory=list)
    readiness_scope: ReadinessScope = "human_review_scaling"
    readiness_status: CorpusExpansionReadinessStatus = "not_ready"
    notes: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_queue(self) -> "CorpusExpansionReviewQueue":
        if self.current_capture_count != len(self.queue_items):
            raise ValueError("current_capture_count does not match queue length")
        if self.reviewed_capture_count > self.current_capture_count:
            raise ValueError("reviewed_capture_count cannot exceed current_capture_count")
        _validate_distribution("category_distribution", self.category_distribution, self.current_capture_count)
        _validate_distribution("confidence_distribution", self.confidence_distribution, self.current_capture_count)
        _validate_distribution("queue_state_distribution", self.queue_state_distribution, self.current_capture_count)
        return self


class CorpusExpansionMetrics(CorpusExpansionModel):
    schema_version: Literal[CORPUS_EXPANSION_METRICS_SCHEMA_VERSION]
    record_type: Literal["corpus_expansion_metrics"]
    pilot_run_id: NonEmptyString
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_capture_count: int = Field(ge=0)
    current_capture_count: int = Field(ge=0)
    reviewed_capture_count: int = Field(ge=0)
    queued_capture_count: int = Field(ge=0)
    unresolved_capture_count: int = Field(ge=0)
    needs_additional_evidence_count: int = Field(ge=0)
    confirmed_count: int = Field(ge=0)
    contradicted_count: int = Field(ge=0)
    category_distribution: dict[str, int] = Field(default_factory=dict)
    confidence_distribution: dict[str, int] = Field(default_factory=dict)
    queue_state_distribution: dict[str, int] = Field(default_factory=dict)
    contradiction_rate: Percentage
    unresolved_rate: Percentage
    reviewer_coverage: Percentage
    readiness_scope: ReadinessScope = "human_review_scaling"
    readiness_status: CorpusExpansionReadinessStatus = "not_ready"
    insufficient_for_model_training: bool = True
    insufficient_for_production_scoring: bool = True
    evidence_only_corpus_expansion: bool = True
    known_limitations: list[NonEmptyString] = Field(default_factory=list)
    notes: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_metrics(self) -> "CorpusExpansionMetrics":
        if self.reviewed_capture_count > self.current_capture_count:
            raise ValueError("reviewed_capture_count cannot exceed current_capture_count")
        _validate_distribution("category_distribution", self.category_distribution, self.current_capture_count)
        _validate_distribution("confidence_distribution", self.confidence_distribution, self.current_capture_count)
        _validate_distribution("queue_state_distribution", self.queue_state_distribution, self.current_capture_count)
        _validate_rate("contradiction_rate", self.contradiction_rate)
        _validate_rate("unresolved_rate", self.unresolved_rate)
        _validate_rate("reviewer_coverage", self.reviewer_coverage)
        return self


class CorpusExpansionManifest(CorpusExpansionModel):
    schema_version: Literal[CORPUS_EXPANSION_MANIFEST_SCHEMA_VERSION]
    record_type: Literal["corpus_expansion_manifest"]
    pilot_run_id: NonEmptyString
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_capture_count: int = Field(ge=0)
    current_capture_count: int = Field(ge=0)
    reviewed_capture_count: int = Field(ge=0)
    category_distribution: dict[str, int] = Field(default_factory=dict)
    confidence_distribution: dict[str, int] = Field(default_factory=dict)
    queue_state_distribution: dict[str, int] = Field(default_factory=dict)
    contradiction_rate: Percentage
    unresolved_rate: Percentage
    reviewer_coverage: Percentage
    readiness_scope: ReadinessScope = "human_review_scaling"
    readiness_status: CorpusExpansionReadinessStatus = "not_ready"
    known_limitations: list[NonEmptyString] = Field(default_factory=list)
    metrics_file: NonEmptyString | None = None
    review_queue_file: NonEmptyString | None = None
    notes: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_manifest(self) -> "CorpusExpansionManifest":
        if self.reviewed_capture_count > self.current_capture_count:
            raise ValueError("reviewed_capture_count cannot exceed current_capture_count")
        _validate_distribution("category_distribution", self.category_distribution, self.current_capture_count)
        _validate_distribution("confidence_distribution", self.confidence_distribution, self.current_capture_count)
        _validate_distribution("queue_state_distribution", self.queue_state_distribution, self.current_capture_count)
        _validate_rate("contradiction_rate", self.contradiction_rate)
        _validate_rate("unresolved_rate", self.unresolved_rate)
        _validate_rate("reviewer_coverage", self.reviewer_coverage)
        return self


class CorpusExpansionReadinessAssessment(CorpusExpansionModel):
    schema_version: Literal[CORPUS_EXPANSION_READINESS_SCHEMA_VERSION]
    record_type: Literal["corpus_expansion_readiness"]
    pilot_run_id: NonEmptyString
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    readiness_scope: ReadinessScope = "human_review_scaling"
    readiness_status: CorpusExpansionReadinessStatus = "not_ready"
    block_reasons: list[NonEmptyString] = Field(default_factory=list)
    warning_reasons: list[NonEmptyString] = Field(default_factory=list)
    thresholds_used: dict[str, float | int] = Field(default_factory=dict)
    current_capture_count: int = Field(ge=0, default=0)
    reviewed_capture_count: int = Field(ge=0, default=0)
    category_coverage: list[NonEmptyString] = Field(default_factory=list)
    confidence_bucket_coverage: list[NonEmptyString] = Field(default_factory=list)
    contradiction_rate: Percentage = 0.0
    unresolved_rate: Percentage = 0.0
    reviewer_coverage: Percentage = 0.0


class ValidationResult(CorpusExpansionModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def validate_corpus_expansion_queue_item(payload: dict[str, Any]) -> list[str]:
    try:
        CorpusExpansionQueueItem.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []


def validate_corpus_expansion_review_queue_payload(payload: dict[str, Any]) -> list[str]:
    try:
        CorpusExpansionReviewQueue.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []


def validate_corpus_expansion_metrics_payload(payload: dict[str, Any]) -> list[str]:
    try:
        CorpusExpansionMetrics.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []


def validate_corpus_expansion_manifest_payload(payload: dict[str, Any]) -> list[str]:
    try:
        CorpusExpansionManifest.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []


def validate_corpus_expansion_readiness_payload(payload: dict[str, Any]) -> list[str]:
    try:
        CorpusExpansionReadinessAssessment.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []


def _validate_distribution(label: str, distribution: dict[str, int], expected_total: int) -> None:
    if any(count < 0 for count in distribution.values()):
        raise ValueError(f"{label} cannot contain negative counts")
    if distribution and sum(distribution.values()) != expected_total:
        raise ValueError(f"{label} must sum to {expected_total}")


def _validate_rate(label: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")
