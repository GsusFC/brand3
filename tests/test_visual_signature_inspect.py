from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "visual_signature_inspect.py"
EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "visual_signature"


def _load_inspector():
    spec = importlib.util.spec_from_file_location("visual_signature_inspect", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_inspector_summarizes_saved_payload():
    inspector = _load_inspector()
    payload = inspector.load_payload(EXAMPLES_DIR / "strong_visual_system.json")

    output = inspector.inspect_payload(payload, label="strong")

    assert "== strong ==" in output
    assert "Interpretation status: interpretable" in output
    assert "Extraction confidence: 0.84 (high)" in output
    assert "palette preview:" in output
    assert "typography:" in output
    assert "layout:" in output
    assert "components:" in output
    assert "consistency:" in output


def test_inspector_detects_weak_or_missing_signals():
    inspector = _load_inspector()
    payload = inspector.load_payload(EXAMPLES_DIR / "weak_visual_system.json")

    weak = inspector.weak_signals(payload)

    assert "colors: missing primary signal" in weak
    assert "typography: missing primary signal" in weak
    assert "logo: missing primary signal" in weak
    assert "extraction limitation: screenshot_not_available" in weak


def test_inspector_compares_fixture_payloads():
    inspector = _load_inspector()
    paths = [
        EXAMPLES_DIR / "weak_visual_system.json",
        EXAMPLES_DIR / "strong_visual_system.json",
        EXAMPLES_DIR / "template_saas_system.json",
    ]
    named_payloads = [(path.stem, inspector.load_payload(path)) for path in paths]

    output = inspector.compare_payloads(named_payloads)

    assert "Visual Signature Comparison" in output
    assert "strong_visual_system | Strong System Co | interpretable | 0.84" in output
    assert "weak_visual_system | Weak Signals Ltd | interpretable | 0.21" in output


def test_inspector_excludes_not_interpretable_payload_from_weak_visual_signals():
    inspector = _load_inspector()
    payload = inspector.load_payload(EXAMPLES_DIR / "weak_visual_system.json")
    payload["interpretation_status"] = "not_interpretable"
    payload["acquisition"] = {
        "adapter": "firecrawl",
        "status_code": None,
        "warnings": [],
        "errors": ["fixture acquisition failure"],
    }

    weak = inspector.weak_signals(payload)
    output = inspector.inspect_payload(payload, label="failed")

    assert weak == []
    assert "Interpretation status: not_interpretable" in output
    assert "Acquisition failure:" in output
    assert "acquisition error: fixture acquisition failure" in output
    assert "Weak or missing signals:" not in output


def test_inspector_displays_vision_summary_when_present():
    inspector = _load_inspector()
    payload = inspector.load_payload(EXAMPLES_DIR / "strong_visual_system.json")
    payload["vision"] = {
        "screenshot": {
            "available": True,
            "quality": "usable",
            "capture_type": "viewport",
            "width": 1440,
            "height": 900,
            "viewport_width": 1440,
            "viewport_height": 900,
        },
        "screenshot_palette": {
            "dominant_colors": [
                {"hex": "#ffffff", "occurrences": 1200, "ratio": 0.5},
                {"hex": "#111111", "occurrences": 800, "ratio": 0.33},
            ],
            "confidence": 0.8,
        },
        "viewport_palette": {
            "dominant_colors": [
                {"hex": "#ffffff", "occurrences": 1200, "ratio": 0.5},
                {"hex": "#111111", "occurrences": 800, "ratio": 0.33},
            ],
            "confidence": 0.8,
        },
        "composition": {
            "visual_density": "balanced",
            "whitespace_ratio": 0.42,
            "composition_classification": "balanced_blocks",
        },
        "viewport_composition": {
            "visual_density": "sparse",
            "whitespace_ratio": 0.82,
            "composition_classification": "sparse_single_focus",
        },
        "vision_confidence": {"score": 0.76, "level": "high"},
        "viewport_confidence": {"score": 0.84, "level": "high"},
        "agreement": {
            "agreement_level": "medium",
            "disagreement_flags": ["dom_density_disagrees_with_viewport_first_fold"],
            "summary_notes": ["DOM suggests a denser page, but the viewport reads as spacious."],
        },
    }

    output = inspector.inspect_payload(payload, label="vision")

    assert "Vision summaries:" in output
    assert "screenshot: available=True; quality=usable; capture_type=viewport; dimensions=1440x900; viewport=1440x900" in output
    assert "screenshot palette: #ffffff[###] #111111[###]" in output
    assert "viewport palette: #ffffff[###] #111111[###]" in output
    assert "composition: density=balanced; whitespace=42%; classification=balanced_blocks" in output
    assert "viewport composition: density=sparse; whitespace=82%; classification=sparse_single_focus" in output
    assert "vision confidence: 0.76 (high)" in output
    assert "viewport confidence: 0.84 (high)" in output
    assert "agreement: medium; flags=dom_density_disagrees_with_viewport_first_fold" in output
    assert "agreement notes: DOM suggests a denser page, but the viewport reads as spacious." in output


def test_all_visual_signature_examples_are_valid_json():
    inspector = _load_inspector()
    expected_names = {
        "inconsistent_system.json",
        "strong_visual_system.json",
        "template_saas_system.json",
        "weak_visual_system.json",
    }
    payload_paths = sorted(EXAMPLES_DIR / name for name in expected_names)

    assert {path.name for path in payload_paths} == expected_names
    for path in payload_paths:
        payload = inspector.load_payload(path)
        assert payload["version"] == "visual-signature-mvp-1"
