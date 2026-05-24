"""Reusable Phase Zero validation helpers."""

from __future__ import annotations

from typing import Any

from src.visual_signature.phase_zero.catalog import (
    OBSERVATION_REGISTRY,
    SCORING_REGISTRY,
    STATE_REGISTRY,
    TRANSITION_REGISTRY,
)
from src.visual_signature.phase_zero.models import (
    DatasetEligibilityRecord,
    MutationAuditRecord,
    PerceptualObservationRecord,
    PerceptualStateRecord,
    ReasoningTrace,
    ReviewRecord,
    ScoringRegistry,
    StateRegistry,
    TransitionRecord,
    TransitionRegistry,
    UncertaintyPolicy,
    UncertaintyProfile,
)


REGISTRY_EXPECTATIONS = {
    "observation_registry": {item["key"] for item in OBSERVATION_REGISTRY["items"]},
    "state_registry": {item["key"] for item in STATE_REGISTRY["items"]},
    "transition_registry": {item["key"] for item in TRANSITION_REGISTRY["items"]},
    "scoring_registry": {item["key"] for item in SCORING_REGISTRY["items"]},
}


def validate_registry_document(payload: dict[str, Any], *, registry_type: str) -> list[str]:
    errors: list[str] = []
    if registry_type not in REGISTRY_EXPECTATIONS:
        return [f"unknown_registry_type:{registry_type}"]
    if payload.get("registry_type") != registry_type:
        errors.append("registry_type_invalid")
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        errors.append("schema_version_missing")
    taxonomy_version = payload.get("taxonomy_version")
    if not isinstance(taxonomy_version, str) or not taxonomy_version:
        errors.append("taxonomy_version_missing")
    items = payload.get("items")
    if not isinstance(items, list):
        errors.append("items_must_be_list")
        return errors

    allowed = REGISTRY_EXPECTATIONS[registry_type]
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"item_{index}:not_an_object")
            continue
        key = str(item.get("key") or "")
        if not key:
            errors.append(f"item_{index}:key_missing")
            continue
        if key not in allowed:
            errors.append(f"item_{index}:unknown_key:{key}")
    return errors


def validate_record_schema(record: dict[str, Any]) -> list[str]:
    record_type = str(record.get("record_type") or "")
    try:
        if record_type == "perceptual_observation":
            PerceptualObservationRecord.model_validate(record)
            _validate_observation_key(record)
        elif record_type == "perceptual_state":
            PerceptualStateRecord.model_validate(record)
            _validate_state_key(record)
        elif record_type == "transition_record":
            TransitionRecord.model_validate(record)
            _validate_transition_reason(record)
        elif record_type == "mutation_audit":
            MutationAuditRecord.model_validate(record)
            _validate_mutation_states(record)
        elif record_type == "review_record":
            ReviewRecord.model_validate(record)
        elif record_type == "reasoning_trace":
            ReasoningTrace.model_validate(record)
        elif record_type == "dataset_eligibility":
            DatasetEligibilityRecord.model_validate(record)
        elif record_type == "uncertainty_profile":
            UncertaintyProfile.model_validate(record)
        elif record_type == "uncertainty_policy":
            UncertaintyPolicy.model_validate(record)
        elif record_type == "scoring_registry":
            ScoringRegistry.model_validate(record)
        elif record_type == "state_registry":
            StateRegistry.model_validate(record)
        elif record_type == "transition_registry":
            TransitionRegistry.model_validate(record)
        else:
            return [f"unknown_record_type:{record_type}"]
    except Exception as exc:
        return [str(exc)]
    return []


def _validate_observation_key(record: dict[str, Any]) -> None:
    allowed = REGISTRY_EXPECTATIONS["observation_registry"]
    key = str(record.get("observation_key") or "")
    if key not in allowed:
        raise ValueError(f"unknown_observation_key:{key}")


def _validate_state_key(record: dict[str, Any]) -> None:
    allowed = REGISTRY_EXPECTATIONS["state_registry"]
    state = str(record.get("perceptual_state") or "")
    if state not in allowed:
        raise ValueError(f"unknown_state_key:{state}")
    for transition in record.get("transitions", []):
        if not isinstance(transition, dict):
            continue
        from_state = str(transition.get("from_state") or "")
        to_state = str(transition.get("to_state") or "")
        if from_state not in allowed:
            raise ValueError(f"unknown_transition_from_state:{from_state}")
        if to_state not in allowed:
            raise ValueError(f"unknown_transition_to_state:{to_state}")


def _validate_transition_reason(record: dict[str, Any]) -> None:
    allowed = REGISTRY_EXPECTATIONS["transition_registry"]
    reason = str(record.get("reason") or "")
    if reason not in allowed:
        raise ValueError(f"unknown_transition_reason:{reason}")


def _validate_mutation_states(record: dict[str, Any]) -> None:
    allowed = REGISTRY_EXPECTATIONS["state_registry"]
    before_state = str(record.get("before_state") or "")
    after_state = str(record.get("after_state") or "")
    if before_state not in allowed:
        raise ValueError(f"unknown_before_state:{before_state}")
    if after_state not in allowed:
        raise ValueError(f"unknown_after_state:{after_state}")
