"""Build Phase Zero records from Phase One source captures."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.phase_one.types import PhaseOneCaptureBundle, PhaseOneSourceCapture
from src.visual_signature.phase_zero.eligibility import evaluate_dataset_eligibility
from src.visual_signature.phase_zero.models import (
    DATASET_ELIGIBILITY_SCHEMA_VERSION,
    MUTATION_AUDIT_SCHEMA_VERSION,
    OBSERVATION_RECORD_SCHEMA_VERSION,
    PHASE_ZERO_TAXONOMY_VERSION,
    REASONING_TRACE_SCHEMA_VERSION,
    STATE_RECORD_SCHEMA_VERSION,
    TRANSITION_RECORD_SCHEMA_VERSION,
    UNCERTAINTY_PROFILE_SCHEMA_VERSION,
)


def build_phase_one_bundle(source: PhaseOneSourceCapture) -> PhaseOneCaptureBundle:
    observation_records = [
        _build_observation_record(source, "obstruction"),
        _build_observation_record(source, "density"),
    ]
    normalized_transitions = _normalize_transitions(source)
    transition_records = [_build_transition_record(source, transition) for transition in normalized_transitions]
    state_record = _build_state_record(source, transition_records)
    mutation_audit_record = _build_mutation_audit_record(source, transition_records)
    dataset_eligibility_record = _build_dataset_eligibility_record(source, state_record, mutation_audit_record)

    records: list[dict[str, Any]] = [*observation_records, state_record, *transition_records, dataset_eligibility_record]
    if mutation_audit_record:
        records.insert(3, mutation_audit_record)

    validation_errors = _validate_records(records)
    return PhaseOneCaptureBundle(
        source=source,
        observation_records=observation_records,
        state_record=state_record,
        transition_records=transition_records,
        mutation_audit_record=mutation_audit_record,
        dataset_eligibility_record=dataset_eligibility_record,
        validation_errors=validation_errors,
    )


def _build_observation_record(source: PhaseOneSourceCapture, key: str) -> dict[str, Any]:
    if key == "obstruction":
        obstruction = source.before_obstruction or {}
        obstruction_present = bool(obstruction.get("present"))
        value = str(obstruction.get("type") or ("none" if not obstruction_present else "unknown"))
        confidence = _float(obstruction.get("confidence"), default=1.0 if not obstruction_present else 0.0)
        reasons = [str(obstruction.get("severity") or ("no_obstruction_detected" if not obstruction_present else "obstruction_observed"))]
        trace_summary = f"Capture reports obstruction value {value}."
        statement = f"Viewport obstruction evidence is {value}."
    else:
        metrics = source.raw_viewport_metrics or {}
        value = str(metrics.get("viewport_visual_density") or "unknown")
        confidence = _float(metrics.get("composition_confidence"), default=0.8)
        reasons = [str(metrics.get("viewport_composition") or "density_observed")]
        trace_summary = f"Raw viewport density is {value}."
        statement = f"Viewport density evidence is {value}."

    return {
        "schema_version": OBSERVATION_RECORD_SCHEMA_VERSION,
        "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
        "record_type": "perceptual_observation",
        "record_id": f"obs_{_slug(source.brand_name)}_{key}",
        "created_at": _created_at(source),
        "capture_id": source.capture_id,
        "brand_name": source.brand_name,
        "website_url": source.website_url,
        "perception_layer": "functional",
        "observation_key": key,
        "observation_value": value,
        "confidence": confidence,
        "uncertainty": _uncertainty_profile(confidence, reasons=reasons, reviewer_required=source.perceptual_state in {"REVIEW_REQUIRED_STATE", "UNSAFE_MUTATION_BLOCKED"}),
        "evidence_refs": _evidence_refs(source),
        "reasoning_trace": {
            "schema_version": REASONING_TRACE_SCHEMA_VERSION,
            "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
            "record_type": "reasoning_trace",
            "trace_id": f"trace_{_slug(source.brand_name)}_{key}",
            "created_at": _created_at(source),
            "summary": trace_summary,
            "statements": [
                {
                    "statement": statement,
                    "confidence": confidence,
                    "evidence_refs": _evidence_refs(source),
                    "warnings": [],
                }
            ],
            "unsupported_inference_warnings": [],
            "review_required": source.perceptual_state in {"REVIEW_REQUIRED_STATE", "UNSAFE_MUTATION_BLOCKED"},
            "lineage_refs": _lineage_refs(source),
        },
        "lineage_refs": _lineage_refs(source),
    }


def _build_state_record(source: PhaseOneSourceCapture, transitions: list[dict[str, Any]]) -> dict[str, Any]:
    confidence = _state_confidence(source, transitions)
    review_required = source.perceptual_state in {"REVIEW_REQUIRED_STATE", "UNSAFE_MUTATION_BLOCKED"}
    return {
        "schema_version": STATE_RECORD_SCHEMA_VERSION,
        "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
        "record_type": "perceptual_state",
        "record_id": f"state_{_slug(source.brand_name)}",
        "created_at": _created_at(source),
        "capture_id": source.capture_id,
        "brand_name": source.brand_name,
        "website_url": source.website_url,
        "perceptual_state": source.perceptual_state or "RAW_STATE",
        "confidence": confidence,
        "uncertainty": _uncertainty_profile(
            confidence,
            reasons=[str((source.before_obstruction or {}).get("severity") or "state_observed")],
            reviewer_required=review_required,
        ),
        "transitions": transitions,
        "reasoning_trace": {
            "schema_version": REASONING_TRACE_SCHEMA_VERSION,
            "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
            "record_type": "reasoning_trace",
            "trace_id": f"trace_{_slug(source.brand_name)}_state",
            "created_at": _created_at(source),
            "summary": f"Capture state recorded as {source.perceptual_state or 'RAW_STATE'}.",
            "statements": [
                {
                    "statement": f"Perceptual state is {source.perceptual_state or 'RAW_STATE'}.",
                    "confidence": confidence,
                    "evidence_refs": _evidence_refs(source),
                    "warnings": [],
                }
            ],
            "unsupported_inference_warnings": [],
            "review_required": review_required,
            "lineage_refs": _lineage_refs(source),
        },
        "lineage_refs": _lineage_refs(source),
    }


def _build_transition_record(source: PhaseOneSourceCapture, transition: dict[str, Any]) -> dict[str, Any]:
    source_reason = str(transition.get("reason") or "raw_capture_created")
    reason = _normalize_transition_reason(source_reason)
    confidence = _float(transition.get("confidence"), default=0.0)
    notes = [str(item) for item in transition.get("notes", []) if item]
    if source_reason != reason:
        notes.append(f"source_transition_reason:{source_reason}")
    return {
        "schema_version": TRANSITION_RECORD_SCHEMA_VERSION,
        "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
        "record_type": "transition_record",
        "transition_id": f"transition_{_slug(source.brand_name)}_{reason}",
        "created_at": _created_at(source),
        "capture_id": source.capture_id,
        "from_state": str(transition.get("from_state") or "RAW_STATE"),
        "to_state": str(transition.get("to_state") or "RAW_STATE"),
        "reason": reason,
        "confidence": confidence,
        "evidence_refs": _evidence_refs(source),
        "lineage_refs": _lineage_refs(source),
        "mutation_ref": _mutation_ref(source, transition),
        "notes": notes,
    }


def _build_mutation_audit_record(source: PhaseOneSourceCapture, transitions: list[dict[str, Any]]) -> dict[str, Any] | None:
    mutation = source.mutation_audit
    if not isinstance(mutation, dict):
        return None
    return {
        "schema_version": MUTATION_AUDIT_SCHEMA_VERSION,
        "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
        "record_type": "mutation_audit",
        "mutation_id": str(mutation.get("mutation_id") or f"mutation_{_slug(source.brand_name)}"),
        "created_at": _created_at(source),
        "capture_id": source.capture_id,
        "brand_name": source.brand_name,
        "website_url": source.website_url,
        "mutation_type": str(mutation.get("mutation_type") or "unknown"),
        "before_state": str(mutation.get("before_state") or source.perceptual_state or "REVIEW_REQUIRED_STATE"),
        "after_state": str(mutation.get("after_state") or source.perceptual_state or "REVIEW_REQUIRED_STATE"),
        "attempted": bool(mutation.get("attempted")),
        "successful": bool(mutation.get("successful")),
        "reversible": bool(mutation.get("reversible", True)),
        "risk_level": str(mutation.get("risk_level") or "low"),
        "trigger": str(mutation.get("trigger") or "close"),
        "evidence_preserved": bool(mutation.get("evidence_preserved", True)),
        "before_artifact_ref": str(mutation.get("before_artifact_ref") or source.raw_screenshot_path or ""),
        "after_artifact_ref": str(mutation.get("after_artifact_ref") or source.clean_attempt_screenshot_path or ""),
        "lineage_refs": _lineage_refs(source, transition_keys=[t.get("reason") for t in transitions]),
        "integrity_notes": [str(item) for item in mutation.get("integrity_notes", []) if item],
    }


def _build_dataset_eligibility_record(
    source: PhaseOneSourceCapture,
    state_record: dict[str, Any],
    mutation_audit_record: dict[str, Any] | None,
) -> dict[str, Any]:
    raw_present = bool(source.raw_screenshot_path)
    mutation_lineage_preserved = _mutation_lineage_ok(mutation_audit_record)
    review_required = state_record["uncertainty"]["reviewer_required"]
    review_completed = False
    observed_confidence = _float(state_record.get("confidence"), default=0.0)
    candidate = {
        "schema_version": "phase-zero-dataset-eligibility-1",
        "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
        "record_type": "dataset_eligibility",
        "record_id": f"elig_{_slug(source.brand_name)}",
        "created_at": _created_at(source),
        "capture_id": source.capture_id,
        "brand_name": source.brand_name,
        "website_url": source.website_url,
        "eligible": False,
        "reasons": [],
        "blocked_reasons": [],
        "raw_evidence_preserved": raw_present,
        "mutation_lineage_preserved": mutation_lineage_preserved,
        "schema_valid": True,
        "review_required": review_required,
        "review_completed": review_completed,
        "uncertainty_below_threshold": observed_confidence >= 0.8,
        "confidence_threshold": 0.8,
        "observed_confidence": observed_confidence,
        "unsupported_inference_found": False,
        "evidence_refs": _evidence_refs(source),
        "lineage_refs": _lineage_refs(source),
    }
    if mutation_audit_record:
        candidate["lineage_refs"].append(f"mutation:{mutation_audit_record['mutation_id']}")
    return evaluate_dataset_eligibility(candidate).model_dump(mode="json")


def _validate_records(records: list[dict[str, Any]]) -> list[str]:
    from src.visual_signature.phase_zero.validation import validate_record_schema

    errors: list[str] = []
    for record in records:
        errors.extend(validate_record_schema(record))
    return errors


def _evidence_refs(source: PhaseOneSourceCapture) -> list[str]:
    refs: list[str] = []
    if source.raw_screenshot_path:
        refs.append(source.raw_screenshot_path)
    return refs


def _lineage_refs(source: PhaseOneSourceCapture, transition_keys: list[str] | None = None) -> list[str]:
    refs = [f"capture_manifest:{source.source_manifest_path}", f"capture:{source.capture_id}"]
    if source.source_dismissal_audit_path:
        refs.append(f"dismissal_audit:{source.source_dismissal_audit_path}")
    if source.clean_attempt_screenshot_path:
        refs.append(f"clean_attempt:{source.clean_attempt_screenshot_path}")
    if transition_keys:
        for key in transition_keys:
            if key:
                refs.append(f"transition:{key}")
    if source.mutation_audit and source.mutation_audit.get("mutation_id"):
        refs.append(f"mutation:{source.mutation_audit['mutation_id']}")
    return refs


def _mutation_ref(source: PhaseOneSourceCapture, transition: dict[str, Any]) -> str | None:
    mutation = source.mutation_audit or {}
    mutation_id = mutation.get("mutation_id")
    if mutation_id and str(transition.get("reason") or "").startswith("safe_mutation"):
        return str(mutation_id)
    return None


def _state_confidence(source: PhaseOneSourceCapture, transitions: list[dict[str, Any]]) -> float:
    obstruction = source.before_obstruction or {}
    obstruction_confidence = _float(obstruction.get("confidence"), default=0.0)
    if obstruction_confidence:
        return obstruction_confidence
    metrics = source.raw_viewport_metrics or {}
    metric_confidence = _float(metrics.get("composition_confidence"), default=0.0)
    if metric_confidence:
        return metric_confidence
    if source.perceptual_state in {"RAW_STATE", ""}:
        if any(str(item.get("reason")) == "no_obstruction_detected" for item in transitions):
            return 1.0
        return 1.0
    return 0.8


def _normalize_transitions(source: PhaseOneSourceCapture) -> list[dict[str, Any]]:
    transitions = [item for item in source.perceptual_transitions if isinstance(item, dict)]
    if transitions:
        return transitions

    obstruction = source.before_obstruction or {}
    obstruction_present = bool(obstruction.get("present"))
    confidence = _float(obstruction.get("confidence"), default=0.0)
    evidence_refs = _evidence_refs(source)

    normalized = [
        {
            "from_state": "RAW_STATE",
            "to_state": "RAW_STATE",
            "reason": "raw_capture_created",
            "confidence": 1.0,
            "evidence_refs": evidence_refs,
            "lineage_refs": _lineage_refs(source),
            "mutation_ref": None,
            "notes": ["raw_viewport_preserved_as_primary_evidence"],
        }
    ]

    if not obstruction_present:
        normalized.append(
            {
                "from_state": "RAW_STATE",
                "to_state": "RAW_STATE",
                "reason": "no_obstruction_detected",
                "confidence": confidence,
                "evidence_refs": evidence_refs,
                "lineage_refs": _lineage_refs(source),
                "mutation_ref": None,
                "notes": ["no_obstruction_detected"],
            }
        )
        return normalized

    perceived_state = source.perceptual_state or "OBSTRUCTED_STATE"
    if perceived_state == "UNSAFE_MUTATION_BLOCKED":
        reason = "protected_environment_detected"
        to_state = "UNSAFE_MUTATION_BLOCKED"
        notes = ["protected_environment_detected"]
    elif perceived_state == "REVIEW_REQUIRED_STATE":
        reason = "no_safe_affordance_detected"
        to_state = "REVIEW_REQUIRED_STATE"
        notes = ["no_safe_affordance_detected"]
    elif perceived_state == "ELIGIBLE_FOR_SAFE_INTERVENTION":
        reason = "exact_safe_affordance_detected"
        to_state = "ELIGIBLE_FOR_SAFE_INTERVENTION"
        notes = ["exact_safe_affordance_detected"]
    else:
        reason = "viewport_obstruction_detected"
        to_state = "OBSTRUCTED_STATE"
        notes = ["viewport_obstruction_detected"]
    normalized.append(
        {
            "from_state": "RAW_STATE",
            "to_state": to_state,
            "reason": reason,
            "confidence": confidence or 1.0,
            "evidence_refs": evidence_refs,
            "lineage_refs": _lineage_refs(source),
            "mutation_ref": None,
            "notes": notes,
        }
    )
    return normalized


def _normalize_transition_reason(reason: str) -> str:
    if reason == "low_confidence_obstruction":
        return "human_review_required"
    return reason


def _mutation_lineage_ok(mutation_audit_record: dict[str, Any] | None) -> bool:
    if not mutation_audit_record:
        return True
    if not mutation_audit_record.get("attempted"):
        return True
    before = str(mutation_audit_record.get("before_artifact_ref") or "")
    after = str(mutation_audit_record.get("after_artifact_ref") or "")
    if not before:
        return False
    if not mutation_audit_record.get("successful") and not after:
        return False
    return True


def _uncertainty_profile(
    confidence: float,
    *,
    reasons: list[str] | None = None,
    reviewer_required: bool = False,
) -> dict[str, Any]:
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
        "known_unknowns": [],
        "uncertainty_reasons": reasons or [],
        "reviewer_required": reviewer_required,
        "unsupported_inference": False,
    }


def _created_at(source: PhaseOneSourceCapture) -> str:
    return source.captured_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    value = value.lower().strip()
    out = []
    for char in value:
        if char.isalnum():
            out.append(char)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-") or "capture"


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
