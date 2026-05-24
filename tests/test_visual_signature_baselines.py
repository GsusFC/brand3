from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.visual_signature.baselines import (
    build_category_baselines,
    compare_records_to_baselines,
    metric_row_from_payload,
)


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "visual_signature_build_baselines.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("visual_signature_build_baselines", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload(
    brand_name: str,
    category: str,
    *,
    whitespace: float,
    density: str = "balanced",
    composition: str = "balanced_blocks",
    palette_count: int = 4,
    agreement: str = "high",
    ctas: int = 2,
    components: int = 6,
    fonts: int = 2,
    interpretation_status: str = "interpretable",
) -> dict:
    return {
        "brand_name": brand_name,
        "website_url": f"https://{brand_name.lower().replace(' ', '-')}.example",
        "version": "visual-signature-mvp-1",
        "interpretation_status": interpretation_status,
        "calibration": {"expected_category": category},
        "colors": {
            "palette": [{"hex": f"#{index:06x}"} for index in range(palette_count)],
            "confidence": 0.8,
        },
        "typography": {
            "font_families": [{"family": f"Font {index}"} for index in range(fonts)],
            "size_samples_px": [16, 24, 32],
            "weight_range": {"min": 400, "max": 700},
            "confidence": 0.8,
        },
        "logo": {"logo_detected": True, "confidence": 0.8},
        "layout": {"visual_density": density, "confidence": 0.8},
        "components": {
            "primary_ctas": [f"CTA {index}" for index in range(ctas)],
            "components": [{"type": "cta", "count": ctas}, {"type": "card", "count": components}],
            "confidence": 0.8,
        },
        "assets": {"screenshot_available": True, "confidence": 0.8},
        "consistency": {"overall_consistency": 0.8, "confidence": 0.8},
        "extraction_confidence": {"score": 0.8, "level": "high"},
        "vision": {
            "viewport_whitespace_ratio": whitespace,
            "viewport_visual_density": density,
            "viewport_palette": {
                "color_count": palette_count,
                "dominant_colors": [{"hex": f"#{index:06x}"} for index in range(palette_count)],
            },
            "viewport_composition": {
                "whitespace_ratio": whitespace,
                "visual_density": density,
                "composition_classification": composition,
            },
            "viewport_confidence": {"score": 0.82, "level": "high"},
            "agreement": {
                "agreement_level": agreement,
                "disagreement_flags": [],
                "summary_notes": [],
            },
        },
    }


def test_metric_row_extracts_required_visual_signature_baseline_metrics():
    row = metric_row_from_payload(_payload("Linear", "SaaS", whitespace=0.2), source_path="/tmp/linear.json")

    assert row.category == "SaaS"
    assert row.brand_name == "Linear"
    assert row.viewport_whitespace == 0.2
    assert row.viewport_whitespace_band == "low"
    assert row.viewport_density == "balanced"
    assert row.viewport_density_score == 0.55
    assert row.viewport_composition == "balanced_blocks"
    assert row.palette_complexity is not None
    assert row.dom_viewport_agreement_level == "high"
    assert row.dom_viewport_agreement_score == 1.0
    assert row.cta_density is not None
    assert row.visible_cta_weight is not None
    assert row.component_density is not None
    assert row.typography_complexity is not None
    assert row.extraction_confidence == 0.8
    assert row.vision_confidence == 0.82
    assert row.signal_availability == 1.0
    assert row.signal_usability == 0.8
    assert row.signal_coverage == 0.87


def test_build_category_baseline_excludes_not_interpretable_from_averages():
    rows = [
        metric_row_from_payload(_payload("A", "SaaS", whitespace=0.2)),
        metric_row_from_payload(_payload("B", "SaaS", whitespace=0.4)),
        metric_row_from_payload(_payload("C", "SaaS", whitespace=0.6)),
        metric_row_from_payload(
            _payload("Failed", "SaaS", whitespace=0.99, interpretation_status="not_interpretable")
        ),
    ]

    baseline = build_category_baselines(rows)["SaaS"]

    assert baseline.sample_count == 4
    assert baseline.interpretable_count == 3
    assert baseline.not_interpretable_count == 1
    assert baseline.category_averages["viewport_whitespace"] == 0.4
    assert baseline.distributions["interpretation_status"]["not_interpretable"] == 1


def test_compare_records_to_baseline_flags_iqr_outliers_and_not_interpretable():
    rows = [
        metric_row_from_payload(_payload("A", "SaaS", whitespace=0.2)),
        metric_row_from_payload(_payload("B", "SaaS", whitespace=0.21)),
        metric_row_from_payload(_payload("C", "SaaS", whitespace=0.22)),
        metric_row_from_payload(_payload("Outlier", "SaaS", whitespace=0.9)),
        metric_row_from_payload(
            _payload("Failed", "SaaS", whitespace=0.1, interpretation_status="not_interpretable")
        ),
    ]
    baselines = build_category_baselines(rows)

    comparisons = compare_records_to_baselines(rows, baselines)
    by_brand = {item.brand_name: item for item in comparisons}

    assert "viewport_whitespace_above_category_range" in by_brand["Outlier"].outlier_flags
    assert "not_interpretable_excluded_from_baseline" in by_brand["Failed"].outlier_flags
    assert by_brand["Failed"].confidence["score"] == 0.0


def test_build_baseline_script_writes_json_and_markdown_artifacts(tmp_path):
    script = _load_script()
    input_dir = tmp_path / "payloads"
    output_dir = tmp_path / "baselines"
    input_dir.mkdir()
    payloads = [
        _payload("A", "SaaS", whitespace=0.2),
        _payload("B", "SaaS", whitespace=0.3),
        _payload("C", "SaaS", whitespace=0.4),
        _payload("Media", "editorial/media", whitespace=0.1, density="dense", composition="dense_grid"),
    ]
    for payload in payloads:
        path = input_dir / f"{payload['brand_name'].lower()}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
    (input_dir / "manifest.json").write_text("{}", encoding="utf-8")

    result = script.build_baseline_artifacts(input_dir=input_dir, output_dir=output_dir)

    assert result["payload_count"] == 4
    assert result["category_count"] == 2
    baseline_payload = json.loads((output_dir / "category_baselines.json").read_text(encoding="utf-8"))
    comparison_payload = json.loads((output_dir / "brand_comparisons.json").read_text(encoding="utf-8"))
    assert "SaaS" in baseline_payload["categories"]
    assert comparison_payload["comparison_count"] == 4
    assert (output_dir / "metric_audit.json").exists()
    assert (output_dir / "metric_audit.md").exists()
    assert "# Visual Signature Category Baselines" in (output_dir / "category_baselines.md").read_text(encoding="utf-8")
    assert "# Visual Signature Category Comparisons" in (output_dir / "brand_comparisons.md").read_text(encoding="utf-8")
    assert "# Visual Signature Metric Audit" in (output_dir / "metric_audit.md").read_text(encoding="utf-8")
