from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.visual_signature.governance import (
    build_runtime_policy_matrix,
    runtime_policy_matrix_markdown,
    validate_runtime_policy_matrix_payload,
    write_runtime_policy_matrix,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_runtime_policy_matrix.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_runtime_policy_matrix_is_consistent():
    matrix = build_runtime_policy_matrix()

    assert matrix.schema_version == "visual-signature-runtime-policy-matrix-1"
    assert matrix.matrix_version == "visual-signature-runtime-policy-matrix-1"
    assert matrix.governance_scope == "visual_signature"
    assert matrix.capability_count == 9
    assert matrix.policy_count == 60
    assert len(matrix.capabilities) == 9
    assert matrix.runtime_mutation_policy.scope_policies["production_runtime"] == "blocked"
    assert all(not capability.production_enabled for capability in matrix.capabilities)
    assert all(not capability.runtime_mutation for capability in matrix.capabilities)
    assert all(set(capability.allowed_scopes).isdisjoint(capability.prohibited_scopes) for capability in matrix.capabilities)
    assert "viewport_obstruction_detection" in {capability.capability_id for capability in matrix.capabilities}
    assert "mutation_audit" in {capability.capability_id for capability in matrix.capabilities}


def test_runtime_policy_matrix_validation_and_markdown():
    matrix = build_runtime_policy_matrix()
    payload = matrix.model_dump(mode="json")

    assert validate_runtime_policy_matrix_payload(payload) == []
    markdown = runtime_policy_matrix_markdown(matrix)
    assert "Capability existence != runtime approval" in markdown
    assert "Readiness is scope-dependent" in markdown
    assert "Runtime policy is governance-only" in markdown
    assert "No production enablement is implied" in markdown
    assert "production_runtime" in markdown
    assert "blocked" in markdown.lower()


def test_runtime_policy_matrix_script_writes_outputs(tmp_path: Path):
    script = _load_script(SCRIPT_PATH, "visual_signature_runtime_policy_matrix")
    output_root = tmp_path / "governance"

    assert script.main(["--output-root", str(output_root)]) == 0

    json_path = output_root / "runtime_policy_matrix.json"
    md_path = output_root / "runtime_policy_matrix.md"
    assert json_path.exists()
    assert md_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["capability_count"] == 9
    assert payload["policy_count"] == 60
    assert payload["runtime_mutation_policy"]["scope_policies"]["production_runtime"] == "blocked"
    assert validate_runtime_policy_matrix_payload(payload) == []
    assert "Capability existence != runtime approval" in md_path.read_text(encoding="utf-8")


def test_runtime_policy_matrix_rejects_unknown_capability():
    matrix = build_runtime_policy_matrix().model_dump(mode="json")
    matrix["capabilities"][0]["capability_id"] = "unknown_capability"

    errors = validate_runtime_policy_matrix_payload(matrix)
    assert errors
    assert "unknown capability_ids" in errors[0].lower()


def test_runtime_policy_matrix_rejects_invalid_scope():
    matrix = build_runtime_policy_matrix().model_dump(mode="json")
    matrix["capabilities"][0]["scope_policies"]["bogus_scope"] = "allowed"

    errors = validate_runtime_policy_matrix_payload(matrix)
    assert errors
    assert "bogus_scope" in errors[0].lower()


def test_runtime_policy_matrix_rejects_invalid_policy():
    matrix = build_runtime_policy_matrix().model_dump(mode="json")
    matrix["capabilities"][0]["scope_policies"]["broader_corpus_use"] = "maybe"

    errors = validate_runtime_policy_matrix_payload(matrix)
    assert errors
    assert "maybe" in errors[0].lower()


def test_runtime_policy_matrix_rejects_production_runtime_mutation():
    matrix = build_runtime_policy_matrix().model_dump(mode="json")
    matrix["runtime_mutation_policy"]["scope_policies"]["production_runtime"] = "allowed"

    errors = validate_runtime_policy_matrix_payload(matrix)
    assert errors
    assert "production_runtime must be blocked" in errors[0].lower()


def test_runtime_policy_matrix_rejects_count_mismatch():
    matrix = build_runtime_policy_matrix().model_dump(mode="json")
    matrix["policy_count"] = matrix["policy_count"] + 1

    errors = validate_runtime_policy_matrix_payload(matrix)
    assert errors
    assert "policy_count does not match" in errors[0].lower()


def test_runtime_policy_matrix_write_outputs(tmp_path: Path):
    outputs = write_runtime_policy_matrix(output_root=tmp_path)
    assert Path(outputs["runtime_policy_matrix_json"]).exists()
    assert Path(outputs["runtime_policy_matrix_md"]).exists()
