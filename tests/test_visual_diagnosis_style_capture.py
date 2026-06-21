from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.visual_signature.capture.style_capture import extract_computed_style_snapshot_from_page


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "visual_diagnosis_capture_computed_styles.py"


class FakePage:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def evaluate(self, script, arg):
        self.calls.append((script, arg))
        return self.payload


def _load_script():
    spec = importlib.util.spec_from_file_location("visual_diagnosis_capture_computed_styles", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_computed_style_snapshot_from_page_normalizes_playwright_payload():
    page = FakePage(
        {
            "url": "https://example.com",
            "colors": ["rgb(0, 0, 0)", None, "#ffffff"],
            "elements": [
                {"tag": "body", "styles": {"fontFamily": "Inter"}},
                "invalid",
                {"tag": "h1", "styles": {"fontSize": "64px"}},
            ],
        }
    )

    snapshot = extract_computed_style_snapshot_from_page(page, max_elements=12)

    assert snapshot["schema_version"] == "computed-style-snapshot-v1"
    assert snapshot["url"] == "https://example.com"
    assert snapshot["colors"] == ["rgb(0, 0, 0)", "#ffffff"]
    assert snapshot["element_count"] == 2
    assert page.calls[0][1]["maxElements"] == 12


def test_capture_computed_styles_script_writes_manifest_with_paths(tmp_path, monkeypatch):
    module = _load_script()
    source_manifest = tmp_path / "manifest.json"
    source_manifest.write_text(
        json.dumps(
            {
                "brands": [
                    {"brand_name": "Example", "website_url": "https://example.com"},
                    {"brand_name": "Broken", "website_url": "https://broken.example"},
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_capture(url):
        if "broken" in url:
            raise RuntimeError("navigation failed")
        return {
            "schema_version": "computed-style-snapshot-v1",
            "url": url,
            "element_count": 3,
            "colors": ["#111111", "#ffffff"],
            "elements": [{"tag": "body"}],
        }

    monkeypatch.setattr(module, "capture_computed_style_snapshot", fake_capture)

    manifest = module.capture_manifest(source_manifest, output_root=tmp_path / "out")

    assert manifest["total"] == 2
    assert manifest["ok"] == 1
    assert manifest["error"] == 1
    first = manifest["results"][0]
    assert first["status"] == "captured"
    assert first["computed_style_snapshot_path"].endswith("example.computed-style.json")
    assert Path(first["computed_style_snapshot_path"]).exists()
    assert manifest["results"][1]["status"] == "failed"
