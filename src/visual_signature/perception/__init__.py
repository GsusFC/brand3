"""Visual Signature perceptual state scaffolding.

This package formalizes the evidence-only perceptual state machine used to
track raw captures, obstructions, safe intervention eligibility, mutations,
and review-required outcomes. It does not affect scoring, rubric dimensions,
production reports, or production UI.
"""

from src.visual_signature.perception.mutation_audit import MutationAuditRecord
from src.visual_signature.perception.perceptual_state_machine import PerceptualStateMachine
from src.visual_signature.perception.state_models import (
    MutationClassification,
    PerceptualStateSnapshot,
    StateEvaluation,
    TransitionRecord,
)
from src.visual_signature.perception.transition_policy import (
    classify_mutation_result,
    classify_obstruction_state,
    evaluate_intervention_eligibility,
)

__all__ = [
    "MutationAuditRecord",
    "MutationClassification",
    "PerceptualStateMachine",
    "PerceptualStateSnapshot",
    "StateEvaluation",
    "TransitionRecord",
    "classify_mutation_result",
    "classify_obstruction_state",
    "evaluate_intervention_eligibility",
]
