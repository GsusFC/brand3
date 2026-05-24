"""Perceptual state machine scaffolding for Visual Signature."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.visual_signature.perception.state_models import (
    MutationClassification,
    PerceptualState,
    PerceptualStateSnapshot,
    StateEvaluation,
    TransitionRecord,
)
from src.visual_signature.perception.transition_policy import (
    classify_mutation_result,
    classify_obstruction_state,
    evaluate_intervention_eligibility,
)


@dataclass
class PerceptualStateMachine:
    """Evidence-only perceptual state machine.

    The machine never overwrites the raw snapshot. It accumulates transitions
    and mutation audits so the raw state remains auditable throughout any
    attempted intervention.
    """

    raw_snapshot: PerceptualStateSnapshot
    current_state: PerceptualState = field(init=False)
    transitions: list[TransitionRecord] = field(default_factory=list)
    mutation_results: list[MutationClassification] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.current_state = self.raw_snapshot.state
        self.transitions.append(
            TransitionRecord(
                from_state=self.raw_snapshot.state,
                to_state=self.raw_snapshot.state,
                reason="raw_capture_created",
                confidence=self.raw_snapshot.confidence,
                evidence_refs=list(self.raw_snapshot.evidence_refs),
                notes=list(self.raw_snapshot.notes),
            )
        )

    @classmethod
    def from_raw_capture(
        cls,
        *,
        evidence_refs: list[str] | None = None,
        confidence: float = 1.0,
        notes: list[str] | None = None,
    ) -> "PerceptualStateMachine":
        return cls(
            raw_snapshot=PerceptualStateSnapshot(
                state="RAW_STATE",
                reason="raw_capture_created",
                confidence=confidence,
                evidence_refs=list(evidence_refs or []),
                notes=list(notes or []),
            ),
        )

    def classify_obstruction(
        self,
        obstruction: dict[str, Any] | None,
        *,
        evidence_refs: list[str] | None = None,
    ) -> StateEvaluation:
        decision = classify_obstruction_state(obstruction, evidence_refs=evidence_refs)
        self._record_transition(decision)
        return decision

    def evaluate_eligibility(
        self,
        obstruction: dict[str, Any] | None,
        *,
        affordance_labels: list[Any] | None = None,
        evidence_refs: list[str] | None = None,
    ) -> StateEvaluation:
        decision = evaluate_intervention_eligibility(
            obstruction,
            affordance_labels=affordance_labels,
            evidence_refs=evidence_refs,
        )
        self._record_transition(decision)
        return decision

    def classify_mutation(
        self,
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
        classification = classify_mutation_result(
            before_state=before_state,
            attempted=attempted,
            successful=successful,
            reversible=reversible,
            evidence_preserved=evidence_preserved,
            mutation_type=mutation_type,
            trigger=trigger,
            before_artifact_ref=before_artifact_ref,
            after_artifact_ref=after_artifact_ref,
            evidence_refs=evidence_refs,
            confidence=confidence,
            notes=notes,
            risk_level=risk_level,
            mutation_id=mutation_id,
        )
        self.current_state = classification.state
        self.transitions.append(classification.transition)
        self.mutation_results.append(classification)
        return classification

    def record_transition(
        self,
        *,
        to_state: PerceptualState,
        reason: str,
        confidence: float,
        evidence_refs: list[str] | None = None,
        mutation_ref: str | None = None,
        notes: list[str] | None = None,
    ) -> TransitionRecord:
        transition = TransitionRecord(
            from_state=self.current_state,
            to_state=to_state,
            reason=reason,  # type: ignore[arg-type]
            confidence=confidence,
            evidence_refs=list(evidence_refs or []),
            mutation_ref=mutation_ref,
            notes=list(notes or []),
        )
        self.current_state = to_state
        self.transitions.append(transition)
        return transition

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_snapshot": self.raw_snapshot.to_dict(),
            "current_state": self.current_state,
            "transitions": [transition.to_dict() for transition in self.transitions],
            "mutation_results": [result.to_dict() for result in self.mutation_results],
        }

    def _record_transition(self, decision: StateEvaluation) -> TransitionRecord:
        transition = TransitionRecord(
            from_state=self.current_state,
            to_state=decision.state,
            reason=decision.reason,
            confidence=decision.confidence,
            evidence_refs=list(decision.evidence_refs),
            notes=list(decision.notes),
        )
        self.current_state = decision.state
        self.transitions.append(transition)
        return transition
