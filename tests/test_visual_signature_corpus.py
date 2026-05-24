from __future__ import annotations

from pathlib import Path

from src.visual_signature.corpus import (
    REQUIRED_CATEGORIES,
    baseline_eligibility,
    load_category_seed,
    load_corpus_manifest,
    validate_category_seed,
    validate_corpus_manifest,
)


CORPUS_ROOT = Path(__file__).resolve().parents[1] / "examples" / "visual_signature" / "calibration_corpus"


def _eligible_payload() -> dict:
    return {
        "brand_name": "Eligible",
        "website_url": "https://eligible.example",
        "interpretation_status": "interpretable",
        "acquisition": {"errors": [], "status_code": 200},
        "colors": {"confidence": 0.8},
        "typography": {"confidence": 0.8},
        "logo": {"confidence": 0.8},
        "layout": {"confidence": 0.8},
        "components": {"confidence": 0.8},
        "assets": {"confidence": 0.8},
        "consistency": {"confidence": 0.8},
        "vision": {
            "screenshot": {
                "available": True,
                "quality": "usable",
                "capture_type": "viewport",
                "viewport_width": 1440,
                "viewport_height": 900,
            },
            "viewport_composition": {
                "visual_density": "balanced",
                "composition_classification": "balanced_blocks",
                "whitespace_ratio": 0.4,
            },
            "viewport_palette": {
                "color_count": 4,
                "dominant_colors": [{"hex": "#ffffff"}],
            },
            "viewport_confidence": {"score": 0.82, "level": "high"},
            "agreement": {"agreement_level": "high", "disagreement_flags": [], "summary_notes": []},
            "viewport_obstruction": {
                "present": False,
                "type": "none",
                "severity": "none",
                "coverage_ratio": 0.0,
                "first_impression_valid": True,
                "confidence": 0.0,
                "signals": [],
                "limitations": [],
            },
        },
    }


def test_corpus_manifest_schema_is_valid():
    manifest = load_corpus_manifest(CORPUS_ROOT / "corpus_manifest.json")

    result = validate_corpus_manifest(manifest)

    assert result.valid, result.to_dict()
    assert {item["slug"] for item in manifest["categories"]} == REQUIRED_CATEGORIES
    assert manifest["no_scoring_boundary"]["modifies_scoring"] is False
    assert manifest["no_scoring_boundary"]["modifies_rubric_dimensions"] is False
    assert manifest["no_scoring_boundary"]["modifies_production_reports"] is False
    assert manifest["no_scoring_boundary"]["modifies_production_ui"] is False


def test_category_seed_files_load_and_validate():
    paths = sorted((CORPUS_ROOT / "categories").glob("*.json"))

    assert {path.stem for path in paths} == REQUIRED_CATEGORIES
    for path in paths:
        seed = load_category_seed(path)
        result = validate_category_seed(seed)
        assert result.valid, {path.name: result.to_dict()}
        assert 12 <= len(seed["records"]) <= 15
        maturity = {record["design_maturity_label"] for record in seed["records"]}
        fame = {record["brand_fame_level"] for record in seed["records"]}
        assert "low" in maturity
        assert "medium" in maturity
        assert "high" in maturity
        assert "low" in fame
        for record in seed["records"]:
            assert record["baseline_eligible"] is False
            assert record["brand_name"]
            assert record["website_url"].startswith("https://")
            assert record["category"] == seed["category"]
            assert record["subcategory"]
            assert record["selection_reason"]
            assert record["brand_fame_level"] in {"low", "medium", "high"}
            assert record["design_maturity_label"] in {"low", "medium", "high"}


def test_baseline_eligibility_true_for_complete_viewport_payload():
    result = baseline_eligibility(_eligible_payload())

    assert result["baseline_eligible"] is True
    assert result["failures"] == []
    assert result["signal_coverage"] == 1.0


def test_baseline_eligibility_false_for_failed_or_incomplete_payload():
    payload = _eligible_payload()
    payload["interpretation_status"] = "not_interpretable"
    payload["acquisition"]["errors"] = ["fixture acquisition failure"]
    payload["vision"]["screenshot"]["available"] = False

    result = baseline_eligibility(payload)

    assert result["baseline_eligible"] is False
    assert "interpretation_status_not_interpretable" in result["failures"]
    assert "acquisition_errors_present" in result["failures"]
    assert "viewport_screenshot_missing" in result["failures"]


def test_baseline_eligibility_false_for_invalid_first_impression_obstruction():
    payload = _eligible_payload()
    payload["vision"]["viewport_obstruction"] = {
        "present": True,
        "type": "cookie_modal",
        "severity": "major",
        "coverage_ratio": 0.55,
        "first_impression_valid": False,
    }

    result = baseline_eligibility(payload)

    assert result["baseline_eligible"] is False
    assert "viewport_first_impression_obstructed" in result["failures"]


def test_category_seeds_do_not_require_binary_screenshots():
    for path in sorted((CORPUS_ROOT / "categories").glob("*.json")):
        seed = load_category_seed(path)
        for record in seed["records"]:
            assert "capture" not in record
            assert "evidence" not in record


def test_captured_screenshots_are_viewport_pngs_when_present():
    screenshot_files = [
        path
        for path in (CORPUS_ROOT / "screenshots").rglob("*")
        if path.is_file()
    ]

    assert screenshot_files
    binary_screenshots = [path for path in screenshot_files if path.name != ".gitkeep"]
    assert binary_screenshots
    assert all(path.suffix == ".png" for path in binary_screenshots)
    assert all("viewport" in path.relative_to(CORPUS_ROOT).parts for path in binary_screenshots)
