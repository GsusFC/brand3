"""Build and export the Visual Signature capability registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.visual_signature.calibration.readiness_models import ReadinessScope
from src.visual_signature.governance.capability_models import (
    CAPABILITY_REGISTRY_SCHEMA_VERSION,
    CapabilityEntry,
    CapabilityRegistry,
    validate_capability_registry,
)


GOVERNANCE_SCOPE = "visual_signature"
DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "governance"
ALL_SCOPES: tuple[ReadinessScope, ...] = (
    "broader_corpus_use",
    "provider_pilot_use",
    "human_review_scaling",
    "production_runtime",
    "scoring_integration",
    "model_training",
)


def build_capability_registry() -> CapabilityRegistry:
    capabilities = [_build_entry(item) for item in _capability_specs()]
    return CapabilityRegistry(
        schema_version=CAPABILITY_REGISTRY_SCHEMA_VERSION,
        registry_version=CAPABILITY_REGISTRY_SCHEMA_VERSION,
        record_type="capability_registry",
        governance_scope=GOVERNANCE_SCOPE,
        capability_count=len(capabilities),
        capabilities=capabilities,
        notes=[
            "This is an evidence-only governance registry.",
            "Capability presence does not imply production approval.",
            "Readiness is scope-dependent and separate from capability presence.",
            "Evidence-only capabilities can still be not_ready.",
            "No scoring, rubric dimensions, production UI, production reports, or capture behavior are modified.",
        ],
    )


def write_capability_registry(
    *,
    output_root: str | Path | None = None,
    output_json_path: str | Path | None = None,
    output_md_path: str | Path | None = None,
) -> dict[str, str]:
    registry = build_capability_registry()
    validation_errors = validate_capability_registry(registry.model_dump(mode="json"))
    if validation_errors:
        raise ValueError(f"Capability registry validation failed: {validation_errors}")

    root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    output_json = Path(output_json_path) if output_json_path is not None else root / "capability_registry.json"
    output_md = Path(output_md_path) if output_md_path is not None else root / "capability_registry.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(registry.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(capability_registry_markdown(registry) + "\n", encoding="utf-8")
    return {"capability_registry_json": str(output_json), "capability_registry_md": str(output_md)}


def capability_registry_markdown(registry: CapabilityRegistry) -> str:
    lines = [
        "# Visual Signature Capability Registry",
        "",
        "Evidence-only governance registry for Visual Signature capabilities.",
        "",
        "- Not a production enablement list: yes",
        "- Capability presence != production approval: yes",
        "- Readiness is scope-dependent: yes",
        "- Evidence-only capabilities can still be not_ready: yes",
        "",
        "## Registry Metadata",
        "",
        f"- Registry version: `{registry.registry_version}`",
        f"- Generated at: {registry.generated_at.isoformat()}",
        f"- Capability count: {registry.capability_count}",
        f"- Governance scope: `{registry.governance_scope}`",
        "",
        "## Governance Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in registry.notes)
    lines.extend(
        [
            "",
            "## Capabilities",
            "",
        ]
    )
    for capability in registry.capabilities:
        lines.extend(
            [
                f"### {capability.capability_id}",
                "",
                f"- Description: {capability.description}",
                f"- Layer: {capability.layer}",
                f"- Maturity state: `{capability.maturity_state}`",
                f"- Evidence status: `{capability.evidence_status}`",
                f"- Mutation risk: `{capability.mutation_risk}`",
                f"- Scoring impact: `{str(capability.scoring_impact).lower()}`",
                f"- Runtime mutation: `{str(capability.runtime_mutation).lower()}`",
                f"- Production enabled: `{str(capability.production_enabled).lower()}`",
                f"- Allowed scopes: {', '.join(f'`{scope}`' for scope in capability.allowed_scopes)}",
                f"- Prohibited scopes: {', '.join(f'`{scope}`' for scope in capability.prohibited_scopes)}",
                f"- Dependencies: {', '.join(f'`{item}`' for item in capability.dependencies)}",
                f"- Outputs: {', '.join(f'`{item}`' for item in capability.outputs)}",
                f"- Known limitations: {', '.join(capability.known_limitations)}",
                f"- Governance notes: {', '.join(capability.governance_notes)}",
                "",
            ]
        )
    lines.extend(
        [
            "## Validation Notes",
            "",
            "- Prohibited scopes are disjoint from allowed scopes.",
            "- Registry validation rejects score-impacting or production-enabled capabilities.",
            "- The registry is evidence-only and does not alter runtime behavior.",
        ]
    )
    return "\n".join(lines).rstrip()


def validate_capability_registry_payload(payload: dict[str, Any]) -> list[str]:
    return validate_capability_registry(payload)


def _build_entry(spec: dict[str, Any]) -> CapabilityEntry:
    allowed_scopes = list(spec["allowed_scopes"])
    prohibited_scopes = [scope for scope in ALL_SCOPES if scope not in allowed_scopes]
    return CapabilityEntry(
        capability_id=spec["capability_id"],
        description=spec["description"],
        layer=spec["layer"],
        maturity_state=spec["maturity_state"],
        evidence_status=spec["evidence_status"],
        mutation_risk=spec["mutation_risk"],
        allowed_scopes=allowed_scopes,
        prohibited_scopes=prohibited_scopes,
        dependencies=spec["dependencies"],
        outputs=spec["outputs"],
        known_limitations=spec["known_limitations"],
        governance_notes=spec["governance_notes"],
        scoring_impact=False,
        runtime_mutation=False,
        production_enabled=False,
    )


def _capability_specs() -> list[dict[str, Any]]:
    return [
        {
            "capability_id": "viewport_obstruction_detection",
            "description": "Detects viewport obstructions such as cookie banners, consent modals, login walls, and overlays.",
            "layer": "vision",
            "maturity_state": "governed",
            "evidence_status": "validated",
            "mutation_risk": "low",
            "allowed_scopes": ["broader_corpus_use", "provider_pilot_use", "human_review_scaling"],
            "dependencies": ["raw_viewport_capture", "dom_heuristics", "obstruction_signals"],
            "outputs": ["viewport_obstruction", "obstruction_audit", "capture_manifest.obstruction_fields"],
            "known_limitations": [
                "Overlay ownership can be ambiguous.",
                "False positives remain possible on sticky site chrome.",
            ],
            "governance_notes": [
                "Detection is evidence-only.",
                "Does not click, dismiss, or mutate the page.",
            ],
        },
        {
            "capability_id": "affordance_semantics",
            "description": "Classifies visible interaction affordances such as close, consent, login, subscription, and checkout controls.",
            "layer": "perception",
            "maturity_state": "governed",
            "evidence_status": "validated",
            "mutation_risk": "low",
            "allowed_scopes": ["broader_corpus_use", "provider_pilot_use", "human_review_scaling"],
            "dependencies": ["visible_text", "aria_label", "role", "dom_context", "overlay_context"],
            "outputs": ["candidate_click_targets.affordance_category", "dismissal_audit.affordance_category_distribution"],
            "known_limitations": [
                "Semantic labels are conservative by design.",
                "Classification does not imply click eligibility.",
            ],
            "governance_notes": [
                "Diagnostics only.",
                "Click behavior remains separate.",
            ],
        },
        {
            "capability_id": "affordance_localization",
            "description": "Determines whether a detected affordance belongs to the active obstruction or unrelated UI.",
            "layer": "perception",
            "maturity_state": "constrained",
            "evidence_status": "validated",
            "mutation_risk": "low",
            "allowed_scopes": ["broader_corpus_use", "provider_pilot_use", "human_review_scaling"],
            "dependencies": ["dom_ancestry", "viewport_location", "z_index", "overlay_context", "aria_dialog_relationships"],
            "outputs": ["candidate_click_targets.affordance_owner", "dismissal_audit.affordance_owner_distribution"],
            "known_limitations": [
                "Ownership can remain unknown when evidence is mixed.",
                "Localization is diagnostic-only and does not widen clicking.",
            ],
            "governance_notes": [
                "Used to explain rejected targets.",
                "Does not promote targets into execution.",
            ],
        },
        {
            "capability_id": "perceptual_state_machine",
            "description": "Tracks perceptual state transitions and mutation lineage for captured interfaces.",
            "layer": "perception",
            "maturity_state": "governed",
            "evidence_status": "validated",
            "mutation_risk": "low",
            "allowed_scopes": ["broader_corpus_use", "provider_pilot_use", "human_review_scaling"],
            "dependencies": ["raw_capture", "obstruction_detection", "safe_intervention_policy"],
            "outputs": ["perceptual_state", "perceptual_transitions", "mutation_audit"],
            "known_limitations": [
                "State vocabulary is intentionally small.",
                "Experimental mutation records remain supplemental to raw evidence.",
            ],
            "governance_notes": [
                "Supports evidence lineage and auditability.",
                "Does not alter scoring or capture defaults.",
            ],
        },
        {
            "capability_id": "mutation_audit",
            "description": "Records safe, minimal interaction attempts and before/after evidence lineage.",
            "layer": "mutation",
            "maturity_state": "constrained",
            "evidence_status": "validated",
            "mutation_risk": "moderate",
            "allowed_scopes": ["broader_corpus_use", "provider_pilot_use", "human_review_scaling"],
            "dependencies": ["dismissal_flow", "raw_viewport_capture", "safe_affordance_discovery"],
            "outputs": ["mutation_audit", "dismissal_audit"],
            "known_limitations": [
                "Safe attempts are opt-in and conservative.",
                "Mutation success never replaces raw evidence.",
            ],
            "governance_notes": [
                "Audit trail only.",
                "Supports reversible evidence-preserving captures.",
            ],
        },
        {
            "capability_id": "phase_two_review",
            "description": "Joins reviewed outcomes to Phase One records for human validation and eligibility control.",
            "layer": "validation",
            "maturity_state": "governed",
            "evidence_status": "validated",
            "mutation_risk": "none",
            "allowed_scopes": ["broader_corpus_use", "human_review_scaling"],
            "dependencies": ["phase_one_records", "review_records"],
            "outputs": ["review_outcome", "reviewed_dataset_eligibility"],
            "known_limitations": [
                "Human review remains required for uncertain records.",
                "Review coverage is sample-dependent.",
            ],
            "governance_notes": [
                "Human validation remains separate from scoring.",
                "Reviewed eligibility is a governance output only.",
            ],
        },
        {
            "capability_id": "calibration_bundle",
            "description": "Builds the evidence bundle that joins machine claims with reviewed outcomes.",
            "layer": "calibration",
            "maturity_state": "governed",
            "evidence_status": "validated",
            "mutation_risk": "none",
            "allowed_scopes": ["broader_corpus_use", "provider_pilot_use", "human_review_scaling"],
            "dependencies": ["phase_one_records", "phase_two_reviews", "capture_manifest", "dismissal_audit"],
            "outputs": ["calibration_records", "calibration_summary", "calibration_manifest"],
            "known_limitations": [
                "Current bundle is small and category-sparse.",
                "High-confidence contradictions are still present.",
            ],
            "governance_notes": [
                "Evidence-only bundle generation.",
                "No scoring or runtime behavior changes.",
            ],
        },
        {
            "capability_id": "calibration_reliability_reporting",
            "description": "Produces evidence-only reliability interpretation of the calibration bundle.",
            "layer": "calibration",
            "maturity_state": "governed",
            "evidence_status": "validated",
            "mutation_risk": "none",
            "allowed_scopes": ["broader_corpus_use", "human_review_scaling"],
            "dependencies": ["calibration_bundle", "validated_records"],
            "outputs": ["calibration_reliability_report"],
            "known_limitations": [
                "Interpretive and descriptive only.",
                "Not a substitute for larger corpus sampling.",
            ],
            "governance_notes": [
                "Summarizes bundle quality and limitations.",
                "Does not imply readiness by itself.",
            ],
        },
        {
            "capability_id": "calibration_readiness_gate",
            "description": "Evaluates whether the calibration bundle is ready for a specific scope.",
            "layer": "governance",
            "maturity_state": "constrained",
            "evidence_status": "validated",
            "mutation_risk": "none",
            "allowed_scopes": ["broader_corpus_use"],
            "dependencies": ["calibration_bundle", "calibration_manifest", "calibration_corpus_manifest"],
            "outputs": ["calibration_readiness", "calibration_governance_checkpoint"],
            "known_limitations": [
                "Current implementation only governs broader corpus use.",
                "Does not define readiness for production, scoring, runtime, provider pilot, or training.",
            ],
            "governance_notes": [
                "Scope-aware readiness is explicit and conservative.",
                "Unsupported scopes are not silently reused from broader-corpus thresholds.",
            ],
        },
    ]
