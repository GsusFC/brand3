"""Mutation audit helpers for Visual Signature perception."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from src.visual_signature.perception.state_models import MutationRiskLevel, PerceptualState


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
