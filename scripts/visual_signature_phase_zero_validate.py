from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.visual_signature.phase_zero import PHASE_ZERO_ROOT
from src.visual_signature.phase_zero.eligibility import evaluate_dataset_eligibility
from src.visual_signature.phase_zero.validation import validate_registry_document, validate_record_schema
from src.visual_signature.phase_zero.models import (
    DatasetEligibilityRecord,
    MutationAuditRecord,
    ObservationRegistry,
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


SCHEMA_FILES = {
    "schemas/observation_registry.schema.json": ObservationRegistry,
    "schemas/state_registry.schema.json": StateRegistry,
    "schemas/transition_registry.schema.json": TransitionRegistry,
    "schemas/scoring_registry.schema.json": ScoringRegistry,
    "schemas/uncertainty_policy.schema.json": UncertaintyPolicy,
    "schemas/uncertainty_profile.schema.json": UncertaintyProfile,
    "schemas/reasoning_trace.schema.json": ReasoningTrace,
    "schemas/perceptual_observation.schema.json": PerceptualObservationRecord,
    "schemas/perceptual_state.schema.json": PerceptualStateRecord,
    "schemas/transition_record.schema.json": TransitionRecord,
    "schemas/mutation_audit.schema.json": MutationAuditRecord,
    "schemas/review_record.schema.json": ReviewRecord,
    "schemas/dataset_eligibility.schema.json": DatasetEligibilityRecord,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Phase Zero artifacts.")
    parser.add_argument("--root", type=Path, default=PHASE_ZERO_ROOT)
    args = parser.parse_args(argv)

    root = args.root
    errors: list[str] = []

    manifest = _load_json(root / "manifests" / "phase_zero_manifest.json")
    if manifest.get("schema_version") != "phase-zero-manifest-1":
        errors.append("manifest_schema_version_invalid")

    for relative, model in SCHEMA_FILES.items():
        schema = _load_json(root / relative)
        if schema.get("title") is None and schema.get("$schema") is None:
            errors.append(f"{relative}:missing_schema_metadata")
        schema_version = schema.get("properties", {}).get("schema_version")
        if not isinstance(schema_version, dict):
            errors.append(f"{relative}:schema_version_property_missing")
        elif "const" not in schema_version and "enum" not in schema_version:
            errors.append(f"{relative}:schema_version_not_constrained")
        taxonomy_version = schema.get("properties", {}).get("taxonomy_version")
        if not isinstance(taxonomy_version, dict):
            errors.append(f"{relative}:taxonomy_version_property_missing")
        elif "const" not in taxonomy_version and "enum" not in taxonomy_version:
            errors.append(f"{relative}:taxonomy_version_not_constrained")
        # Sanity check that the generated schema matches the model contract.
        if model.model_json_schema().get("type") != schema.get("type"):
            errors.append(f"{relative}:schema_type_mismatch")

    for relative, registry_type in (
        ("taxonomy/observation_registry.json", "observation_registry"),
        ("taxonomy/state_registry.json", "state_registry"),
        ("taxonomy/transition_registry.json", "transition_registry"),
        ("taxonomy/scoring_registry.json", "scoring_registry"),
    ):
        registry_errors = validate_registry_document(_load_json(root / relative), registry_type=registry_type)
        errors.extend(f"{relative}:{item}" for item in registry_errors)

    for relative, model in (
        ("fixtures/observation_record.example.json", PerceptualObservationRecord),
        ("fixtures/state_record.example.json", PerceptualStateRecord),
        ("fixtures/transition_record.example.json", TransitionRecord),
        ("fixtures/mutation_audit.example.json", MutationAuditRecord),
        ("fixtures/review_record.example.json", ReviewRecord),
        ("fixtures/reasoning_trace.example.json", ReasoningTrace),
        ("fixtures/uncertainty_profile.example.json", UncertaintyProfile),
        ("fixtures/dataset_eligibility.example.json", DatasetEligibilityRecord),
    ):
        payload = _load_json(root / relative)
        validation_errors = validate_record_schema(payload)
        if validation_errors:
            errors.extend(f"{relative}:{item}" for item in validation_errors)
        else:
            try:
                model.model_validate(payload)
            except Exception as exc:
                errors.append(f"{relative}:{exc}")

    policy = _load_json(root / "taxonomy" / "uncertainty_policy.json")
    if policy.get("confidence_threshold") != 0.8:
        errors.append("uncertainty_policy_confidence_threshold_invalid")

    result = evaluate_dataset_eligibility(_load_json(root / "fixtures" / "dataset_eligibility.example.json"))
    if not result.eligible:
        errors.append("dataset_eligibility_example_not_eligible")

    if errors:
        for item in errors:
            print(item)
        return 1

    print(json.dumps({"root": str(root), "validated": True, "schema_count": len(SCHEMA_FILES)}, indent=2))
    return 0


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
