"""Pydantic models for Visual Signature calibration readiness gates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.visual_signature.phase_zero.models import PHASE_ZERO_TAXONOMY_VERSION


CALIBRATION_READINESS_SCHEMA_VERSION = "visual-signature-calibration-readiness-1"

ReadinessStatus = Literal["ready", "not_ready"]
ReadinessScope = Literal[
    "broader_corpus_use",
    "provider_pilot_use",
    "human_review_scaling",
    "production_runtime",
    "scoring_integration",
    "model_training",
]

NonEmptyString = Annotated[str, Field(min_length=1)]


class ReadinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReadinessThresholds(ReadinessModel):
    minimum_total_claims: int
    minimum_reviewed_claims: int
    minimum_categories: int
    minimum_claims_per_category: int
    minimum_confidence_buckets: int
    maximum_contradiction_rate: float
    maximum_high_confidence_contradictions: int
    maximum_unresolved_rate: float


class CoverageStats(ReadinessModel):
    count: int
    share: float
    meets_minimum: bool
    minimum_required: int
    reviewed_count: int = 0


class ReadinessResult(ReadinessModel):
    schema_version: Literal[CALIBRATION_READINESS_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["calibration_readiness"]
    readiness_scope: ReadinessScope = "broader_corpus_use"
    calibration_run_id: NonEmptyString
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ReadinessStatus
    block_reasons: list[NonEmptyString] = Field(default_factory=list)
    warning_reasons: list[NonEmptyString] = Field(default_factory=list)
    bundle_valid: bool
    validation_errors: list[NonEmptyString] = Field(default_factory=list)
    source_corpus_manifest_path: NonEmptyString | None = None
    summary_count_consistency: bool
    record_count: int
    reviewed_claims: int
    category_coverage: dict[str, CoverageStats] = Field(default_factory=dict)
    confidence_bucket_coverage: dict[str, CoverageStats] = Field(default_factory=dict)
    contradiction_rate: float
    unresolved_rate: float
    overconfidence_rate: float
    minimum_thresholds_used: ReadinessThresholds
    recommendation: NonEmptyString
    notes: list[NonEmptyString] = Field(default_factory=list)


def validate_readiness_result(payload: dict[str, Any]) -> list[str]:
    try:
        ReadinessResult.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []
