from __future__ import annotations

import json
from pathlib import Path

from scripts.visual_interpretation_lab import build_visual_evidence_pack, run_lab
from src.visual_signature.interpretation.gemini import GeminiVisionClient
from src.visual_signature.interpretation.models import VisualInterpretation
from src.visual_signature.interpretation.validation import validate_visual_interpretation


def test_visual_evidence_pack_requires_real_screenshot(tmp_path: Path):
    row = {
        "brand_name": "Missing Shot",
        "website_url": "https://missing.example",
        "category_hint": "developer saas",
        "screenshot_capture": {"screenshot_url": "file://missing.png", "quality": "usable"},
    }

    pack = build_visual_evidence_pack(row)

    assert pack.schema_version == "visual-evidence-pack-v1"
    assert pack.status == "not_evaluable"
    assert pack.capture_quality == "missing"
    assert pack.screenshot_available is False
    assert "screenshot_missing" in pack.limitations


def test_validator_blocks_usable_result_for_not_evaluable_pack(tmp_path: Path):
    pack = build_visual_evidence_pack(
        {
            "brand_name": "Blocked",
            "website_url": "https://blocked.example",
            "screenshot_capture": {"screenshot_url": "file://missing.png", "quality": "blocked"},
        }
    )
    interpretation = VisualInterpretation(
        brand_name="Blocked",
        website_url="https://blocked.example",
        status="usable",
        confidence="medium",
        visual_positioning="Looks visually clear.",
    )

    validation = validate_visual_interpretation(pack, interpretation)

    assert validation.valid is False
    assert "not_evaluable_pack_must_not_return_usable_interpretation" in validation.errors
    assert "not_evaluable_pack_must_return_low_confidence" in validation.errors


def test_validator_rejects_missing_identity_fields(tmp_path: Path):
    screenshot = tmp_path / "shot.png"
    screenshot.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    pack = build_visual_evidence_pack(
        {
            "brand_name": "Example",
            "website_url": "https://example.com",
            "screenshot_capture": {"screenshot_url": str(screenshot), "quality": "usable"},
        }
    )
    interpretation = VisualInterpretation(
        brand_name="",
        website_url="",
        status="not_evaluable",
        confidence="low",
    )

    validation = validate_visual_interpretation(pack, interpretation)

    assert validation.valid is False
    assert "brand_name_missing" in validation.errors
    assert "website_url_missing" in validation.errors


def test_gemini_request_embeds_local_screenshot(tmp_path: Path):
    screenshot = tmp_path / "shot.png"
    screenshot.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    pack = build_visual_evidence_pack(
        {
            "brand_name": "Image Brand",
            "website_url": "https://image.example",
            "screenshot_capture": {"screenshot_url": str(screenshot), "quality": "usable"},
        }
    )
    client = GeminiVisionClient(api_key="test-key", model="gemini-2.5-flash")

    request = client.build_request(pack, system_prompt="system", user_prompt="user")

    parts = request["contents"][0]["parts"]
    assert parts[0]["text"] == "user"
    assert parts[1]["inlineData"]["mimeType"] == "image/png"
    assert parts[1]["inlineData"]["data"]
    assert request["generationConfig"]["responseMimeType"] == "application/json"


def test_visual_interpretation_lab_dry_run_writes_outputs(tmp_path: Path):
    screenshot = tmp_path / "linear.png"
    screenshot.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "brands": [
                    {
                        "brand_name": "Linear",
                        "website_url": "https://linear.app",
                        "category_hint": "developer saas infrastructure",
                        "screenshot_capture": {"screenshot_url": str(screenshot), "quality": "usable"},
                        "visual_signature": {"colors": {"dominant_colors": ["#000000"]}},
                        "human_review": {"identity_read_fit": "partial"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_lab(manifest, output_root=tmp_path / "out")
    output_dir = Path(result["output_dir"])

    assert (output_dir / "summary.json").exists()
    assert (output_dir / "summary.md").exists()
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["mode"] == "dry_run"
    assert summary["metrics"]["total"] == 1
    assert summary["metrics"]["valid"] == 1
    assert summary["results"][0]["interpretation"]["status"] == "usable"
