"""Pydantic models for the Visual Signature capability registry."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.visual_signature.calibration.readiness_models import ReadinessScope


CAPABILITY_REGISTRY_SCHEMA_VERSION = "visual-signature-capability-registry-1"

CapabilityMaturityState = Literal["experimental", "constrained", "governed", "production_candidate"]
CapabilityEvidenceStatus = Literal["validated", "evidence_only"]
MutationRisk = Literal["none", "low", "moderate", "high"]
GovernanceScope = Literal["visual_signature"]

NonEmptyString = Annotated[str, Field(min_length=1)]


class CapabilityRegistryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapabilityEntry(CapabilityRegistryModel):
    capability_id: NonEmptyString
    description: NonEmptyString
    layer: NonEmptyString
    maturity_state: CapabilityMaturityState
    evidence_status: CapabilityEvidenceStatus
    mutation_risk: MutationRisk
    allowed_scopes: list[ReadinessScope] = Field(min_length=1)
    prohibited_scopes: list[ReadinessScope] = Field(min_length=1)
    dependencies: list[NonEmptyString] = Field(min_length=1)
    outputs: list[NonEmptyString] = Field(min_length=1)
    known_limitations: list[NonEmptyString] = Field(min_length=1)
    governance_notes: list[NonEmptyString] = Field(min_length=1)
    scoring_impact: bool = False
    runtime_mutation: bool = False
    production_enabled: bool = False

    @model_validator(mode="after")
    def _validate_scope_partition(self) -> "CapabilityEntry":
        allowed = set(self.allowed_scopes)
        prohibited = set(self.prohibited_scopes)
        overlap = allowed & prohibited
        if overlap:
            raise ValueError(f"allowed_scopes and prohibited_scopes overlap: {sorted(overlap)}")
        if not allowed:
            raise ValueError("allowed_scopes must not be empty")
        if not prohibited:
            raise ValueError("prohibited_scopes must not be empty")
        return self


class CapabilityRegistry(CapabilityRegistryModel):
    schema_version: Literal[CAPABILITY_REGISTRY_SCHEMA_VERSION]
    registry_version: Literal[CAPABILITY_REGISTRY_SCHEMA_VERSION]
    record_type: Literal["capability_registry"]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    governance_scope: GovernanceScope
    capability_count: int
    capabilities: list[CapabilityEntry]
    notes: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_registry(self) -> "CapabilityRegistry":
        if self.capability_count != len(self.capabilities):
            raise ValueError("capability_count does not match capabilities length")
        capability_ids = [capability.capability_id for capability in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("capability_ids must be unique")
        if self.governance_scope != "visual_signature":
            raise ValueError("governance_scope must be visual_signature")
        if any(capability.scoring_impact for capability in self.capabilities):
            raise ValueError("scoring_impact must be false for all capabilities")
        if any(capability.production_enabled for capability in self.capabilities):
            raise ValueError("production_enabled must be false for all capabilities")
        if any(capability.runtime_mutation for capability in self.capabilities):
            raise ValueError("runtime_mutation must be false for all capabilities in this registry")
        return self


def validate_capability_registry(payload: dict[str, Any]) -> list[str]:
    try:
        CapabilityRegistry.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []
