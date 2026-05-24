from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.visual_signature.corpus_expansion import (
    build_reviewer_workflow_pilot,
    reviewer_workflow_pilot_markdown,
    validate_reviewer_workflow_pilot_payload,
    write_reviewer_workflow_pilot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_reviewer_workflow_pilot.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_reviewer_workflow_pilot_is_pending_only():
    payload = build_reviewer_workflow_pilot()
    assert validate_reviewer_workflow_pilot_payload(payload) == []
    assert payload["readiness_scope"] == "human_review_scaling"
    assert payload["pilot_status"] == "pending"
    assert payload["selected_review_queue_item_count"] == 2
    assert all(item["queue_state"] in {"queued", "needs_additional_evidence"} for item in payload["selected_review_queue_items"])
    assert all(item.get("review_outcome") is None for item in payload["selected_review_queue_items"])
    assert "No fake review decisions: yes" in reviewer_workflow_pilot_markdown(payload)


def test_reviewer_workflow_pilot_writes_artifacts(tmp_path: Path):
    outputs = write_reviewer_workflow_pilot(output_root=tmp_path)
    json_path = Path(outputs["reviewer_workflow_pilot_json"])
    md_path = Path(outputs["reviewer_workflow_pilot_md"])
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert validate_reviewer_workflow_pilot_payload(payload) == []
    assert "This pilot keeps all review decisions pending or queued." in md_path.read_text(encoding="utf-8")


def test_no_fake_completed_review_records_are_generated():
    payload = build_reviewer_workflow_pilot()
    assert payload["queue_state_distribution"].get("reviewed", 0) == 0
    assert all("reviewed_at" not in item or item["reviewed_at"] is None for item in payload["selected_review_queue_items"])
    assert all("reviewer_id" not in item or item["reviewer_id"] is None for item in payload["selected_review_queue_items"])


def test_invalid_selected_item_state_fails():
    payload = build_reviewer_workflow_pilot()
    payload["selected_review_queue_items"][0]["queue_state"] = "reviewed"
    errors = validate_reviewer_workflow_pilot_payload(payload)
    assert any("not pending" in error.lower() for error in errors)


def test_script_writes_outputs(tmp_path: Path):
    script = _load_script(SCRIPT_PATH, "visual_signature_reviewer_workflow_pilot")
    output_root = tmp_path / "pilot"
    assert script.main(["--output-root", str(output_root)]) == 0
    json_path = output_root / "reviewer_workflow_pilot.json"
    md_path = output_root / "reviewer_workflow_pilot.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert validate_reviewer_workflow_pilot_payload(payload) == []
