from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from src.visual_signature.platform import (
    build_platform_bundle,
    validate_platform_bundle,
    write_platform_bundle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_platform.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_platform_bundle_discovers_expected_sections_and_artifacts(tmp_path: Path) -> None:
    output_root = tmp_path / "platform"
    outputs = write_platform_bundle(output_root=output_root)

    assert Path(outputs["platform_index_html"]).exists()
    assert Path(outputs["platform_css"]).exists()
    assert Path(outputs["platform_js"]).exists()
    assert validate_platform_bundle(platform_root=output_root) == []

    html = (output_root / "index.html").read_text(encoding="utf-8")
    css = (output_root / "platform.css").read_text(encoding="utf-8")
    js = (output_root / "platform.js").read_text(encoding="utf-8")
    payload = _embedded_payload(html)
    section_titles = {section["title"] for section in payload["sections"]}
    artifact_keys = {artifact["key"] for artifact in payload["artifacts"]}

    assert section_titles == {
        "Brand3 Overview",
        "Initial Scoring",
        "Visual Signature",
        "Captures",
        "Reviewer Workflow",
        "Calibration",
        "Governance",
        "Corpus Expansion",
    }
    assert payload["platform_status"] == "ready"
    assert "scoring_output_root" in artifact_keys
    assert "scoring_reports_root" in artifact_keys
    assert "scoring_dimensions_source" in artifact_keys
    assert "capture_manifest" in artifact_keys
    assert "reviewer_viewer" in artifact_keys
    assert "calibration_readiness" in artifact_keys
    assert "runtime_policy_matrix" in artifact_keys
    assert "pilot_metrics" in artifact_keys
    assert all(artifact["exists"] for artifact in payload["artifacts"] if artifact["required"])
    assert "platform-data" in html
    assert "Brand3 Platform" in html
    assert "no scoring logic changes" in html
    assert "Brand3 Overview" in html
    assert "Initial Scoring" in html
    assert "Visual Signature" in html
    assert "Captures" in html
    assert "Reviewer Workflow" in html
    assert "Calibration" in html
    assert "Governance" in html
    assert "Corpus Expansion" in html
    assert "fetch(" not in js
    assert "localStorage" not in js
    assert ".left-nav" in css
    assert "JetBrains Mono" in css


def test_platform_js_has_no_syntax_errors(tmp_path: Path) -> None:
    output_root = tmp_path / "platform"
    write_platform_bundle(output_root=output_root)

    result = subprocess.run(
        ["node", "--check", str(output_root / "platform.js")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_platform_renders_when_optional_artifacts_are_missing(tmp_path: Path) -> None:
    visual_root = tmp_path / "visual_signature"
    scoring_root = tmp_path / "missing_scoring_output"
    _write_minimal_required_artifacts(visual_root)
    output_root = visual_root / "platform"

    write_platform_bundle(output_root=output_root, visual_signature_root=visual_root, scoring_output_root=scoring_root)
    errors = validate_platform_bundle(platform_root=output_root, visual_signature_root=visual_root, scoring_output_root=scoring_root)
    payload = build_platform_bundle(output_root=output_root, visual_signature_root=visual_root, scoring_output_root=scoring_root)

    assert errors == []
    assert payload["platform_status"] == "ready"
    assert any(not artifact["exists"] and not artifact["required"] for artifact in payload["artifacts"])
    initial_scoring = next(section for section in payload["sections"] if section["title"] == "Initial Scoring")
    assert initial_scoring["status"] == "missing_artifacts"
    assert (output_root / "index.html").exists()
    assert "Brand3 Platform" in (output_root / "index.html").read_text(encoding="utf-8")


def test_script_writes_platform(tmp_path: Path) -> None:
    script = _load_script(SCRIPT_PATH, "visual_signature_platform")
    output_root = tmp_path / "platform"

    assert script.main(["--output-root", str(output_root)]) == 0
    assert (output_root / "index.html").exists()
    assert (output_root / "platform.css").exists()
    assert (output_root / "platform.js").exists()
    assert validate_platform_bundle(platform_root=output_root) == []


def _embedded_payload(html: str) -> dict:
    marker = '<script id="platform-data" type="application/json">'
    start = html.index(marker) + len(marker)
    end = html.index("</script>", start)
    return json.loads(html[start:end])


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_text(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_minimal_required_artifacts(root: Path) -> None:
    _write_json(
        root / "screenshots" / "capture_manifest.json",
        {"total": 1, "ok": 1, "error": 0, "results": [{"brand_name": "Example", "capture_id": "example"}]},
    )
    _write_json(root / "screenshots" / "dismissal_audit.json", {"status": "valid", "results": []})
    _write_json(
        root / "corpus_expansion" / "review_queue.json",
        {
            "readiness_status": "not_ready",
            "queue_state_distribution": {"queued": 1},
            "queue_items": [{"queue_id": "queue_example", "brand_name": "Example", "capture_id": "example", "queue_state": "queued"}],
        },
    )
    _write_json(
        root / "corpus_expansion" / "reviewer_workflow_pilot.json",
        {
            "pilot_status": "pending",
            "selected_review_queue_item_ids": ["queue_example"],
            "selected_review_queue_item_count": 1,
        },
    )
    _write_text(root / "corpus_expansion" / "reviewer_viewer" / "index.html", "<!doctype html>")
    _write_json(root / "calibration" / "calibration_manifest.json", {"validation_status": "valid", "record_count": 1})
    _write_json(root / "calibration" / "calibration_records.json", {"record_count": 1})
    _write_json(root / "calibration" / "calibration_summary.json", {"record_count": 1, "reviewed_claims": 1})
    _write_json(root / "calibration" / "calibration_readiness.json", {"status": "not_ready", "bundle_valid": True})
    _write_json(root / "governance" / "capability_registry.json", {"capability_count": 0, "capabilities": []})
    _write_json(root / "governance" / "runtime_policy_matrix.json", {"policy_count": 0, "capability_count": 0})
    _write_json(root / "governance" / "governance_integrity_report.json", {"status": "valid", "error_count": 0, "warning_count": 0})
    _write_json(root / "governance" / "three_track_validation_plan.json", {"recommended_order": [], "global_constraints": []})
    _write_json(
        root / "corpus_expansion" / "corpus_expansion_manifest.json",
        {"readiness_status": "not_ready", "current_capture_count": 1, "target_capture_count": 20},
    )
    _write_json(root / "corpus_expansion" / "pilot_metrics.json", {"readiness_status": "not_ready"})
