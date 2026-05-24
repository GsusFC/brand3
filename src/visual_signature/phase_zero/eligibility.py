"""Executable dataset eligibility rules for Phase Zero artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.visual_signature.phase_zero.validation import validate_record_schema
from src.visual_signature.phase_zero.models import (
    DATASET_ELIGIBILITY_SCHEMA_VERSION,
    DatasetEligibilityRecord,
    PHASE_ZERO_TAXONOMY_VERSION,
    MutationAuditRecord,
    UNCERTAINTY_PROFILE_SCHEMA_VERSION,
    UncertaintyProfile,
)


def evaluate_dataset_eligibility(record: dict[str, Any], *, confidence_threshold: float = 0.8) -> DatasetEligibilityRecord:
    schema_valid = _schema_valid(record)
    raw_evidence_preserved = _raw_evidence_preserved(record)
    mutation_lineage_preserved = _mutation_lineage_preserved(record)
    review_required = _review_required(record)
    review_completed = _review_completed(record)
    unsupported_inference_found = _unsupported_inference_found(record)
    observed_confidence = _observed_confidence(record)
    uncertainty_below_threshold = observed_confidence >= confidence_threshold

    reasons: list[str] = []
    blocked_reasons: list[str] = []

    if not schema_valid:
        blocked_reasons.append("schema_invalid")
    else:
        reasons.append("schema valid")
    if not raw_evidence_preserved:
        blocked_reasons.append("raw_evidence_missing")
    else:
        reasons.append("raw evidence preserved")
    if not mutation_lineage_preserved:
        blocked_reasons.append("mutation_lineage_missing")
    else:
        reasons.append("mutation lineage preserved")
    if unsupported_inference_found:
        blocked_reasons.append("unsupported_inference_present")
    else:
        reasons.append("no unsupported inference")

    if review_required and not review_completed:
        blocked_reasons.append("review_required_not_completed")
    elif review_completed:
        reasons.append("review completed")

    if not uncertainty_below_threshold:
        if review_required and review_completed:
            reasons.append("uncertainty explicitly labeled")
        else:
            blocked_reasons.append("confidence_below_threshold")

    eligible = not blocked_reasons

    return DatasetEligibilityRecord(
        schema_version=DATASET_ELIGIBILITY_SCHEMA_VERSION,
        taxonomy_version=PHASE_ZERO_TAXONOMY_VERSION,
        record_type="dataset_eligibility",
        record_id=str(record.get("record_id") or record.get("capture_id") or "eligibility_unknown"),
        created_at=_created_at(record),
        capture_id=str(record.get("capture_id") or "capture_unknown"),
        brand_name=str(record.get("brand_name") or "unknown"),
        website_url=str(record.get("website_url") or ""),
        eligible=eligible,
        reasons=reasons,
        blocked_reasons=blocked_reasons,
        raw_evidence_preserved=raw_evidence_preserved,
        mutation_lineage_preserved=mutation_lineage_preserved,
        schema_valid=schema_valid,
        review_required=review_required,
        review_completed=review_completed,
        uncertainty_below_threshold=uncertainty_below_threshold,
        confidence_threshold=confidence_threshold,
        observed_confidence=observed_confidence,
        unsupported_inference_found=unsupported_inference_found,
        evidence_refs=_evidence_refs(record),
        lineage_refs=_lineage_refs(record),
    )


def _schema_valid(record: dict[str, Any]) -> bool:
    return not validate_record_schema(_schema_validation_candidate(record))


def _raw_evidence_preserved(record: dict[str, Any]) -> bool:
    if _evidence_refs(record):
        return True
    for key in ("raw_screenshot_path", "raw_artifact_ref", "raw_viewport_path"):
        if record.get(key):
            return True
    return False


def _mutation_lineage_preserved(record: dict[str, Any]) -> bool:
    mutation = record.get("mutation_audit")
    if isinstance(mutation, dict):
        try:
            mutation_model = MutationAuditRecord.model_validate(mutation)
        except Exception:
            return False
        if mutation_model.attempted:
            return bool(mutation_model.before_artifact_ref) and (
                mutation_model.successful is False or bool(mutation_model.after_artifact_ref)
            )
        return True

    explicit = record.get("mutation_lineage_preserved")
    if isinstance(explicit, bool):
        return explicit
    return True


def _review_required(record: dict[str, Any]) -> bool:
    uncertainty = _uncertainty(record)
    return bool(record.get("review_required") or uncertainty.reviewer_required)


def _review_completed(record: dict[str, Any]) -> bool:
    return bool(record.get("review_completed") or record.get("human_review_completed"))


def _unsupported_inference_found(record: dict[str, Any]) -> bool:
    uncertainty = _uncertainty(record)
    if uncertainty.unsupported_inference:
        return True
    trace = record.get("reasoning_trace")
    if isinstance(trace, dict):
        warnings = trace.get("unsupported_inference_warnings")
        if isinstance(warnings, list) and warnings:
            return True
        for statement in trace.get("statements", []):
            if isinstance(statement, dict) and statement.get("warnings"):
                for warning in statement["warnings"]:
                    if "unsupported" in str(warning).lower():
                        return True
    return False


def _observed_confidence(record: dict[str, Any]) -> float:
    uncertainty = _uncertainty(record)
    if isinstance(uncertainty.confidence, (int, float)):
        return float(uncertainty.confidence)
    confidence = record.get("confidence")
    try:
        return float(confidence)
    except (TypeError, ValueError):
        return 0.0


def _uncertainty(record: dict[str, Any]) -> UncertaintyProfile:
    value = record.get("uncertainty")
    if isinstance(value, dict):
        return UncertaintyProfile.model_validate(value)
    return UncertaintyProfile(
        schema_version=UNCERTAINTY_PROFILE_SCHEMA_VERSION,
        taxonomy_version=PHASE_ZERO_TAXONOMY_VERSION,
        record_type="uncertainty_profile",
        confidence=0.0,
        confidence_level="low",
        known_unknowns=[],
        uncertainty_reasons=[],
        reviewer_required=False,
        unsupported_inference=False,
    )


def _evidence_refs(record: dict[str, Any]) -> list[str]:
    refs = record.get("evidence_refs")
    return [str(item) for item in refs] if isinstance(refs, list) else []


def _lineage_refs(record: dict[str, Any]) -> list[str]:
    refs = record.get("lineage_refs")
    return [str(item) for item in refs] if isinstance(refs, list) else []


def _schema_validation_candidate(record: dict[str, Any]) -> dict[str, Any]:
    if "mutation_audit" not in record:
        return record
    candidate = dict(record)
    candidate.pop("mutation_audit", None)
    return candidate


def _created_at(record: dict[str, Any]) -> datetime:
    value = record.get("created_at")
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)
