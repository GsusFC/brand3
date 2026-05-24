"""Phase Zero artifacts for Brand3 Visual Signature.

Phase Zero is the contract layer: taxonomy, registries, schemas, eligibility
rules, reasoning trace format, and fixtures used to validate the foundation
before additional perceptual logic is added.
"""

from __future__ import annotations

from pathlib import Path

from src.visual_signature.phase_zero.eligibility import evaluate_dataset_eligibility
from src.visual_signature.phase_zero.models import (
    DATASET_ELIGIBILITY_SCHEMA_VERSION,
    MUTATION_AUDIT_SCHEMA_VERSION,
    OBSERVATION_REGISTRY_SCHEMA_VERSION,
    OBSERVATION_RECORD_SCHEMA_VERSION,
    PHASE_ZERO_TAXONOMY_VERSION,
    REASONING_TRACE_SCHEMA_VERSION,
    REVIEW_RECORD_SCHEMA_VERSION,
    SCORING_REGISTRY_SCHEMA_VERSION,
    STATE_RECORD_SCHEMA_VERSION,
    STATE_REGISTRY_SCHEMA_VERSION,
    TRANSITION_RECORD_SCHEMA_VERSION,
    TRANSITION_REGISTRY_SCHEMA_VERSION,
    UNCERTAINTY_POLICY_SCHEMA_VERSION,
    UNCERTAINTY_PROFILE_SCHEMA_VERSION,
    DatasetEligibilityRecord,
    MutationAuditRecord,
    ObservationDefinition,
    ObservationRegistry,
    PerceptualObservationRecord,
    PerceptualStateRecord,
    ReasoningStatement,
    ReasoningTrace,
    ReviewRecord,
    ScoreDefinition,
    ScoringRegistry,
    StateDefinition,
    StateRegistry,
    TransitionDefinition,
    TransitionRecord,
    TransitionRegistry,
    UncertaintyPolicy,
    UncertaintyProfile,
)

PHASE_ZERO_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "phase_zero"

__all__ = [
    "DATASET_ELIGIBILITY_SCHEMA_VERSION",
    "MUTATION_AUDIT_SCHEMA_VERSION",
    "OBSERVATION_REGISTRY_SCHEMA_VERSION",
    "OBSERVATION_RECORD_SCHEMA_VERSION",
    "PHASE_ZERO_ROOT",
    "PHASE_ZERO_TAXONOMY_VERSION",
    "REASONING_TRACE_SCHEMA_VERSION",
    "REVIEW_RECORD_SCHEMA_VERSION",
    "SCORING_REGISTRY_SCHEMA_VERSION",
    "STATE_RECORD_SCHEMA_VERSION",
    "STATE_REGISTRY_SCHEMA_VERSION",
    "TRANSITION_RECORD_SCHEMA_VERSION",
    "TRANSITION_REGISTRY_SCHEMA_VERSION",
    "UNCERTAINTY_POLICY_SCHEMA_VERSION",
    "UNCERTAINTY_PROFILE_SCHEMA_VERSION",
    "DatasetEligibilityRecord",
    "MutationAuditRecord",
    "ObservationDefinition",
    "ObservationRegistry",
    "PerceptualObservationRecord",
    "PerceptualStateRecord",
    "ReasoningStatement",
    "ReasoningTrace",
    "ReviewRecord",
    "ScoreDefinition",
    "ScoringRegistry",
    "StateDefinition",
    "StateRegistry",
    "TransitionDefinition",
    "TransitionRecord",
    "TransitionRegistry",
    "UncertaintyPolicy",
    "UncertaintyProfile",
    "evaluate_dataset_eligibility",
]
