"""Build and export the Visual Signature runtime policy matrix."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.governance.capability_registry import build_capability_registry
from src.visual_signature.governance.runtime_policy_models import (
    ALL_READINESS_SCOPES,
    RUNTIME_POLICY_MATRIX_SCHEMA_VERSION,
    RuntimeMutationPolicy,
    RuntimePolicyEntry,
    RuntimePolicyMatrix,
    validate_runtime_policy_matrix_payload,
)


GOVERNANCE_SCOPE = "visual_signature"
DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "governance"


def build_runtime_policy_matrix() -> RuntimePolicyMatrix:
    registry = build_capability_registry()
    capability_map = {capability.capability_id: capability for capability in registry.capabilities}
    entries = [_build_entry(capability_map[item["capability_id"]], item["scope_policies"]) for item in _policy_specs()]
    runtime_mutation_policy = RuntimeMutationPolicy(
        scope_policies={
            "broader_corpus_use": "experimental_only",
            "provider_pilot_use": "experimental_only",
            "human_review_scaling": "review_only",
            "production_runtime": "blocked",
            "scoring_integration": "blocked",
            "model_training": "blocked",
        }
    )
    return RuntimePolicyMatrix(
        schema_version=RUNTIME_POLICY_MATRIX_SCHEMA_VERSION,
        matrix_version=RUNTIME_POLICY_MATRIX_SCHEMA_VERSION,
        record_type="runtime_policy_matrix",
        generated_at=datetime.now(timezone.utc),
        governance_scope=GOVERNANCE_SCOPE,
        capability_count=len(entries),
        policy_count=sum(len(entry.scope_policies) for entry in entries) + len(runtime_mutation_policy.scope_policies),
        capabilities=entries,
        runtime_mutation_policy=runtime_mutation_policy,
        notes=[
            "Evidence-only governance matrix.",
            "Capability presence does not imply production approval.",
            "Readiness is scope-dependent and separate from capability presence.",
            "Runtime policy is governance-only and does not modify runtime behavior.",
            "No scoring, rubric dimensions, production UI, production reports, or capture behavior are modified.",
        ],
    )


def write_runtime_policy_matrix(
    *,
    output_root: str | Path | None = None,
    output_json_path: str | Path | None = None,
    output_md_path: str | Path | None = None,
) -> dict[str, str]:
    matrix = build_runtime_policy_matrix()
    validation_errors = validate_runtime_policy_matrix_payload(matrix.model_dump(mode="json"))
    if validation_errors:
        raise ValueError(f"Runtime policy matrix validation failed: {validation_errors}")

    root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    output_json = Path(output_json_path) if output_json_path is not None else root / "runtime_policy_matrix.json"
    output_md = Path(output_md_path) if output_md_path is not None else root / "runtime_policy_matrix.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(matrix.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(runtime_policy_matrix_markdown(matrix) + "\n", encoding="utf-8")
    return {"runtime_policy_matrix_json": str(output_json), "runtime_policy_matrix_md": str(output_md)}


def runtime_policy_matrix_markdown(matrix: RuntimePolicyMatrix) -> str:
    lines = [
        "# Visual Signature Runtime Policy Matrix",
        "",
        "Evidence-only governance matrix for Visual Signature capabilities under different readiness scopes.",
        "",
        "- Capability existence != runtime approval: yes",
        "- Readiness is scope-dependent: yes",
        "- Runtime policy is governance-only: yes",
        "- No production enablement is implied: yes",
        "",
        "## Registry Metadata",
        "",
        f"- Matrix version: `{matrix.matrix_version}`",
        f"- Generated at: {matrix.generated_at.isoformat()}",
        f"- Governance scope: `{matrix.governance_scope}`",
        f"- Capability count: {matrix.capability_count}",
        f"- Policy count: {matrix.policy_count}",
        "",
        "## Scope Legend",
        "",
    ]
    lines.extend(
        [
            "- `allowed`: capability may be used within the evaluated evidence-only scope.",
            "- `blocked`: capability must not be used within the evaluated scope.",
            "- `review_only`: capability may be reviewed or inspected, but not used for runtime execution.",
            "- `experimental_only`: capability is limited to experimental diagnostics and is not approved for broader use.",
            "",
            "## Runtime Mutation Guardrail",
            "",
        ]
    )
    for scope, policy in matrix.runtime_mutation_policy.scope_policies.items():
        lines.append(f"- {scope}: {policy}")
    lines.extend(["", "## Capabilities", ""])
    for capability in matrix.capabilities:
        lines.extend(
            [
                f"### {capability.capability_id}",
                "",
                f"- Description: {capability.description}",
                f"- Layer: {capability.layer}",
                f"- Maturity state: `{capability.maturity_state}`",
                f"- Evidence status: `{capability.evidence_status}`",
                f"- Mutation risk: `{capability.mutation_risk}`",
                f"- Runtime mutation: `{str(capability.runtime_mutation).lower()}`",
                f"- Production enabled: `{str(capability.production_enabled).lower()}`",
                f"- Allowed scopes: {', '.join(f'`{scope}`' for scope in capability.allowed_scopes)}",
                f"- Prohibited scopes: {', '.join(f'`{scope}`' for scope in capability.prohibited_scopes)}",
                "",
                "| Scope | Policy |",
                "| --- | --- |",
            ]
        )
        for scope in ALL_READINESS_SCOPES:
            lines.append(f"| {scope} | {capability.scope_policies[scope]} |")
        lines.extend([""])
    lines.extend(
        [
            "## Validation Notes",
            "",
            "- All capability IDs must exist in the capability registry.",
            "- All readiness scopes are explicit and validated.",
            "- `production_runtime` never silently allows runtime mutation.",
            "- Blocked and allowed states are not co-located for the same capability/scope.",
        ]
    )
    return "\n".join(lines).rstrip()


def validate_runtime_policy_matrix(payload: dict[str, Any]) -> list[str]:
    return validate_runtime_policy_matrix_payload(payload)


def _build_entry(capability, scope_policies: dict[str, str]) -> RuntimePolicyEntry:
    return RuntimePolicyEntry(
        capability_id=capability.capability_id,
        description=capability.description,
        layer=capability.layer,
        maturity_state=capability.maturity_state,
        evidence_status=capability.evidence_status,
        mutation_risk=capability.mutation_risk,
        runtime_mutation=capability.runtime_mutation,
        production_enabled=capability.production_enabled,
        allowed_scopes=list(capability.allowed_scopes),
        prohibited_scopes=list(capability.prohibited_scopes),
        scope_policies=scope_policies,
        dependencies=list(capability.dependencies),
        outputs=list(capability.outputs),
        governance_notes=list(capability.governance_notes),
    )


def _policy_specs() -> list[dict[str, Any]]:
    return [
        {
            "capability_id": "viewport_obstruction_detection",
            "scope_policies": {
                "broader_corpus_use": "allowed",
                "provider_pilot_use": "allowed",
                "human_review_scaling": "allowed",
                "production_runtime": "review_only",
                "scoring_integration": "blocked",
                "model_training": "blocked",
            },
        },
        {
            "capability_id": "affordance_semantics",
            "scope_policies": {
                "broader_corpus_use": "review_only",
                "provider_pilot_use": "review_only",
                "human_review_scaling": "allowed",
                "production_runtime": "review_only",
                "scoring_integration": "blocked",
                "model_training": "blocked",
            },
        },
        {
            "capability_id": "affordance_localization",
            "scope_policies": {
                "broader_corpus_use": "review_only",
                "provider_pilot_use": "review_only",
                "human_review_scaling": "allowed",
                "production_runtime": "review_only",
                "scoring_integration": "blocked",
                "model_training": "blocked",
            },
        },
        {
            "capability_id": "perceptual_state_machine",
            "scope_policies": {
                "broader_corpus_use": "review_only",
                "provider_pilot_use": "review_only",
                "human_review_scaling": "allowed",
                "production_runtime": "review_only",
                "scoring_integration": "blocked",
                "model_training": "blocked",
            },
        },
        {
            "capability_id": "mutation_audit",
            "scope_policies": {
                "broader_corpus_use": "experimental_only",
                "provider_pilot_use": "experimental_only",
                "human_review_scaling": "review_only",
                "production_runtime": "blocked",
                "scoring_integration": "blocked",
                "model_training": "blocked",
            },
        },
        {
            "capability_id": "phase_two_review",
            "scope_policies": {
                "broader_corpus_use": "review_only",
                "provider_pilot_use": "review_only",
                "human_review_scaling": "allowed",
                "production_runtime": "blocked",
                "scoring_integration": "blocked",
                "model_training": "blocked",
            },
        },
        {
            "capability_id": "calibration_bundle",
            "scope_policies": {
                "broader_corpus_use": "allowed",
                "provider_pilot_use": "allowed",
                "human_review_scaling": "allowed",
                "production_runtime": "review_only",
                "scoring_integration": "blocked",
                "model_training": "blocked",
            },
        },
        {
            "capability_id": "calibration_reliability_reporting",
            "scope_policies": {
                "broader_corpus_use": "allowed",
                "provider_pilot_use": "review_only",
                "human_review_scaling": "allowed",
                "production_runtime": "review_only",
                "scoring_integration": "blocked",
                "model_training": "blocked",
            },
        },
        {
            "capability_id": "calibration_readiness_gate",
            "scope_policies": {
                "broader_corpus_use": "review_only",
                "provider_pilot_use": "blocked",
                "human_review_scaling": "blocked",
                "production_runtime": "blocked",
                "scoring_integration": "blocked",
                "model_training": "blocked",
            },
        },
    ]
