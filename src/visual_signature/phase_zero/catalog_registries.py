"""Registry and policy records for the phase zero catalog."""

from __future__ import annotations

from src.visual_signature.phase_zero.models import (
    OBSERVATION_REGISTRY_SCHEMA_VERSION,
    PHASE_ZERO_TAXONOMY_VERSION,
    SCORING_REGISTRY_SCHEMA_VERSION,
    STATE_REGISTRY_SCHEMA_VERSION,
    TRANSITION_REGISTRY_SCHEMA_VERSION,
    UNCERTAINTY_POLICY_SCHEMA_VERSION,
)


OBSERVATION_REGISTRY = {
    "schema_version": OBSERVATION_REGISTRY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "registry_type": "observation_registry",
    "items": [
        {"key": "obstruction", "layer": "functional", "description": "Visible viewport blocking elements or overlays.", "value_type": "categorical", "notes": ["Used to gate safe intervention eligibility."]},
        {"key": "cta_clarity", "layer": "functional", "description": "How easy the primary call to action is to identify.", "value_type": "categorical", "notes": ["Separate from CTA effectiveness or conversion impact."]},
        {"key": "navigation_clarity", "layer": "functional", "description": "How easy primary navigation is to detect and use.", "value_type": "categorical", "notes": ["Avoids conflating hidden routes with visible hierarchy."]},
        {"key": "density", "layer": "functional", "description": "How visually dense the viewport feels.", "value_type": "categorical", "notes": ["Observation only; not automatically good or bad."]},
        {"key": "visual_tone", "layer": "editorial", "description": "Overall visual mood or tone.", "value_type": "categorical", "notes": ["Supports editorial / brand perception."]},
        {"key": "brand_consistency", "layer": "editorial", "description": "Consistency of visual language across the viewport.", "value_type": "categorical", "notes": ["Does not imply sameness or sameness as quality."]},
        {"key": "expressive_density", "layer": "editorial", "description": "How much expressive visual variation is present.", "value_type": "categorical", "notes": ["Useful for creative intent versus noise analysis."]},
        {"key": "creative_intent", "layer": "editorial", "description": "Whether irregularity reads as intentional rather than error.", "value_type": "categorical", "notes": ["Used to avoid treating rule-breaking as defect by default."]},
    ],
}

STATE_REGISTRY = {
    "schema_version": STATE_REGISTRY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "registry_type": "state_registry",
    "items": [
        {"key": "RAW_STATE", "description": "Raw viewport capture before any mutation or intervention.", "terminal": False, "review_required": False, "mutation_allowed": False},
        {"key": "OBSTRUCTED_STATE", "description": "Viewport is obstructed by a visible overlay or blocking layer.", "terminal": False, "review_required": False, "mutation_allowed": False},
        {"key": "ELIGIBLE_FOR_SAFE_INTERVENTION", "description": "A reversible, exact affordance is present and safe to attempt.", "terminal": False, "review_required": False, "mutation_allowed": True},
        {"key": "MINIMALLY_MUTATED_STATE", "description": "A safe, reversible mutation succeeded and raw evidence is preserved.", "terminal": False, "review_required": False, "mutation_allowed": False},
        {"key": "UNSAFE_MUTATION_BLOCKED", "description": "Intervention was blocked because the environment is protected or ambiguous.", "terminal": True, "review_required": True, "mutation_allowed": False},
        {"key": "REVIEW_REQUIRED_STATE", "description": "Perception exists but needs human validation before export or action.", "terminal": True, "review_required": True, "mutation_allowed": False},
    ],
}

TRANSITION_REGISTRY = {
    "schema_version": TRANSITION_REGISTRY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "registry_type": "transition_registry",
    "items": [
        {"key": "raw_capture_created", "from_states": [], "to_state": "RAW_STATE", "description": "Raw viewport evidence was captured.", "requires_lineage": True, "requires_evidence": True},
        {"key": "viewport_obstruction_detected", "from_states": ["RAW_STATE"], "to_state": "OBSTRUCTED_STATE", "description": "Viewport evidence contains an obstruction.", "requires_lineage": True, "requires_evidence": True},
        {"key": "no_obstruction_detected", "from_states": ["RAW_STATE"], "to_state": "RAW_STATE", "description": "No obstruction was found in the raw viewport.", "requires_lineage": True, "requires_evidence": True},
        {"key": "exact_safe_affordance_detected", "from_states": ["OBSTRUCTED_STATE"], "to_state": "ELIGIBLE_FOR_SAFE_INTERVENTION", "description": "An obvious reversible affordance is present.", "requires_lineage": True, "requires_evidence": True},
        {"key": "no_safe_affordance_detected", "from_states": ["OBSTRUCTED_STATE"], "to_state": "REVIEW_REQUIRED_STATE", "description": "The obstruction is visible but no safe affordance is obvious.", "requires_lineage": True, "requires_evidence": True},
        {"key": "protected_environment_detected", "from_states": ["OBSTRUCTED_STATE"], "to_state": "UNSAFE_MUTATION_BLOCKED", "description": "The overlay looks like a protected environment such as login or paywall.", "requires_lineage": True, "requires_evidence": True},
        {"key": "safe_mutation_attempted", "from_states": ["ELIGIBLE_FOR_SAFE_INTERVENTION"], "to_state": "ELIGIBLE_FOR_SAFE_INTERVENTION", "description": "A safe intervention was attempted.", "requires_lineage": True, "requires_evidence": True},
        {"key": "safe_mutation_succeeded", "from_states": ["ELIGIBLE_FOR_SAFE_INTERVENTION"], "to_state": "MINIMALLY_MUTATED_STATE", "description": "A safe intervention succeeded and raw evidence remains preserved.", "requires_lineage": True, "requires_evidence": True},
        {"key": "safe_mutation_failed", "from_states": ["ELIGIBLE_FOR_SAFE_INTERVENTION"], "to_state": "REVIEW_REQUIRED_STATE", "description": "A safe intervention failed and the raw state remains primary.", "requires_lineage": True, "requires_evidence": True},
        {"key": "human_review_required", "from_states": ["OBSTRUCTED_STATE", "REVIEW_REQUIRED_STATE"], "to_state": "REVIEW_REQUIRED_STATE", "description": "A human reviewer is required to resolve uncertainty.", "requires_lineage": True, "requires_evidence": True},
    ],
}

SCORING_REGISTRY = {
    "schema_version": SCORING_REGISTRY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "registry_type": "scoring_registry",
    "items": [
        {"key": "functional_readability", "description": "Visible clarity of structure, CTA, and navigation.", "observation_keys": ["obstruction", "cta_clarity", "navigation_clarity", "density"], "enabled": False, "boundary_note": "Evidence only in Phase Zero."},
        {"key": "editorial_signal_strength", "description": "Visible tone, rhythm, tension, and consistency.", "observation_keys": ["visual_tone", "brand_consistency", "expressive_density", "creative_intent"], "enabled": False, "boundary_note": "Observation layer only until a future explicit decision."},
        {"key": "perceptual_confidence", "description": "Confidence that observations are trustworthy enough to export.", "observation_keys": ["confidence"], "enabled": False, "boundary_note": "Used for dataset eligibility, not scoring."},
        {"key": "lineage_stability", "description": "How stable the perceptual signature is over time.", "observation_keys": ["perceptual_state", "transition_record"], "enabled": False, "boundary_note": "Reserved for drift analysis, not user-facing scoring."},
    ],
}

UNCERTAINTY_POLICY = {
    "schema_version": UNCERTAINTY_POLICY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "policy_type": "uncertainty_policy",
    "confidence_threshold": 0.8,
    "reviewer_required_threshold": 0.65,
    "known_unknown_labels": ["insufficient_viewport", "ambiguous_creative_intent", "mixed_affordance_signals", "hidden_navigation_uncertainty", "aesthetic_uncertainty"],
    "uncertainty_reasons": ["insufficient_viewport", "ambiguous_creative_intent", "mixed_affordance_signals", "hidden_navigation_uncertainty", "aesthetic_uncertainty"],
    "reviewer_required_labels": ["needs_human_validation", "inference_not_supported", "state_ambiguity"],
}
