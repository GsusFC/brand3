"""Transition policy helpers for the Visual Signature perceptual state machine."""

from __future__ import annotations

from typing import Any

from src.visual_signature.perception.mutation_audit import build_mutation_audit_record
from src.visual_signature.perception.state_models import (
    MutationClassification,
    PerceptualState,
    StateEvaluation,
    TransitionRecord,
)


PROTECTED_OBSTRUCTION_TYPES = {
    "login_wall",
    "paywall",
    "geo_gate",
    "protected_environment",
    "protected_content",
}
SAFE_INTERVENTION_TYPES = {"cookie_banner", "cookie_modal", "newsletter_modal", "promo_modal"}
AMBIGUOUS_AFFORDANCES = {
    "manage choices",
    "privacy settings",
    "preferences",
    "settings",
    "learn more",
    "subscribe",
    "sign up",
    "signup",
    "join",
}
COOKIE_SAFE_AFFORDANCES = {
    "accept all",
    "accept",
    "allow all",
    "agree",
    "i agree",
    "ok",
    "got it",
    "reject all",
    "decline",
    "continue",
    "close",
    "x",
    "dismiss",
}
SECONDARY_SAFE_AFFORDANCES = {"close", "x", "dismiss"}


def classify_obstruction_state(
    obstruction: dict[str, Any] | None,
    *,
    evidence_refs: list[str] | None = None,
) -> StateEvaluation:
    """Classify the base perceptual state from obstruction evidence alone."""
    data = obstruction if isinstance(obstruction, dict) else {}
    present = bool(data.get("present"))
    obstruction_type = _obstruction_type(data.get("type"))
    confidence = _float_or_zero(data.get("confidence"))
    first_impression_valid = bool(data.get("first_impression_valid", True))
    notes: list[str] = []

    if not present:
        return StateEvaluation(
            state="RAW_STATE",
            reason="no_obstruction_detected",
            confidence=1.0 if data else 0.0,
            evidence_refs=_refs(evidence_refs),
            notes=notes,
        )

    if obstruction_type in PROTECTED_OBSTRUCTION_TYPES:
        notes.append("protected_environment_requires_no_mutation")
        return StateEvaluation(
            state="UNSAFE_MUTATION_BLOCKED",
            reason="protected_environment_detected",
            confidence=_policy_confidence(confidence, floor=0.85),
            evidence_refs=_refs(evidence_refs),
            notes=notes,
        )

    if obstruction_type == "unknown_overlay":
        notes.append("overlay_type_ambiguous")
        return StateEvaluation(
            state="REVIEW_REQUIRED_STATE",
            reason="low_confidence_obstruction" if confidence < 0.65 else "human_review_required",
            confidence=_policy_confidence(confidence, floor=0.55),
            evidence_refs=_refs(evidence_refs),
            notes=notes,
        )

    if confidence < 0.35 or first_impression_valid is False:
        notes.append("obstruction_present_but_confidence_or_first_impression_is_low")
        return StateEvaluation(
            state="REVIEW_REQUIRED_STATE",
            reason="low_confidence_obstruction",
            confidence=_policy_confidence(confidence, floor=0.35),
            evidence_refs=_refs(evidence_refs),
            notes=notes,
        )

    return StateEvaluation(
        state="OBSTRUCTED_STATE",
        reason="viewport_obstruction_detected",
        confidence=_policy_confidence(confidence, floor=0.65),
        evidence_refs=_refs(evidence_refs),
        notes=notes,
    )


def evaluate_intervention_eligibility(
    obstruction: dict[str, Any] | None,
    *,
    affordance_labels: list[Any] | None = None,
    evidence_refs: list[str] | None = None,
) -> StateEvaluation:
    """Decide whether a minimal safe intervention is allowed."""
    base = classify_obstruction_state(obstruction, evidence_refs=evidence_refs)
    data = obstruction if isinstance(obstruction, dict) else {}
    obstruction_type = _obstruction_type(data.get("type"))
    safe_affordances = _normalized_affordances(affordance_labels)
    exact_safe_affordance = _exact_safe_affordance(obstruction_type, safe_affordances)
    ambiguous_affordance = _has_ambiguous_affordance(safe_affordances)

    if base.state == "RAW_STATE":
        return base
    if base.state == "UNSAFE_MUTATION_BLOCKED":
        return base
    if base.state == "REVIEW_REQUIRED_STATE" and obstruction_type == "unknown_overlay":
        return base

    notes = list(base.notes)
    if exact_safe_affordance:
        notes.append("exact_safe_affordance_detected")
        return StateEvaluation(
            state="ELIGIBLE_FOR_SAFE_INTERVENTION",
            reason="exact_safe_affordance_detected",
            confidence=max(base.confidence, 0.75),
            eligible_for_safe_intervention=True,
            evidence_refs=_refs(evidence_refs),
            notes=notes,
            safe_affordances=[exact_safe_affordance],
        )

    if ambiguous_affordance:
        notes.append("ambiguous_affordance_detected")
        return StateEvaluation(
            state="REVIEW_REQUIRED_STATE",
            reason="ambiguous_affordance_detected",
            confidence=max(base.confidence, 0.5),
            evidence_refs=_refs(evidence_refs),
            notes=notes,
            safe_affordances=safe_affordances,
        )

    if obstruction_type in SAFE_INTERVENTION_TYPES:
        notes.append("no_safe_affordance_detected")
        return StateEvaluation(
            state="OBSTRUCTED_STATE",
            reason="no_safe_affordance_detected",
            confidence=base.confidence,
            evidence_refs=_refs(evidence_refs),
            notes=notes,
            safe_affordances=safe_affordances,
        )

    return StateEvaluation(
        state=base.state,
        reason=base.reason,
        confidence=base.confidence,
        eligible_for_safe_intervention=False,
        evidence_refs=_refs(evidence_refs),
        notes=notes,
        safe_affordances=safe_affordances,
    )


def classify_mutation_result(
    *,
    before_state: PerceptualState,
    attempted: bool,
    successful: bool,
    reversible: bool = True,
    evidence_preserved: bool = True,
    mutation_type: str = "safe_mutation",
    trigger: str = "safe_mutation_attempted",
    before_artifact_ref: str | None = None,
    after_artifact_ref: str | None = None,
    evidence_refs: list[str] | None = None,
    confidence: float = 0.9,
    notes: list[str] | None = None,
    risk_level: str = "low",
    mutation_id: str | None = None,
) -> MutationClassification:
    """Classify the result of a safe mutation attempt while preserving raw evidence."""
    notes_list = list(notes or [])
    if not attempted:
        after_state: PerceptualState = before_state
        reason: Any = "human_review_required"
        notes_list.append("mutation_not_attempted")
    elif successful:
        after_state = "MINIMALLY_MUTATED_STATE"
        reason = "safe_mutation_succeeded"
        notes_list.append("safe_mutation_success_preserves_raw_state")
    else:
        after_state = "REVIEW_REQUIRED_STATE"
        reason = "safe_mutation_failed"
        notes_list.append("safe_mutation_failed_without_overwriting_raw_state")

    transition = TransitionRecord(
        from_state=before_state,
        to_state=after_state,
        reason=reason,
        confidence=_policy_confidence(confidence, floor=0.5 if attempted else 0.35),
        evidence_refs=_refs(evidence_refs),
        mutation_ref=mutation_id,
        notes=notes_list,
    )
    audit = build_mutation_audit_record(
        mutation_id=mutation_id,
        mutation_type=mutation_type,
        before_state=before_state,
        after_state=after_state,
        attempted=attempted,
        successful=successful,
        reversible=reversible,
        risk_level=_risk_level(risk_level),
        trigger=trigger,
        evidence_preserved=evidence_preserved,
        before_artifact_ref=before_artifact_ref,
        after_artifact_ref=after_artifact_ref,
        integrity_notes=_integrity_notes(attempted, successful, evidence_preserved, notes_list),
    )
    return MutationClassification(
        state=after_state,
        reason=reason,
        confidence=transition.confidence,
        transition=transition,
        mutation_audit=audit,
        notes=notes_list,
    )


def _exact_safe_affordance(obstruction_type: str, affordances: list[str]) -> str | None:
    if not affordances:
        return None
    if obstruction_type in {"newsletter_modal", "promo_modal"}:
        safe_set = SECONDARY_SAFE_AFFORDANCES
    else:
        safe_set = COOKIE_SAFE_AFFORDANCES
    for affordance in affordances:
        if affordance in safe_set:
            return affordance
    return None


def _has_ambiguous_affordance(affordances: list[str]) -> bool:
    return any(label in AMBIGUOUS_AFFORDANCES for label in affordances)


def _normalized_affordances(values: list[Any] | None) -> list[str]:
    labels: list[str] = []
    for value in values or []:
        label = _affordance_label(value)
        if label:
            labels.append(label)
    return list(dict.fromkeys(labels))


def _affordance_label(value: Any) -> str:
    if isinstance(value, str):
        return _normalize_label(value)
    if isinstance(value, dict):
        for key in ("label", "text", "aria_label", "aria-label", "title", "name"):
            label = value.get(key)
            if label:
                return _normalize_label(str(label))
    return ""


def _obstruction_type(value: Any) -> str:
    if not isinstance(value, str):
        return "unknown_overlay"
    normalized = _normalize_label(value).replace(" ", "_")
    if normalized in {"cookie_banner", "cookie_modal", "newsletter_modal", "login_wall", "promo_modal"}:
        return normalized
    if normalized in {"paywall", "geo_gate", "protected_environment", "protected_content"}:
        return normalized
    if normalized in {"none", ""}:
        return "none"
    return "unknown_overlay"


def _normalize_label(value: str) -> str:
    normalized = " ".join((value or "").lower().replace("-", " ").replace("/", " ").split())
    normalized = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in normalized)
    return " ".join(normalized.split())


def _policy_confidence(value: float, *, floor: float) -> float:
    return round(max(0.0, min(1.0, max(value, floor))), 3)


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _risk_level(value: str) -> str:
    if value in {"low", "medium", "high", "blocking"}:
        return value
    return "low"


def _refs(values: list[str] | None) -> list[str]:
    return [str(value) for value in values or [] if str(value)]


def _integrity_notes(
    attempted: bool,
    successful: bool,
    evidence_preserved: bool,
    notes: list[str],
) -> list[str]:
    result = list(notes)
    if not evidence_preserved:
        result.append("evidence_preservation_failed")
    elif attempted and successful:
        result.append("raw_state_preserved_as_primary_evidence")
    elif attempted and not successful:
        result.append("raw_state_preserved_after_failed_attempt")
    else:
        result.append("no_mutation_attempted")
    return list(dict.fromkeys(result))
