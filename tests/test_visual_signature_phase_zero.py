from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

from src.visual_signature.phase_zero import PHASE_ZERO_ROOT
from src.visual_signature.phase_zero.eligibility import evaluate_dataset_eligibility
from src.visual_signature.phase_zero.validation import validate_record_schema, validate_registry_document
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


GENERATE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "visual_signature_phase_zero_generate.py"
VALIDATE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "visual_signature_phase_zero_validate.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_phase_zero_checked_in_files_validate():
    root = PHASE_ZERO_ROOT

    manifest = _read_json(root / "manifests" / "phase_zero_manifest.json")
    assert manifest["schema_version"] == "phase-zero-manifest-1"
    assert "schemas/uncertainty_profile.schema.json" in manifest["files"]

    assert ObservationRegistry.model_validate(_read_json(root / "taxonomy" / "observation_registry.json"))
    assert StateRegistry.model_validate(_read_json(root / "taxonomy" / "state_registry.json"))
    assert TransitionRegistry.model_validate(_read_json(root / "taxonomy" / "transition_registry.json"))
    assert ScoringRegistry.model_validate(_read_json(root / "taxonomy" / "scoring_registry.json"))
    assert UncertaintyPolicy.model_validate(_read_json(root / "taxonomy" / "uncertainty_policy.json"))

    observation = _read_json(root / "fixtures" / "observation_record.example.json")
    state = _read_json(root / "fixtures" / "state_record.example.json")
    transition = _read_json(root / "fixtures" / "transition_record.example.json")
    mutation = _read_json(root / "fixtures" / "mutation_audit.example.json")
    review = _read_json(root / "fixtures" / "review_record.example.json")
    reasoning = _read_json(root / "fixtures" / "reasoning_trace.example.json")
    uncertainty = _read_json(root / "fixtures" / "uncertainty_profile.example.json")
    eligibility = _read_json(root / "fixtures" / "dataset_eligibility.example.json")
    assert observation["taxonomy_version"] == "phase-zero-taxonomy-1"
    assert state["taxonomy_version"] == "phase-zero-taxonomy-1"
    assert transition["taxonomy_version"] == "phase-zero-taxonomy-1"
    assert mutation["taxonomy_version"] == "phase-zero-taxonomy-1"
    assert review["taxonomy_version"] == "phase-zero-taxonomy-1"
    assert reasoning["taxonomy_version"] == "phase-zero-taxonomy-1"
    assert uncertainty["taxonomy_version"] == "phase-zero-taxonomy-1"
    assert eligibility["taxonomy_version"] == "phase-zero-taxonomy-1"
    assert PerceptualObservationRecord.model_validate(observation)
    assert PerceptualStateRecord.model_validate(state)
    assert TransitionRecord.model_validate(transition)
    assert MutationAuditRecord.model_validate(mutation)
    assert ReviewRecord.model_validate(review)
    assert ReasoningTrace.model_validate(reasoning)
    assert UncertaintyProfile.model_validate(uncertainty)
    assert DatasetEligibilityRecord.model_validate(eligibility)


def test_phase_zero_dataset_eligibility_rules_are_executable():
    eligible = _read_json(PHASE_ZERO_ROOT / "fixtures" / "dataset_eligibility.example.json")
    result = evaluate_dataset_eligibility(eligible)
    assert result.eligible is True
    assert result.schema_valid is True
    assert result.raw_evidence_preserved is True
    assert result.mutation_lineage_preserved is True
    assert result.review_required is True
    assert result.review_completed is True

    blocked = deepcopy(eligible)
    blocked["evidence_refs"] = []
    blocked["raw_evidence_preserved"] = False
    blocked["review_completed"] = False
    blocked["uncertainty_below_threshold"] = False
    blocked_result = evaluate_dataset_eligibility(blocked)
    assert blocked_result.eligible is False
    assert "raw_evidence_missing" in blocked_result.blocked_reasons


def test_phase_zero_rejects_schema_version_mismatch():
    observation = _read_json(PHASE_ZERO_ROOT / "fixtures" / "observation_record.example.json")
    observation["schema_version"] = "phase-zero-observation-record-999"

    errors = validate_record_schema(observation)

    assert errors
    assert any("schema_version" in item for item in errors)

    missing_taxonomy = _read_json(PHASE_ZERO_ROOT / "fixtures" / "observation_record.example.json")
    missing_taxonomy.pop("taxonomy_version", None)
    missing_errors = validate_record_schema(missing_taxonomy)
    assert missing_errors


def test_phase_zero_rejects_unsupported_inference():
    observation = _read_json(PHASE_ZERO_ROOT / "fixtures" / "observation_record.example.json")
    observation["uncertainty"]["unsupported_inference"] = True

    result = evaluate_dataset_eligibility(observation)

    assert result.eligible is False
    assert "unsupported_inference_present" in result.blocked_reasons


def test_phase_zero_reviewer_required_blocks_until_completed():
    eligible = _read_json(PHASE_ZERO_ROOT / "fixtures" / "dataset_eligibility.example.json")
    eligible["review_completed"] = False
    eligible["uncertainty_below_threshold"] = False

    result = evaluate_dataset_eligibility(eligible)

    assert result.eligible is False
    assert "review_required_not_completed" in result.blocked_reasons


def test_phase_zero_mutation_lineage_missing_blocks_export():
    eligible = _read_json(PHASE_ZERO_ROOT / "fixtures" / "dataset_eligibility.example.json")
    eligible["mutation_audit"] = {
        "schema_version": "phase-zero-mutation-audit-1",
        "taxonomy_version": "phase-zero-taxonomy-1",
        "record_type": "mutation_audit",
        "mutation_id": "mutation_missing_lineage",
        "created_at": "2026-05-11T10:00:00Z",
        "capture_id": "cap_phase_zero_example",
        "brand_name": "Example Brand",
        "website_url": "https://example.com",
        "mutation_type": "cookie_banner_dismissal",
        "before_state": "ELIGIBLE_FOR_SAFE_INTERVENTION",
        "after_state": "REVIEW_REQUIRED_STATE",
        "attempted": True,
        "successful": False,
        "reversible": True,
        "risk_level": "low",
        "trigger": "close",
        "evidence_preserved": True,
        "before_artifact_ref": "",
        "after_artifact_ref": "examples/visual_signature/phase_zero/fixtures/clean_attempt.example.png",
        "lineage_refs": ["capture:phase-zero-example"],
        "integrity_notes": [],
    }

    result = evaluate_dataset_eligibility(eligible)

    assert result.eligible is False
    assert "mutation_lineage_missing" in result.blocked_reasons


def test_phase_zero_unknown_registry_key_is_rejected():
    registry = _read_json(PHASE_ZERO_ROOT / "taxonomy" / "observation_registry.json")
    registry["items"].append(
        {
            "key": "new_unapproved_key",
            "layer": "functional",
            "description": "Not allowed",
            "value_type": "categorical",
            "notes": [],
        }
    )

    errors = validate_registry_document(registry, registry_type="observation_registry")

    assert errors
    assert any("unknown_key:new_unapproved_key" in item for item in errors)


def test_phase_zero_review_record_schema_is_valid():
    review = _read_json(PHASE_ZERO_ROOT / "fixtures" / "review_record.example.json")
    assert review["record_type"] == "review_record"
    assert ReviewRecord.model_validate(review)
    assert validate_record_schema(review) == []


def test_phase_zero_generate_and_validate_scripts_round_trip(tmp_path):
    phase_zero_root = tmp_path / "phase_zero"
    repo_root = tmp_path / "repo"

    generate_script = _load_script(GENERATE_SCRIPT, "visual_signature_phase_zero_generate")
    validate_script = _load_script(VALIDATE_SCRIPT, "visual_signature_phase_zero_validate")

    assert generate_script.main(["--root", str(phase_zero_root), "--repo-root", str(repo_root)]) == 0
    assert (phase_zero_root / "schemas" / "perceptual_observation.schema.json").exists()
    assert (phase_zero_root / "fixtures" / "uncertainty_profile.example.json").exists()
    assert (phase_zero_root / "fixtures" / "review_record.example.json").exists()
    assert (repo_root / "src" / "visual_signature" / "phase_zero" / "types.ts").exists()

    assert validate_script.main(["--root", str(phase_zero_root)]) == 0
