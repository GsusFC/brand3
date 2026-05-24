from __future__ import annotations

import importlib.util
import shutil
import json
import re
import subprocess
import sys
from pathlib import Path

from src.visual_signature.corpus_expansion import (
    build_reviewer_viewer_bundle,
    validate_reviewer_viewer_bundle,
    write_reviewer_viewer_bundle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_reviewer_viewer.py"
PACKETS_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "reviewer_packets"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_reviewer_viewer_bundle_writes_static_bundle(tmp_path: Path) -> None:
    viewer_root = tmp_path / "viewer"
    outputs = write_reviewer_viewer_bundle(output_root=viewer_root, packets_root=PACKETS_ROOT)

    assert Path(outputs["viewer_index_html"]).exists()
    assert Path(outputs["viewer_css"]).exists()
    assert Path(outputs["viewer_js"]).exists()
    assert not (viewer_root / "viewer_data.json").exists()
    assert validate_reviewer_viewer_bundle(viewer_root=viewer_root, packets_root=PACKETS_ROOT) == []

    html = (viewer_root / "index.html").read_text(encoding="utf-8")
    css = (viewer_root / "viewer.css").read_text(encoding="utf-8")
    js = (viewer_root / "viewer.js").read_text(encoding="utf-8")
    match = re.search(r'<script id="viewer-data" type="application/json">(.*?)</script>', html, re.S)
    assert match is not None
    payload = json.loads(match.group(1))
    assert '<script id="viewer-data" type="application/json">' in html
    assert "queue_allbirds" in html
    assert "queue_headspace" in html
    assert "Visual Signature Reviewer Viewer" in html
    assert "Visible fallback panel." in html
    assert "Advanced evidence" not in html
    assert "Raw JSON" not in html
    assert "Debug diagnostics" not in html
    assert "Advanced evidence" in js
    assert "Raw JSON" in js
    assert "Debug diagnostics" in js
    assert "term-head" in html
    assert '<details class="details-panel" open>' not in html
    assert "Reviewer decision undefined" not in html
    assert payload["readiness_scope"] == "human_review_scaling"
    assert payload["packets"][0]["queue_id"] == "queue_allbirds"
    assert "packet_markdown_path" in payload["packets"][0]
    assert "packet_markdown" not in payload["packets"][0]
    assert ".queue-strip" in css
    assert ".sidebar" not in css
    assert "#eeeeee" in css
    assert "#f5f5f5" in css
    assert "#ef490d" in css
    assert "width: min(1440px" in css
    assert "grid-template-columns: minmax(0, 1fr) 340px" in css
    assert "box-shadow: 0 10px 32px" in css
    assert ".viewer-workspace" in css
    assert ".footer" in css
    assert "JetBrains Mono" in css
    assert "IBM Plex Mono" not in css
    assert "SFMono-Regular" not in css
    assert "local draft stored" in js
    assert "viewer-error" in js
    assert "Screenshot unavailable." in js
    assert "fetch(" not in js
    assert "localStorage" not in js

    payload = build_reviewer_viewer_bundle(output_root=viewer_root, packets_root=PACKETS_ROOT)
    assert payload["packet_count"] == 2
    assert payload["selected_review_queue_item_ids"] == ["queue_allbirds", "queue_headspace"]
    assert payload["packets"][0]["screenshot_paths"][0].startswith("..")
    assert payload["packets"][0]["packet_markdown_path"].startswith("..")
    assert "packet_markdown" not in payload["packets"][0]


def test_missing_packet_file_fails_validation(tmp_path: Path) -> None:
    viewer_root = tmp_path / "viewer"
    packets_root = tmp_path / "reviewer_packets"
    shutil.copytree(PACKETS_ROOT, packets_root)
    write_reviewer_viewer_bundle(output_root=viewer_root, packets_root=packets_root)
    (packets_root / "headspace.md").unlink()

    errors = validate_reviewer_viewer_bundle(viewer_root=viewer_root, packets_root=packets_root)

    assert any("missing reviewer packet" in error.lower() or "missing packet markdown" in error.lower() for error in errors)


def test_viewer_js_has_no_syntax_breaking_template_issues(tmp_path: Path) -> None:
    viewer_root = tmp_path / "viewer"
    write_reviewer_viewer_bundle(output_root=viewer_root, packets_root=PACKETS_ROOT)
    result = subprocess.run(
        ["node", "--check", str(viewer_root / "viewer.js")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_script_writes_static_viewer(tmp_path: Path) -> None:
    script = _load_script(SCRIPT_PATH, "visual_signature_reviewer_viewer")
    output_root = tmp_path / "viewer"

    assert script.main(["--output-root", str(output_root)]) == 0
    assert (output_root / "index.html").exists()
    assert (output_root / "viewer.css").exists()
    assert (output_root / "viewer.js").exists()
    assert not (output_root / "viewer_data.json").exists()
    html = (output_root / "index.html").read_text(encoding="utf-8")
    js = (output_root / "viewer.js").read_text(encoding="utf-8")
    assert "Visible fallback panel." in html
    assert "Advanced evidence" not in html
    assert "Raw JSON" not in html
    assert "Debug diagnostics" not in html
    assert "Advanced evidence" in js
    assert "Raw JSON" in js
    assert "Debug diagnostics" in js
    assert "term-head" in html
    assert '<details class="details-panel" open>' not in html
    assert "Reviewer decision undefined" not in html
    assert validate_reviewer_viewer_bundle(viewer_root=output_root) == []
