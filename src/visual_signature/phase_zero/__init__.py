"""Phase Zero artifacts for Brand3 Visual Signature.

Phase Zero is the contract layer: taxonomy, registries, schemas, eligibility
rules, reasoning trace format, and fixtures used to validate the foundation
before additional perceptual logic is added.
"""

from __future__ import annotations

from pathlib import Path

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

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

_EXPORTS = {
    "DATASET_ELIGIBILITY_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "DATASET_ELIGIBILITY_SCHEMA_VERSION"),
    "MUTATION_AUDIT_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "MUTATION_AUDIT_SCHEMA_VERSION"),
    "OBSERVATION_REGISTRY_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "OBSERVATION_REGISTRY_SCHEMA_VERSION"),
    "OBSERVATION_RECORD_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "OBSERVATION_RECORD_SCHEMA_VERSION"),
    "PHASE_ZERO_TAXONOMY_VERSION": ("src.visual_signature.phase_zero.models", "PHASE_ZERO_TAXONOMY_VERSION"),
    "REASONING_TRACE_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "REASONING_TRACE_SCHEMA_VERSION"),
    "REVIEW_RECORD_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "REVIEW_RECORD_SCHEMA_VERSION"),
    "SCORING_REGISTRY_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "SCORING_REGISTRY_SCHEMA_VERSION"),
    "STATE_RECORD_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "STATE_RECORD_SCHEMA_VERSION"),
    "STATE_REGISTRY_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "STATE_REGISTRY_SCHEMA_VERSION"),
    "TRANSITION_RECORD_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "TRANSITION_RECORD_SCHEMA_VERSION"),
    "TRANSITION_REGISTRY_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "TRANSITION_REGISTRY_SCHEMA_VERSION"),
    "UNCERTAINTY_POLICY_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "UNCERTAINTY_POLICY_SCHEMA_VERSION"),
    "UNCERTAINTY_PROFILE_SCHEMA_VERSION": ("src.visual_signature.phase_zero.models", "UNCERTAINTY_PROFILE_SCHEMA_VERSION"),
    "DatasetEligibilityRecord": ("src.visual_signature.phase_zero.models", "DatasetEligibilityRecord"),
    "MutationAuditRecord": ("src.visual_signature.phase_zero.models", "MutationAuditRecord"),
    "ObservationDefinition": ("src.visual_signature.phase_zero.models", "ObservationDefinition"),
    "ObservationRegistry": ("src.visual_signature.phase_zero.models", "ObservationRegistry"),
    "PerceptualObservationRecord": ("src.visual_signature.phase_zero.models", "PerceptualObservationRecord"),
    "PerceptualStateRecord": ("src.visual_signature.phase_zero.models", "PerceptualStateRecord"),
    "ReasoningStatement": ("src.visual_signature.phase_zero.models", "ReasoningStatement"),
    "ReasoningTrace": ("src.visual_signature.phase_zero.models", "ReasoningTrace"),
    "ReviewRecord": ("src.visual_signature.phase_zero.models", "ReviewRecord"),
    "ScoreDefinition": ("src.visual_signature.phase_zero.models", "ScoreDefinition"),
    "ScoringRegistry": ("src.visual_signature.phase_zero.models", "ScoringRegistry"),
    "StateDefinition": ("src.visual_signature.phase_zero.models", "StateDefinition"),
    "StateRegistry": ("src.visual_signature.phase_zero.models", "StateRegistry"),
    "TransitionDefinition": ("src.visual_signature.phase_zero.models", "TransitionDefinition"),
    "TransitionRecord": ("src.visual_signature.phase_zero.models", "TransitionRecord"),
    "TransitionRegistry": ("src.visual_signature.phase_zero.models", "TransitionRegistry"),
    "UncertaintyPolicy": ("src.visual_signature.phase_zero.models", "UncertaintyPolicy"),
    "UncertaintyProfile": ("src.visual_signature.phase_zero.models", "UncertaintyProfile"),
    "evaluate_dataset_eligibility": ("src.visual_signature.phase_zero.eligibility", "evaluate_dataset_eligibility"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
