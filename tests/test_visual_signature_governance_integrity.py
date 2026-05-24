from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

from src.visual_signature.governance import (
    check_governance_integrity,
    governance_integrity_report_markdown,
    write_governance_integrity_report,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_governance_integrity.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_current_governance_artifacts_are_valid():
    report = check_governance_integrity(
        capability_registry_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "capability_registry.json",
        runtime_policy_matrix_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "runtime_policy_matrix.json",
        calibration_readiness_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_readiness.json",
        calibration_governance_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_governance_checkpoint.md",
        technical_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "technical_checkpoint.md",
        reliable_visual_perception_path=PROJECT_ROOT / "examples" / "visual_signature" / "reliable_visual_perception.md",
    )

    assert report["status"] == "valid"
    assert report["error_count"] == 0
    assert report["readiness_scope"] == "broader_corpus_use"
    assert report["readiness_status"] == "not_ready"
    assert "Governance Integrity Check" in governance_integrity_report_markdown(report)


def test_governance_integrity_report_is_written(tmp_path: Path):
    outputs = write_governance_integrity_report(
        output_root=tmp_path,
        capability_registry_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "capability_registry.json",
        runtime_policy_matrix_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "runtime_policy_matrix.json",
        calibration_readiness_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_readiness.json",
        calibration_governance_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_governance_checkpoint.md",
        technical_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "technical_checkpoint.md",
        reliable_visual_perception_path=PROJECT_ROOT / "examples" / "visual_signature" / "reliable_visual_perception.md",
    )
    json_path = Path(outputs["governance_integrity_report_json"])
    md_path = Path(outputs["governance_integrity_report_md"])
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["status"] == "valid"
    assert payload["readiness_scope"] == "broader_corpus_use"
    assert "Governance Integrity Check" in md_path.read_text(encoding="utf-8")


def test_missing_capability_referenced_by_runtime_matrix_fails(tmp_path: Path):
    capability_registry = tmp_path / "capability_registry.json"
    runtime_policy_matrix = tmp_path / "runtime_policy_matrix.json"
    calibration_readiness = tmp_path / "calibration_readiness.json"
    calibration_governance_checkpoint = tmp_path / "calibration_governance_checkpoint.md"
    technical_checkpoint = tmp_path / "technical_checkpoint.md"
    reliable_visual_perception = tmp_path / "reliable_visual_perception.md"

    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "capability_registry.json", capability_registry)
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "runtime_policy_matrix.json", runtime_policy_matrix)
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_readiness.json", calibration_readiness)
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_governance_checkpoint.md", calibration_governance_checkpoint)
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "technical_checkpoint.md", technical_checkpoint)
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "reliable_visual_perception.md", reliable_visual_perception)

    payload = json.loads(runtime_policy_matrix.read_text(encoding="utf-8"))
    payload["capabilities"][0]["capability_id"] = "missing_capability"
    runtime_policy_matrix.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = check_governance_integrity(
        capability_registry_path=capability_registry,
        runtime_policy_matrix_path=runtime_policy_matrix,
        calibration_readiness_path=calibration_readiness,
        calibration_governance_checkpoint_path=calibration_governance_checkpoint,
        technical_checkpoint_path=technical_checkpoint,
        reliable_visual_perception_path=reliable_visual_perception,
    )
    assert report["status"] == "invalid"
    assert report["error_count"] > 0
    assert any("unknown capability_id" in error.lower() for error in report["errors"])


def test_production_enabled_true_fails(tmp_path: Path):
    runtime_policy_matrix = _copy_runtime_policy_matrix(tmp_path)
    payload = json.loads(runtime_policy_matrix.read_text(encoding="utf-8"))
    payload["capabilities"][0]["production_enabled"] = True
    runtime_policy_matrix.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = _check_with_runtime_matrix(tmp_path, runtime_policy_matrix)
    assert report["status"] == "invalid"
    assert any("production enabled" in error.lower() for error in report["errors"])


def test_scoring_impact_true_fails(tmp_path: Path):
    runtime_policy_matrix = _copy_runtime_policy_matrix(tmp_path)
    payload = json.loads(runtime_policy_matrix.read_text(encoding="utf-8"))
    payload["capabilities"][0]["scope_policies"]["production_runtime"] = "allowed"
    payload["capabilities"][0]["scoring_impact"] = True
    runtime_policy_matrix.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = _check_with_runtime_matrix(tmp_path, runtime_policy_matrix)
    assert report["status"] == "invalid"
    assert any("scoring" in error.lower() for error in report["errors"])


def test_production_runtime_allowing_runtime_mutation_fails(tmp_path: Path):
    runtime_policy_matrix = _copy_runtime_policy_matrix(tmp_path)
    payload = json.loads(runtime_policy_matrix.read_text(encoding="utf-8"))
    payload["runtime_mutation_policy"]["scope_policies"]["production_runtime"] = "allowed"
    runtime_policy_matrix.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = _check_with_runtime_matrix(tmp_path, runtime_policy_matrix)
    assert report["status"] == "invalid"
    assert any("production_runtime must block runtime mutation" in error.lower() for error in report["errors"])


def test_prohibited_scope_allowed_fails(tmp_path: Path):
    runtime_policy_matrix = _copy_runtime_policy_matrix(tmp_path)
    payload = json.loads(runtime_policy_matrix.read_text(encoding="utf-8"))
    payload["capabilities"][0]["scope_policies"]["production_runtime"] = "allowed"
    runtime_policy_matrix.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = _check_with_runtime_matrix(tmp_path, runtime_policy_matrix)
    assert report["status"] == "invalid"
    assert any("runtime policy allows prohibited scope" in error.lower() for error in report["errors"])


def test_missing_doc_reference_warns_or_fails(tmp_path: Path):
    technical_checkpoint = tmp_path / "technical_checkpoint.md"
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "technical_checkpoint.md", technical_checkpoint)
    technical_checkpoint.write_text("placeholder without references\n", encoding="utf-8")

    report = check_governance_integrity(
        capability_registry_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "capability_registry.json",
        runtime_policy_matrix_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "runtime_policy_matrix.json",
        calibration_readiness_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_readiness.json",
        calibration_governance_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_governance_checkpoint.md",
        technical_checkpoint_path=technical_checkpoint,
        reliable_visual_perception_path=PROJECT_ROOT / "examples" / "visual_signature" / "reliable_visual_perception.md",
    )
    assert report["status"] == "valid"
    assert report["warning_count"] > 0
    assert any("runtime_policy_matrix" in warning.lower() or "capability_registry" in warning.lower() for warning in report["warnings"])


def test_invalid_readiness_scope_fails(tmp_path: Path):
    readiness_path = tmp_path / "calibration_readiness.json"
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_readiness.json", readiness_path)
    payload = json.loads(readiness_path.read_text(encoding="utf-8"))
    payload["readiness_scope"] = "provider_pilot_use"
    readiness_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = check_governance_integrity(
        capability_registry_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "capability_registry.json",
        runtime_policy_matrix_path=PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "runtime_policy_matrix.json",
        calibration_readiness_path=readiness_path,
        calibration_governance_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_governance_checkpoint.md",
        technical_checkpoint_path=PROJECT_ROOT / "examples" / "visual_signature" / "technical_checkpoint.md",
        reliable_visual_perception_path=PROJECT_ROOT / "examples" / "visual_signature" / "reliable_visual_perception.md",
    )
    assert report["status"] == "invalid"
    assert any("calibration readiness scope must be broader_corpus_use" in error.lower() for error in report["errors"])


def test_governance_integrity_script_writes_outputs(tmp_path: Path):
    script = _load_script(SCRIPT_PATH, "visual_signature_governance_integrity")
    output_root = tmp_path / "governance"

    assert script.main(["--output-root", str(output_root)]) == 0

    json_path = output_root / "governance_integrity_report.json"
    md_path = output_root / "governance_integrity_report.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["status"] == "valid"
    assert "Governance Integrity Check" in md_path.read_text(encoding="utf-8")


def _copy_runtime_policy_matrix(tmp_path: Path) -> Path:
    runtime_policy_matrix = tmp_path / "runtime_policy_matrix.json"
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "runtime_policy_matrix.json", runtime_policy_matrix)
    return runtime_policy_matrix


def _check_with_runtime_matrix(tmp_path: Path, runtime_policy_matrix: Path):
    capability_registry = tmp_path / "capability_registry.json"
    calibration_readiness = tmp_path / "calibration_readiness.json"
    calibration_governance_checkpoint = tmp_path / "calibration_governance_checkpoint.md"
    technical_checkpoint = tmp_path / "technical_checkpoint.md"
    reliable_visual_perception = tmp_path / "reliable_visual_perception.md"
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "governance" / "capability_registry.json", capability_registry)
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_readiness.json", calibration_readiness)
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "calibration" / "calibration_governance_checkpoint.md", calibration_governance_checkpoint)
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "technical_checkpoint.md", technical_checkpoint)
    shutil.copy2(PROJECT_ROOT / "examples" / "visual_signature" / "reliable_visual_perception.md", reliable_visual_perception)
    return check_governance_integrity(
        capability_registry_path=capability_registry,
        runtime_policy_matrix_path=runtime_policy_matrix,
        calibration_readiness_path=calibration_readiness,
        calibration_governance_checkpoint_path=calibration_governance_checkpoint,
        technical_checkpoint_path=technical_checkpoint,
        reliable_visual_perception_path=reliable_visual_perception,
    )
