"""Pydantic models for Phase Zero artifacts.

The models are intentionally small and extensible. They provide the machine
contracts used by the Phase Zero registries, record fixtures, validation
scripts, and TypeScript interfaces.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


PHASE_ZERO_TAXONOMY_VERSION = "phase-zero-taxonomy-1"

OBSERVATION_REGISTRY_SCHEMA_VERSION = "phase-zero-observation-registry-1"
STATE_REGISTRY_SCHEMA_VERSION = "phase-zero-state-registry-1"
TRANSITION_REGISTRY_SCHEMA_VERSION = "phase-zero-transition-registry-1"
SCORING_REGISTRY_SCHEMA_VERSION = "phase-zero-scoring-registry-1"
UNCERTAINTY_POLICY_SCHEMA_VERSION = "phase-zero-uncertainty-policy-1"
UNCERTAINTY_PROFILE_SCHEMA_VERSION = "phase-zero-uncertainty-profile-1"
REASONING_TRACE_SCHEMA_VERSION = "phase-zero-reasoning-trace-1"
OBSERVATION_RECORD_SCHEMA_VERSION = "phase-zero-perceptual-observation-1"
STATE_RECORD_SCHEMA_VERSION = "phase-zero-perceptual-state-1"
TRANSITION_RECORD_SCHEMA_VERSION = "phase-zero-transition-record-1"
MUTATION_AUDIT_SCHEMA_VERSION = "phase-zero-mutation-audit-1"
DATASET_ELIGIBILITY_SCHEMA_VERSION = "phase-zero-dataset-eligibility-1"
REVIEW_RECORD_SCHEMA_VERSION = "phase-zero-review-record-1"


class PhaseZeroModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ConfidenceScore = Annotated[float, Field(ge=0.0, le=1.0)]
SchemaVersion = Annotated[str, Field(min_length=1)]
NonEmptyString = Annotated[str, Field(min_length=1)]


class ObservationDefinition(PhaseZeroModel):
    key: NonEmptyString
    layer: Literal["functional", "editorial"]
    description: NonEmptyString
    value_type: Literal["categorical", "numeric", "boolean", "text"]
    notes: list[str] = Field(default_factory=list)


class ObservationRegistry(PhaseZeroModel):
    schema_version: Literal[OBSERVATION_REGISTRY_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    registry_type: Literal["observation_registry"]
    items: list[ObservationDefinition]


class StateDefinition(PhaseZeroModel):
    key: NonEmptyString
    description: NonEmptyString
    terminal: bool = False
    review_required: bool = False
    mutation_allowed: bool = False


class StateRegistry(PhaseZeroModel):
    schema_version: Literal[STATE_REGISTRY_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    registry_type: Literal["state_registry"]
    items: list[StateDefinition]


class TransitionDefinition(PhaseZeroModel):
    key: NonEmptyString
    from_states: list[NonEmptyString]
    to_state: NonEmptyString
    description: NonEmptyString
    requires_lineage: bool = True
    requires_evidence: bool = True


class TransitionRegistry(PhaseZeroModel):
    schema_version: Literal[TRANSITION_REGISTRY_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    registry_type: Literal["transition_registry"]
    items: list[TransitionDefinition]


class ScoreDefinition(PhaseZeroModel):
    key: NonEmptyString
    description: NonEmptyString
    observation_keys: list[NonEmptyString]
    enabled: bool = False
    boundary_note: NonEmptyString


class ScoringRegistry(PhaseZeroModel):
    schema_version: Literal[SCORING_REGISTRY_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    registry_type: Literal["scoring_registry"]
    items: list[ScoreDefinition]


class UncertaintyPolicy(PhaseZeroModel):
    schema_version: Literal[UNCERTAINTY_POLICY_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    policy_type: Literal["uncertainty_policy"]
    confidence_threshold: ConfidenceScore = 0.8
    reviewer_required_threshold: ConfidenceScore = 0.65
    known_unknown_labels: list[NonEmptyString]
    uncertainty_reasons: list[NonEmptyString]
    reviewer_required_labels: list[NonEmptyString]


class UncertaintyProfile(PhaseZeroModel):
    schema_version: Literal[UNCERTAINTY_PROFILE_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["uncertainty_profile"]
    confidence: ConfidenceScore
    confidence_level: Literal["low", "medium", "high"]
    known_unknowns: list[NonEmptyString] = Field(default_factory=list)
    uncertainty_reasons: list[NonEmptyString] = Field(default_factory=list)
    reviewer_required: bool = False
    unsupported_inference: bool = False


class ReasoningStatement(PhaseZeroModel):
    statement: NonEmptyString
    confidence: ConfidenceScore
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    warnings: list[NonEmptyString] = Field(default_factory=list)


class ReasoningTrace(PhaseZeroModel):
    schema_version: Literal[REASONING_TRACE_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["reasoning_trace"]
    trace_id: NonEmptyString
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: NonEmptyString
    statements: list[ReasoningStatement]
    unsupported_inference_warnings: list[NonEmptyString] = Field(default_factory=list)
    review_required: bool = False
    lineage_refs: list[NonEmptyString] = Field(default_factory=list)


class PerceptualObservationRecord(PhaseZeroModel):
    schema_version: Literal[OBSERVATION_RECORD_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["perceptual_observation"]
    record_id: NonEmptyString
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    capture_id: NonEmptyString
    brand_name: NonEmptyString
    website_url: NonEmptyString
    perception_layer: Literal["functional", "editorial"]
    observation_key: NonEmptyString
    observation_value: NonEmptyString
    confidence: ConfidenceScore
    uncertainty: UncertaintyProfile
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    reasoning_trace: ReasoningTrace
    lineage_refs: list[NonEmptyString] = Field(default_factory=list)


class TransitionRecord(PhaseZeroModel):
    schema_version: Literal[TRANSITION_RECORD_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["transition_record"]
    transition_id: NonEmptyString
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    capture_id: NonEmptyString
    from_state: NonEmptyString
    to_state: NonEmptyString
    reason: NonEmptyString
    confidence: ConfidenceScore
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    lineage_refs: list[NonEmptyString] = Field(default_factory=list)
    mutation_ref: str | None = None
    notes: list[NonEmptyString] = Field(default_factory=list)


class PerceptualStateRecord(PhaseZeroModel):
    schema_version: Literal[STATE_RECORD_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["perceptual_state"]
    record_id: NonEmptyString
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    capture_id: NonEmptyString
    brand_name: NonEmptyString
    website_url: NonEmptyString
    perceptual_state: NonEmptyString
    confidence: ConfidenceScore
    uncertainty: UncertaintyProfile
    transitions: list[TransitionRecord]
    reasoning_trace: ReasoningTrace
    lineage_refs: list[NonEmptyString] = Field(default_factory=list)


class MutationAuditRecord(PhaseZeroModel):
    schema_version: Literal[MUTATION_AUDIT_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["mutation_audit"]
    mutation_id: NonEmptyString
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    capture_id: NonEmptyString
    brand_name: NonEmptyString
    website_url: NonEmptyString
    mutation_type: NonEmptyString
    before_state: NonEmptyString
    after_state: NonEmptyString
    attempted: bool
    successful: bool
    reversible: bool
    risk_level: Literal["low", "medium", "high", "blocking"]
    trigger: NonEmptyString
    evidence_preserved: bool
    before_artifact_ref: NonEmptyString
    after_artifact_ref: str | None = None
    lineage_refs: list[NonEmptyString] = Field(default_factory=list)
    integrity_notes: list[NonEmptyString] = Field(default_factory=list)


class ReviewRecord(PhaseZeroModel):
    schema_version: Literal[REVIEW_RECORD_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["review_record"]
    review_id: NonEmptyString
    capture_id: NonEmptyString
    reviewer_id: NonEmptyString
    reviewed_at: datetime
    review_status: Literal["approved", "rejected", "needs_more_evidence"]
    visually_supported: Literal["yes", "partial", "no"]
    unsupported_inference_present: bool
    uncertainty_accepted: bool
    notes: list[NonEmptyString] = Field(default_factory=list)


class DatasetEligibilityRecord(PhaseZeroModel):
    schema_version: Literal[DATASET_ELIGIBILITY_SCHEMA_VERSION]
    taxonomy_version: Literal[PHASE_ZERO_TAXONOMY_VERSION]
    record_type: Literal["dataset_eligibility"]
    record_id: NonEmptyString
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    capture_id: NonEmptyString
    brand_name: NonEmptyString
    website_url: NonEmptyString
    eligible: bool
    reasons: list[NonEmptyString] = Field(default_factory=list)
    blocked_reasons: list[NonEmptyString] = Field(default_factory=list)
    raw_evidence_preserved: bool
    mutation_lineage_preserved: bool
    schema_valid: bool
    review_required: bool
    review_completed: bool
    uncertainty_below_threshold: bool
    confidence_threshold: ConfidenceScore
    observed_confidence: ConfidenceScore
    unsupported_inference_found: bool
    evidence_refs: list[NonEmptyString] = Field(default_factory=list)
    lineage_refs: list[NonEmptyString] = Field(default_factory=list)
