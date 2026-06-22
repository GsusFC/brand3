"""Dataclasses for the Visual Signature perceptual state machine."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


PerceptualState = Literal[
    "RAW_STATE",
    "OBSTRUCTED_STATE",
    "ELIGIBLE_FOR_SAFE_INTERVENTION",
    "MINIMALLY_MUTATED_STATE",
    "UNSAFE_MUTATION_BLOCKED",
    "REVIEW_REQUIRED_STATE",
]

TransitionReason = Literal[
    "raw_capture_created",
    "viewport_obstruction_detected",
    "no_obstruction_detected",
    "exact_safe_affordance_detected",
    "no_safe_affordance_detected",
    "protected_environment_detected",
    "ambiguous_affordance_detected",
    "low_confidence_obstruction",
    "safe_mutation_attempted",
    "safe_mutation_succeeded",
    "safe_mutation_failed",
    "human_review_required",
]

MutationRiskLevel = Literal["low", "medium", "high", "blocking"]


@dataclass
class PerceptualStateSnapshot:
    state: PerceptualState
    reason: TransitionReason
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TransitionRecord:
    from_state: PerceptualState
    to_state: PerceptualState
    reason: TransitionReason
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)
    mutation_ref: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MutationAuditRecord:
    mutation_id: str
    mutation_type: str
    before_state: PerceptualState
    after_state: PerceptualState
    attempted: bool
    successful: bool
    reversible: bool
    risk_level: MutationRiskLevel
    trigger: str
    evidence_preserved: bool
    before_artifact_ref: str | None = None
    after_artifact_ref: str | None = None
    integrity_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StateEvaluation:
    state: PerceptualState
    reason: TransitionReason
    confidence: float
    eligible_for_safe_intervention: bool = False
    evidence_refs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    safe_affordances: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MutationClassification:
    state: PerceptualState
    reason: TransitionReason
    confidence: float
    transition: TransitionRecord
    mutation_audit: MutationAuditRecord
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["transition"] = self.transition.to_dict()
        payload["mutation_audit"] = self.mutation_audit.to_dict()
        return payload


def build_mutation_audit_record(
    *,
    mutation_type: str,
    before_state: PerceptualState,
    after_state: PerceptualState,
    attempted: bool,
    successful: bool,
    reversible: bool,
    risk_level: MutationRiskLevel,
    trigger: str,
    evidence_preserved: bool,
    before_artifact_ref: str | None = None,
    after_artifact_ref: str | None = None,
    integrity_notes: list[str] | None = None,
    mutation_id: str | None = None,
) -> MutationAuditRecord:
    return MutationAuditRecord(
        mutation_id=mutation_id or uuid.uuid4().hex,
        mutation_type=mutation_type,
        before_state=before_state,
        after_state=after_state,
        attempted=attempted,
        successful=successful,
        reversible=reversible,
        risk_level=risk_level,
        trigger=trigger,
        evidence_preserved=evidence_preserved,
        before_artifact_ref=before_artifact_ref,
        after_artifact_ref=after_artifact_ref,
        integrity_notes=integrity_notes or [],
    )
