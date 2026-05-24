from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.visual_signature.governance import (
    build_three_track_validation_plan,
    three_track_validation_plan_markdown,
    validate_three_track_validation_plan_payload,
    write_three_track_validation_plan,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_three_track_validation_plan.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_current_plan_is_valid():
    payload = build_three_track_validation_plan()
    assert validate_three_track_validation_plan_payload(payload) == []
    assert payload["recommended_order"] == [
        "reviewer_workflow_validation",
        "corpus_real_validation",
        "provider_pilot_validation",
    ]
    assert {track["readiness_scope"] for track in payload["tracks"]} == {
        "human_review_scaling",
        "broader_corpus_use",
        "provider_pilot_use",
    }
    markdown = three_track_validation_plan_markdown(payload)
    assert "Visual Signature Three-Track Validation Plan" in markdown
    assert "No track implies production readiness." in markdown


def test_plan_is_written(tmp_path: Path):
    outputs = write_three_track_validation_plan(output_root=tmp_path)
    json_path = Path(outputs["three_track_validation_plan_json"])
    md_path = Path(outputs["three_track_validation_plan_md"])
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["record_type"] == "three_track_validation_plan"
    assert payload["recommended_order"] == [
        "reviewer_workflow_validation",
        "corpus_real_validation",
        "provider_pilot_validation",
    ]
    assert "No track implies production readiness." in md_path.read_text(encoding="utf-8")


def test_duplicate_track_ids_fail():
    payload = build_three_track_validation_plan()
    payload["tracks"][1]["track_id"] = "reviewer_workflow_validation"
    errors = validate_three_track_validation_plan_payload(payload)
    assert any("unique" in error.lower() for error in errors)


def test_invalid_readiness_scope_fails():
    payload = build_three_track_validation_plan()
    payload["tracks"][0]["readiness_scope"] = "invalid_scope"
    errors = validate_three_track_validation_plan_payload(payload)
    assert any("invalid readiness scope" in error.lower() for error in errors)


def test_recommended_order_mismatch_fails():
    payload = build_three_track_validation_plan()
    payload["recommended_order"] = [
        "corpus_real_validation",
        "reviewer_workflow_validation",
        "provider_pilot_validation",
    ]
    errors = validate_three_track_validation_plan_payload(payload)
    assert any("recommended_order must match" in error.lower() for error in errors)


def test_script_writes_outputs(tmp_path: Path):
    script = _load_script(SCRIPT_PATH, "visual_signature_three_track_validation_plan")
    output_root = tmp_path / "governance"
    assert script.main(["--output-root", str(output_root)]) == 0
    json_path = output_root / "three_track_validation_plan.json"
    md_path = output_root / "three_track_validation_plan.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert validate_three_track_validation_plan_payload(payload) == []
    assert "No track implies production readiness." in md_path.read_text(encoding="utf-8")


def test_current_plan_matches_recommendation():
    payload = build_three_track_validation_plan()
    assert payload["global_constraints"]
    assert payload["current_state_implications"]
    assert payload["tracks"][0]["readiness_scope"] == "human_review_scaling"
    assert payload["tracks"][1]["readiness_scope"] == "broader_corpus_use"
    assert payload["tracks"][2]["readiness_scope"] == "provider_pilot_use"
