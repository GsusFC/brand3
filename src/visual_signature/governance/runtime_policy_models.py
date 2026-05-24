"""Pydantic models for the Visual Signature runtime policy matrix."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.visual_signature.calibration.readiness_models import ReadinessScope
from src.visual_signature.governance.capability_models import (
    CapabilityEvidenceStatus,
    CapabilityMaturityState,
    MutationRisk,
)
from src.visual_signature.governance.capability_registry import build_capability_registry


RUNTIME_POLICY_MATRIX_SCHEMA_VERSION = "visual-signature-runtime-policy-matrix-1"

RuntimePolicy = Literal["allowed", "blocked", "review_only", "experimental_only"]
GovernanceScope = Literal["visual_signature"]
RuntimeMutationPolicyScope = ReadinessScope

NonEmptyString = Annotated[str, Field(min_length=1)]

VALID_RUNTIME_POLICIES: tuple[RuntimePolicy, ...] = ("allowed", "blocked", "review_only", "experimental_only")


class RuntimePolicyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuntimePolicyEntry(RuntimePolicyModel):
    capability_id: NonEmptyString
    description: NonEmptyString
    layer: NonEmptyString
    maturity_state: CapabilityMaturityState
    evidence_status: CapabilityEvidenceStatus
    mutation_risk: MutationRisk
    runtime_mutation: bool = False
    production_enabled: bool = False
    allowed_scopes: list[ReadinessScope] = Field(min_length=1)
    prohibited_scopes: list[ReadinessScope] = Field(min_length=1)
    scope_policies: dict[ReadinessScope, RuntimePolicy] = Field(default_factory=dict)
    dependencies: list[NonEmptyString] = Field(default_factory=list)
    outputs: list[NonEmptyString] = Field(default_factory=list)
    governance_notes: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_entry(self) -> "RuntimePolicyEntry":
        if set(self.allowed_scopes) & set(self.prohibited_scopes):
            overlap = sorted(set(self.allowed_scopes) & set(self.prohibited_scopes))
            raise ValueError(f"allowed_scopes and prohibited_scopes overlap: {overlap}")
        if set(self.scope_policies) != set(ALL_READINESS_SCOPES):
            missing = sorted(set(ALL_READINESS_SCOPES) - set(self.scope_policies))
            extra = sorted(set(self.scope_policies) - set(ALL_READINESS_SCOPES))
            details = []
            if missing:
                details.append(f"missing scopes: {missing}")
            if extra:
                details.append(f"invalid scopes: {extra}")
            raise ValueError("scope_policies must cover all readiness scopes; " + "; ".join(details))
        if any(policy not in VALID_RUNTIME_POLICIES for policy in self.scope_policies.values()):
            invalid = sorted({policy for policy in self.scope_policies.values() if policy not in VALID_RUNTIME_POLICIES})
            raise ValueError(f"invalid runtime policies: {invalid}")
        if self.production_enabled:
            raise ValueError("production_enabled must be false for all runtime policy entries")
        return self


class RuntimeMutationPolicy(RuntimePolicyModel):
    scope_policies: dict[ReadinessScope, RuntimePolicy] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_policy(self) -> "RuntimeMutationPolicy":
        if set(self.scope_policies) != set(ALL_READINESS_SCOPES):
            missing = sorted(set(ALL_READINESS_SCOPES) - set(self.scope_policies))
            extra = sorted(set(self.scope_policies) - set(ALL_READINESS_SCOPES))
            details = []
            if missing:
                details.append(f"missing scopes: {missing}")
            if extra:
                details.append(f"invalid scopes: {extra}")
            raise ValueError("scope_policies must cover all readiness scopes; " + "; ".join(details))
        if self.scope_policies["production_runtime"] != "blocked":
            raise ValueError("production_runtime must be blocked for runtime mutation")
        if any(policy not in VALID_RUNTIME_POLICIES for policy in self.scope_policies.values()):
            invalid = sorted({policy for policy in self.scope_policies.values() if policy not in VALID_RUNTIME_POLICIES})
            raise ValueError(f"invalid runtime policies: {invalid}")
        return self


class RuntimePolicyMatrix(RuntimePolicyModel):
    schema_version: Literal[RUNTIME_POLICY_MATRIX_SCHEMA_VERSION]
    matrix_version: Literal[RUNTIME_POLICY_MATRIX_SCHEMA_VERSION]
    record_type: Literal["runtime_policy_matrix"]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    governance_scope: GovernanceScope
    capability_count: int = Field(ge=0)
    policy_count: int = Field(ge=0)
    capabilities: list[RuntimePolicyEntry] = Field(default_factory=list)
    runtime_mutation_policy: RuntimeMutationPolicy
    notes: list[NonEmptyString] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_matrix(self) -> "RuntimePolicyMatrix":
        if self.governance_scope != "visual_signature":
            raise ValueError("governance_scope must be visual_signature")
        if self.capability_count != len(self.capabilities):
            raise ValueError("capability_count does not match capabilities length")
        capability_ids = [entry.capability_id for entry in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("capability_ids must be unique")
        if self.policy_count != sum(len(entry.scope_policies) for entry in self.capabilities) + len(self.runtime_mutation_policy.scope_policies):
            raise ValueError("policy_count does not match explicit policy count")
        known_capabilities = {capability.capability_id for capability in build_capability_registry().capabilities}
        unknown = sorted(set(capability_ids) - known_capabilities)
        if unknown:
            raise ValueError(f"unknown capability_ids: {unknown}")
        for entry in self.capabilities:
            if entry.scope_policies["production_runtime"] == "allowed" and (entry.runtime_mutation or entry.production_enabled or entry.mutation_risk != "none"):
                raise ValueError(f"production_runtime cannot allow runtime mutation for capability {entry.capability_id}")
        if self.runtime_mutation_policy.scope_policies["production_runtime"] != "blocked":
            raise ValueError("runtime mutation must be blocked in production_runtime")
        return self


ALL_READINESS_SCOPES: tuple[ReadinessScope, ...] = (
    "broader_corpus_use",
    "provider_pilot_use",
    "human_review_scaling",
    "production_runtime",
    "scoring_integration",
    "model_training",
)


KNOWN_CAPABILITY_IDS: tuple[str, ...] = (
    "viewport_obstruction_detection",
    "affordance_semantics",
    "affordance_localization",
    "perceptual_state_machine",
    "mutation_audit",
    "phase_two_review",
    "calibration_bundle",
    "calibration_reliability_reporting",
    "calibration_readiness_gate",
)


def validate_runtime_policy_matrix_payload(payload: dict[str, Any]) -> list[str]:
    try:
        RuntimePolicyMatrix.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    return []
