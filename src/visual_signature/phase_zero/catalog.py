"""Small, versioned Phase Zero catalog data.

This module is the canonical source for the initial taxonomy registries and
fixture records. The generator script writes these dicts to JSON files so the
checked-in artifacts stay synchronized with the Pydantic models.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.visual_signature.phase_zero.models import (
    DATASET_ELIGIBILITY_SCHEMA_VERSION,
    MUTATION_AUDIT_SCHEMA_VERSION,
    OBSERVATION_RECORD_SCHEMA_VERSION,
    OBSERVATION_REGISTRY_SCHEMA_VERSION,
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
)


def _now() -> str:
    return datetime(2026, 5, 11, 10, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


OBSERVATION_REGISTRY = {
    "schema_version": OBSERVATION_REGISTRY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "registry_type": "observation_registry",
    "items": [
        {
            "key": "obstruction",
            "layer": "functional",
            "description": "Visible viewport blocking elements or overlays.",
            "value_type": "categorical",
            "notes": ["Used to gate safe intervention eligibility."],
        },
        {
            "key": "cta_clarity",
            "layer": "functional",
            "description": "How easy the primary call to action is to identify.",
            "value_type": "categorical",
            "notes": ["Separate from CTA effectiveness or conversion impact."],
        },
        {
            "key": "navigation_clarity",
            "layer": "functional",
            "description": "How easy primary navigation is to detect and use.",
            "value_type": "categorical",
            "notes": ["Avoids conflating hidden routes with visible hierarchy."],
        },
        {
            "key": "density",
            "layer": "functional",
            "description": "How visually dense the viewport feels.",
            "value_type": "categorical",
            "notes": ["Observation only; not automatically good or bad."],
        },
        {
            "key": "visual_tone",
            "layer": "editorial",
            "description": "Overall visual mood or tone.",
            "value_type": "categorical",
            "notes": ["Supports editorial / brand perception."],
        },
        {
            "key": "brand_consistency",
            "layer": "editorial",
            "description": "Consistency of visual language across the viewport.",
            "value_type": "categorical",
            "notes": ["Does not imply sameness or sameness as quality."],
        },
        {
            "key": "expressive_density",
            "layer": "editorial",
            "description": "How much expressive visual variation is present.",
            "value_type": "categorical",
            "notes": ["Useful for creative intent versus noise analysis."],
        },
        {
            "key": "creative_intent",
            "layer": "editorial",
            "description": "Whether irregularity reads as intentional rather than error.",
            "value_type": "categorical",
            "notes": ["Used to avoid treating rule-breaking as defect by default."],
        },
    ],
}

STATE_REGISTRY = {
    "schema_version": STATE_REGISTRY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "registry_type": "state_registry",
    "items": [
        {
            "key": "RAW_STATE",
            "description": "Raw viewport capture before any mutation or intervention.",
            "terminal": False,
            "review_required": False,
            "mutation_allowed": False,
        },
        {
            "key": "OBSTRUCTED_STATE",
            "description": "Viewport is obstructed by a visible overlay or blocking layer.",
            "terminal": False,
            "review_required": False,
            "mutation_allowed": False,
        },
        {
            "key": "ELIGIBLE_FOR_SAFE_INTERVENTION",
            "description": "A reversible, exact affordance is present and safe to attempt.",
            "terminal": False,
            "review_required": False,
            "mutation_allowed": True,
        },
        {
            "key": "MINIMALLY_MUTATED_STATE",
            "description": "A safe, reversible mutation succeeded and raw evidence is preserved.",
            "terminal": False,
            "review_required": False,
            "mutation_allowed": False,
        },
        {
            "key": "UNSAFE_MUTATION_BLOCKED",
            "description": "Intervention was blocked because the environment is protected or ambiguous.",
            "terminal": True,
            "review_required": True,
            "mutation_allowed": False,
        },
        {
            "key": "REVIEW_REQUIRED_STATE",
            "description": "Perception exists but needs human validation before export or action.",
            "terminal": True,
            "review_required": True,
            "mutation_allowed": False,
        },
    ],
}

TRANSITION_REGISTRY = {
    "schema_version": TRANSITION_REGISTRY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "registry_type": "transition_registry",
    "items": [
        {
            "key": "raw_capture_created",
            "from_states": [],
            "to_state": "RAW_STATE",
            "description": "Raw viewport evidence was captured.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
        {
            "key": "viewport_obstruction_detected",
            "from_states": ["RAW_STATE"],
            "to_state": "OBSTRUCTED_STATE",
            "description": "Viewport evidence contains an obstruction.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
        {
            "key": "no_obstruction_detected",
            "from_states": ["RAW_STATE"],
            "to_state": "RAW_STATE",
            "description": "No obstruction was found in the raw viewport.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
        {
            "key": "exact_safe_affordance_detected",
            "from_states": ["OBSTRUCTED_STATE"],
            "to_state": "ELIGIBLE_FOR_SAFE_INTERVENTION",
            "description": "An obvious reversible affordance is present.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
        {
            "key": "no_safe_affordance_detected",
            "from_states": ["OBSTRUCTED_STATE"],
            "to_state": "REVIEW_REQUIRED_STATE",
            "description": "The obstruction is visible but no safe affordance is obvious.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
        {
            "key": "protected_environment_detected",
            "from_states": ["OBSTRUCTED_STATE"],
            "to_state": "UNSAFE_MUTATION_BLOCKED",
            "description": "The overlay looks like a protected environment such as login or paywall.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
        {
            "key": "safe_mutation_attempted",
            "from_states": ["ELIGIBLE_FOR_SAFE_INTERVENTION"],
            "to_state": "ELIGIBLE_FOR_SAFE_INTERVENTION",
            "description": "A safe intervention was attempted.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
        {
            "key": "safe_mutation_succeeded",
            "from_states": ["ELIGIBLE_FOR_SAFE_INTERVENTION"],
            "to_state": "MINIMALLY_MUTATED_STATE",
            "description": "A safe intervention succeeded and raw evidence remains preserved.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
        {
            "key": "safe_mutation_failed",
            "from_states": ["ELIGIBLE_FOR_SAFE_INTERVENTION"],
            "to_state": "REVIEW_REQUIRED_STATE",
            "description": "A safe intervention failed and the raw state remains primary.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
        {
            "key": "human_review_required",
            "from_states": ["OBSTRUCTED_STATE", "REVIEW_REQUIRED_STATE"],
            "to_state": "REVIEW_REQUIRED_STATE",
            "description": "A human reviewer is required to resolve uncertainty.",
            "requires_lineage": True,
            "requires_evidence": True,
        },
    ],
}

SCORING_REGISTRY = {
    "schema_version": SCORING_REGISTRY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "registry_type": "scoring_registry",
    "items": [
        {
            "key": "functional_readability",
            "description": "Visible clarity of structure, CTA, and navigation.",
            "observation_keys": ["obstruction", "cta_clarity", "navigation_clarity", "density"],
            "enabled": False,
            "boundary_note": "Evidence only in Phase Zero.",
        },
        {
            "key": "editorial_signal_strength",
            "description": "Visible tone, rhythm, tension, and consistency.",
            "observation_keys": ["visual_tone", "brand_consistency", "expressive_density", "creative_intent"],
            "enabled": False,
            "boundary_note": "Observation layer only until a future explicit decision.",
        },
        {
            "key": "perceptual_confidence",
            "description": "Confidence that observations are trustworthy enough to export.",
            "observation_keys": ["confidence"],
            "enabled": False,
            "boundary_note": "Used for dataset eligibility, not scoring.",
        },
        {
            "key": "lineage_stability",
            "description": "How stable the perceptual signature is over time.",
            "observation_keys": ["perceptual_state", "transition_record"],
            "enabled": False,
            "boundary_note": "Reserved for drift analysis, not user-facing scoring.",
        },
    ],
}

UNCERTAINTY_POLICY = {
    "schema_version": UNCERTAINTY_POLICY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "policy_type": "uncertainty_policy",
    "confidence_threshold": 0.8,
    "reviewer_required_threshold": 0.65,
    "known_unknown_labels": [
        "insufficient_viewport",
        "ambiguous_creative_intent",
        "mixed_affordance_signals",
        "hidden_navigation_uncertainty",
        "aesthetic_uncertainty",
    ],
    "uncertainty_reasons": [
        "insufficient_viewport",
        "ambiguous_creative_intent",
        "mixed_affordance_signals",
        "hidden_navigation_uncertainty",
        "aesthetic_uncertainty",
    ],
    "reviewer_required_labels": [
        "needs_human_validation",
        "inference_not_supported",
        "state_ambiguity",
    ],
}

def _uncertainty_profile(
    confidence: float,
    *,
    reasons: list[str] | None = None,
    known_unknowns: list[str] | None = None,
    reviewer_required: bool = False,
    unsupported_inference: bool = False,
) -> dict[str, object]:
    if confidence >= 0.8:
        level = "high"
    elif confidence >= 0.55:
        level = "medium"
    else:
        level = "low"
    return {
        "schema_version": UNCERTAINTY_PROFILE_SCHEMA_VERSION,
        "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
        "record_type": "uncertainty_profile",
        "confidence": confidence,
        "confidence_level": level,
        "known_unknowns": known_unknowns or [],
        "uncertainty_reasons": reasons or [],
        "reviewer_required": reviewer_required,
        "unsupported_inference": unsupported_inference,
    }


UNCERTAINTY_PROFILE = _uncertainty_profile(
    0.78,
    reasons=["mixed_affordance_signals"],
    known_unknowns=["overlay may affect CTA visibility"],
    reviewer_required=True,
)


REASONING_TRACE = {
    "schema_version": REASONING_TRACE_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "record_type": "reasoning_trace",
    "trace_id": "trace_phase_zero_example",
    "created_at": _now(),
    "summary": "The viewport is readable but partially obstructed, so human review is required.",
    "statements": [
        {
            "statement": "A cookie modal covers the lower portion of the viewport.",
            "confidence": 0.92,
            "evidence_refs": ["raw_screenshot_path"],
            "warnings": [],
        },
        {
            "statement": "The primary CTA is visible but its clarity is reduced by the overlay.",
            "confidence": 0.78,
            "evidence_refs": ["raw_screenshot_path", "dom_snapshot_ref"],
            "warnings": [],
        },
    ],
    "unsupported_inference_warnings": [],
    "review_required": True,
    "lineage_refs": ["capture:phase-zero-example"],
}

OBSERVATION_RECORD = {
    "schema_version": OBSERVATION_RECORD_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "record_type": "perceptual_observation",
    "record_id": "obs_phase_zero_example",
    "created_at": _now(),
    "capture_id": "cap_phase_zero_example",
    "brand_name": "Example Brand",
    "website_url": "https://example.com",
    "perception_layer": "functional",
    "observation_key": "cta_clarity",
    "observation_value": "low",
    "confidence": 0.78,
    "uncertainty": UNCERTAINTY_PROFILE,
    "evidence_refs": ["raw_screenshot_path", "dom_snapshot_ref"],
    "reasoning_trace": REASONING_TRACE,
    "lineage_refs": ["capture:phase-zero-example"],
}

STATE_RECORD = {
    "schema_version": STATE_RECORD_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "record_type": "perceptual_state",
    "record_id": "state_phase_zero_example",
    "created_at": _now(),
    "capture_id": "cap_phase_zero_example",
    "brand_name": "Example Brand",
    "website_url": "https://example.com",
    "perceptual_state": "REVIEW_REQUIRED_STATE",
    "confidence": 0.91,
    "uncertainty": _uncertainty_profile(
        0.91,
        reasons=["insufficient_viewport"],
        known_unknowns=["overlay may hide below-the-fold intent"],
        reviewer_required=True,
    ),
    "transitions": [
        {
            "schema_version": TRANSITION_RECORD_SCHEMA_VERSION,
            "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
            "record_type": "transition_record",
            "transition_id": "transition_phase_zero_example",
            "created_at": _now(),
            "capture_id": "cap_phase_zero_example",
            "from_state": "RAW_STATE",
            "to_state": "OBSTRUCTED_STATE",
            "reason": "viewport_obstruction_detected",
            "confidence": 0.93,
            "evidence_refs": ["raw_screenshot_path"],
            "lineage_refs": ["capture:phase-zero-example"],
            "mutation_ref": None,
            "notes": ["cookie modal visible"],
        }
    ],
    "reasoning_trace": REASONING_TRACE,
    "lineage_refs": ["capture:phase-zero-example"],
}

TRANSITION_RECORD = {
    "schema_version": TRANSITION_RECORD_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "record_type": "transition_record",
    "transition_id": "transition_phase_zero_example",
    "created_at": _now(),
    "capture_id": "cap_phase_zero_example",
    "from_state": "RAW_STATE",
    "to_state": "OBSTRUCTED_STATE",
    "reason": "viewport_obstruction_detected",
    "confidence": 0.93,
    "evidence_refs": ["raw_screenshot_path"],
    "lineage_refs": ["capture:phase-zero-example"],
    "mutation_ref": None,
    "notes": ["cookie modal visible"],
}

MUTATION_AUDIT = {
    "schema_version": MUTATION_AUDIT_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "record_type": "mutation_audit",
    "mutation_id": "mutation_phase_zero_example",
    "created_at": _now(),
    "capture_id": "cap_phase_zero_example",
    "brand_name": "Example Brand",
    "website_url": "https://example.com",
    "mutation_type": "cookie_banner_dismissal",
    "before_state": "ELIGIBLE_FOR_SAFE_INTERVENTION",
    "after_state": "REVIEW_REQUIRED_STATE",
    "attempted": True,
    "successful": False,
    "reversible": True,
    "risk_level": "low",
    "trigger": "close",
    "evidence_preserved": True,
    "before_artifact_ref": "examples/visual_signature/phase_zero/fixtures/raw.example.png",
    "after_artifact_ref": "examples/visual_signature/phase_zero/fixtures/clean_attempt.example.png",
    "lineage_refs": ["capture:phase-zero-example", "transition:transition_phase_zero_example"],
    "integrity_notes": [
        "raw_viewport_preserved_as_primary_evidence",
        "clean_attempt_is_supplemental_only",
        "safe_mutation_failed_without_overwriting_raw_state",
    ],
}

DATASET_ELIGIBILITY_RECORD = {
    "schema_version": DATASET_ELIGIBILITY_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "record_type": "dataset_eligibility",
    "record_id": "elig_phase_zero_example",
    "created_at": _now(),
    "capture_id": "cap_phase_zero_example",
    "brand_name": "Example Brand",
    "website_url": "https://example.com",
    "eligible": True,
    "reasons": [
        "raw evidence preserved",
        "schema valid",
        "mutation lineage preserved",
        "no unsupported inference",
        "review completed",
    ],
    "blocked_reasons": [],
    "raw_evidence_preserved": True,
    "mutation_lineage_preserved": True,
    "schema_valid": True,
    "review_required": True,
    "review_completed": True,
    "uncertainty_below_threshold": False,
    "confidence_threshold": 0.8,
    "observed_confidence": 0.91,
    "unsupported_inference_found": False,
    "evidence_refs": ["raw_screenshot_path", "dom_snapshot_ref"],
    "lineage_refs": ["capture:phase-zero-example", "mutation:mutation_phase_zero_example"],
}

REVIEW_RECORD = {
    "schema_version": REVIEW_RECORD_SCHEMA_VERSION,
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "record_type": "review_record",
    "review_id": "review_phase_zero_example",
    "capture_id": "cap_phase_zero_example",
    "reviewer_id": "reviewer_alpha",
    "reviewed_at": _now(),
    "review_status": "approved",
    "visually_supported": "partial",
    "unsupported_inference_present": False,
    "uncertainty_accepted": True,
    "notes": [
        "Viewport obstruction is supported by evidence.",
        "Uncertainty is explicitly acknowledged and accepted.",
    ],
}


PHASE_ZERO_MANIFEST = {
    "schema_version": "phase-zero-manifest-1",
    "phase": "phase_zero",
    "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
    "schema_versions": {
        "observation_registry": OBSERVATION_REGISTRY_SCHEMA_VERSION,
        "state_registry": STATE_REGISTRY_SCHEMA_VERSION,
        "transition_registry": TRANSITION_REGISTRY_SCHEMA_VERSION,
        "scoring_registry": SCORING_REGISTRY_SCHEMA_VERSION,
        "uncertainty_policy": UNCERTAINTY_POLICY_SCHEMA_VERSION,
        "uncertainty_profile": UNCERTAINTY_PROFILE_SCHEMA_VERSION,
        "reasoning_trace": REASONING_TRACE_SCHEMA_VERSION,
        "review_record": REVIEW_RECORD_SCHEMA_VERSION,
        "perceptual_observation": OBSERVATION_RECORD_SCHEMA_VERSION,
        "perceptual_state": STATE_RECORD_SCHEMA_VERSION,
        "transition_record": TRANSITION_RECORD_SCHEMA_VERSION,
        "mutation_audit": MUTATION_AUDIT_SCHEMA_VERSION,
        "dataset_eligibility": DATASET_ELIGIBILITY_SCHEMA_VERSION,
    },
    "directories": [
        "taxonomy",
        "schemas",
        "fixtures",
    ],
    "files": [
        "taxonomy/observation_registry.json",
        "taxonomy/state_registry.json",
        "taxonomy/transition_registry.json",
        "taxonomy/scoring_registry.json",
        "taxonomy/uncertainty_policy.json",
        "schemas/observation_registry.schema.json",
        "schemas/state_registry.schema.json",
        "schemas/transition_registry.schema.json",
        "schemas/scoring_registry.schema.json",
        "schemas/uncertainty_policy.schema.json",
        "schemas/uncertainty_profile.schema.json",
        "schemas/reasoning_trace.schema.json",
        "schemas/perceptual_observation.schema.json",
        "schemas/perceptual_state.schema.json",
        "schemas/transition_record.schema.json",
        "schemas/mutation_audit.schema.json",
        "schemas/dataset_eligibility.schema.json",
        "fixtures/observation_record.example.json",
        "fixtures/state_record.example.json",
        "fixtures/transition_record.example.json",
        "fixtures/mutation_audit.example.json",
        "fixtures/reasoning_trace.example.json",
        "fixtures/uncertainty_profile.example.json",
        "fixtures/dataset_eligibility.example.json",
        "fixtures/review_record.example.json",
        "manifests/phase_zero_manifest.json",
    ],
}
