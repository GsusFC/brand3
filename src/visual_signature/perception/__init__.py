"""Visual Signature perceptual state scaffolding.

This package formalizes the evidence-only perceptual state machine used to
track raw captures, obstructions, safe intervention eligibility, mutations,
and review-required outcomes. It does not affect scoring, rubric dimensions,
production reports, or production UI.
"""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "PerceptualStateMachine",
    "classify_mutation_result",
    "classify_obstruction_state",
    "evaluate_intervention_eligibility",
]

_EXPORTS = {
    "PerceptualStateMachine": ("src.visual_signature.perception.perceptual_state_machine", "PerceptualStateMachine"),
    "classify_mutation_result": ("src.visual_signature.perception.transition_policy", "classify_mutation_result"),
    "classify_obstruction_state": ("src.visual_signature.perception.transition_policy", "classify_obstruction_state"),
    "evaluate_intervention_eligibility": (
        "src.visual_signature.perception.transition_policy",
        "evaluate_intervention_eligibility",
    ),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
