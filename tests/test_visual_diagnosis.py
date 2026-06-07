from __future__ import annotations

import json

from scripts.visual_diagnosis_lab import run_lab
from src.visual_diagnosis import build_visual_diagnosis


def _visual_signature_payload() -> dict:
    return {
        "brand_name": "Example",
        "website_url": "https://example.com",
        "interpretation_status": "interpretable",
        "assets": {"screenshot_available": True, "image_count": 2},
        "layout": {
            "has_navigation": True,
            "has_hero": True,
            "visual_density": "balanced",
            "layout_patterns": ["grid"],
        },
        "logo": {"logo_detected": True},
        "components": {
            "primary_ctas": ["Start"],
            "components": [
                {"type": "card", "count": 4},
                {"type": "cta", "count": 1},
            ],
        },
        "colors": {
            "dominant_colors": ["#ffffff", "#111111"],
            "accent_candidates": ["#7755ff"],
        },
        "typography": {"heading_scale": "moderate"},
        "consistency": {"overall_consistency": 0.78},
        "extraction_confidence": {"score": 0.72, "level": "medium", "limitations": []},
        "semantics": {
            "status": "detected",
            "data": {
                "visual_polish_score": 7,
                "visual_coherence": "not_detected",
            },
        },
        "vision": {
            "screenshot": {
                "available": True,
                "capture_type": "viewport",
                "quality": "usable",
            },
            "viewport_obstruction": {"present": False, "type": "none"},
        },
    }


def test_visual_diagnosis_marks_missing_capture_as_not_evaluable():
    diagnosis = build_visual_diagnosis(
        brand_name="Missing",
        website_url="https://missing.example",
        visual_signature_payload={},
    )

    payload = diagnosis.to_dict()
    assert payload["schema_version"] == "visual-diagnosis-v1"
    assert payload["status"] == "unavailable"
    assert payload["diagnosis"]["identity_read"] == "not_evaluable"
    assert "capture_not_evaluable" in payload["signals"]["antipatterns"]
    assert "visual_evidence_not_evaluable" in payload["limitations"]


def test_visual_diagnosis_detects_template_saas_from_cards_and_cta():
    diagnosis = build_visual_diagnosis(
        brand_name="Example",
        website_url="https://example.com",
        screenshot_capture={"screenshot_url": "file:///tmp/example.png", "capture_type": "viewport"},
        visual_signature_payload=_visual_signature_payload(),
        coherence_breakdown={"visual_identity": 82},
    )

    payload = diagnosis.to_dict()
    assert payload["status"] == "usable"
    assert payload["capture"]["quality"] == "good"
    assert payload["diagnosis"]["reference_profile"] == "template_saas"
    assert payload["diagnosis"]["identity_read"] == "coherent_but_generic"
    assert payload["diagnosis"]["template_likeness"] == "high"
    assert "template_saas_layout" in payload["signals"]["antipatterns"]
    assert "card_heavy_composition" in payload["signals"]["antipatterns"]
    assert "raw_inputs:screenshot_capture" in payload["evidence_refs"]


def test_visual_diagnosis_category_hint_can_select_developer_first():
    payload = _visual_signature_payload()
    payload["components"]["components"] = [{"type": "cta", "count": 1}]
    diagnosis = build_visual_diagnosis(
        brand_name="API Co",
        website_url="https://api.example",
        screenshot_capture={"screenshot_url": "file:///tmp/api.png", "capture_type": "viewport"},
        visual_signature_payload=payload,
        coherence_breakdown={"visual_identity": 88},
        category_hint="developer infrastructure",
    )

    result = diagnosis.to_dict()
    assert result["diagnosis"]["reference_profile"] == "developer_first"
    assert result["diagnosis"]["identity_read"] == "functionally_clear"
    assert result["diagnosis"]["brand_fit"] == "high"


def test_visual_diagnosis_does_not_classify_retail_as_ai_native():
    diagnosis = build_visual_diagnosis(
        brand_name="Retail Co",
        website_url="https://retail.example",
        screenshot_capture={"screenshot_url": "file:///tmp/retail.png", "capture_type": "viewport"},
        visual_signature_payload=_visual_signature_payload(),
        coherence_breakdown={"visual_identity": 76},
        category_hint="ecommerce retail",
    )

    result = diagnosis.to_dict()
    assert result["diagnosis"]["reference_profile"] == "ecommerce_mass_market"
    assert result["diagnosis"]["identity_read"] == "commerce_clear"


def test_visual_diagnosis_lab_writes_summary(tmp_path):
    visual_path = tmp_path / "visual.json"
    visual_path.write_text(json.dumps(_visual_signature_payload()), encoding="utf-8")
    coherence_path = tmp_path / "coherence.json"
    coherence_path.write_text(json.dumps({"visual_identity": 82}), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "brands": [
                    {
                        "brand_name": "Example",
                        "website_url": "https://example.com",
                        "category_hint": "saas",
                        "visual_signature_path": str(visual_path),
                        "coherence_breakdown_path": str(coherence_path),
                        "screenshot_capture": {
                            "screenshot_url": "file:///tmp/example.png",
                            "capture_type": "viewport",
                            "quality": "usable",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_lab(manifest_path, output_root=tmp_path / "out")

    output_dir = tmp_path / "out"
    assert result["summary"]["brand_count"] == 1
    assert list(output_dir.glob("*/summary.json"))
    assert list(output_dir.glob("*/summary.md"))
    assert result["summary"]["results"][0]["diagnosis"]["evidence_refs"][0] == "raw_inputs:screenshot_capture"


def test_visual_diagnosis_suppresses_stale_screenshot_limitation_when_capture_exists():
    payload = _visual_signature_payload()
    payload["vision"] = {}
    payload["extraction_confidence"]["limitations"] = ["screenshot_not_available"]

    diagnosis = build_visual_diagnosis(
        brand_name="Example",
        website_url="https://example.com",
        screenshot_capture={
            "screenshot_url": "file:///tmp/example.png",
            "capture_type": "viewport",
            "quality": "usable",
        },
        visual_signature_payload=payload,
        coherence_breakdown={"visual_identity": 82},
    )

    result = diagnosis.to_dict()
    assert result["capture"]["quality"] == "good"
    assert "screenshot_not_available" not in result["limitations"]


def test_visual_diagnosis_requires_interpretable_visual_analysis_even_with_screenshot():
    payload = _visual_signature_payload()
    payload["interpretation_status"] = "not_interpretable"
    payload["extraction_confidence"]["score"] = 0.0
    payload["vision"] = {}

    diagnosis = build_visual_diagnosis(
        brand_name="Blocked",
        website_url="https://blocked.example",
        screenshot_capture={
            "screenshot_url": "file:///tmp/blocked.png",
            "capture_type": "viewport",
            "quality": "usable",
        },
        visual_signature_payload=payload,
        coherence_breakdown={},
        category_hint="premium luxury",
    )

    result = diagnosis.to_dict()
    assert result["status"] == "unavailable"
    assert result["diagnosis"]["identity_read"] == "not_evaluable"
    assert "visual_analysis_not_interpretable" in result["limitations"]
