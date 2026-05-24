from __future__ import annotations

import importlib.util
import json
import struct
import zlib
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "visual_signature_calibrate.py"
EXAMPLES_PATH = Path(__file__).resolve().parents[1] / "examples" / "visual_signature" / "calibration_brands.json"


def _load_calibrator():
    spec = importlib.util.spec_from_file_location("visual_signature_calibrate", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload(brand_name: str, website_url: str) -> dict:
    return {
        "brand_name": brand_name,
        "website_url": website_url,
        "analyzed_url": website_url,
        "interpretation_status": "interpretable",
        "acquisition": {"adapter": "custom", "status_code": 200, "warnings": [], "errors": []},
        "colors": {"palette": [{"hex": "#111111"}], "dominant_colors": ["#111111"], "confidence": 0.8},
        "typography": {"font_families": [{"family": "Inter"}], "confidence": 0.8},
        "logo": {"logo_detected": True, "candidates": [{"text": brand_name}], "confidence": 0.8},
        "layout": {"has_header": True, "has_navigation": True, "has_hero": True, "section_count": 3, "layout_patterns": ["grid"], "visual_density": "balanced", "confidence": 0.8},
        "components": {"components": [{"type": "cta", "count": 1}], "primary_ctas": ["Get started"], "confidence": 0.8},
        "assets": {"image_count": 1, "svg_count": 1, "screenshot_available": True, "asset_mix": ["logo", "screenshot"], "confidence": 0.8},
        "consistency": {"overall_consistency": 0.8, "color_consistency": 0.8, "typography_consistency": 0.8, "component_consistency": 0.8, "asset_consistency": 0.8, "confidence": 0.8},
        "extraction_confidence": {"score": 0.82, "level": "high", "factors": {"acquisition": 0.9}, "limitations": []},
        "version": "visual-signature-mvp-1",
    }


def _write_png(path: Path, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    raw_rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row.extend(pixels[y * width + x])
        raw_rows.append(bytes(row))
    png = b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk("IHDR".encode(), struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            chunk("IDAT".encode(), zlib.compress(b"".join(raw_rows))),
            chunk("IEND".encode(), b""),
        ]
    )
    path.write_bytes(png)


def _solid(width: int, height: int, color: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    return [color for _ in range(width * height)]


def test_load_calibration_brands_from_json_examples():
    calibrator = _load_calibrator()

    brands = calibrator.load_calibration_brands(EXAMPLES_PATH)

    assert 8 <= len(brands) <= 12
    categories = {brand.expected_category for brand in brands}
    assert "premium/luxury" in categories
    assert "SaaS" in categories
    assert "AI-native" in categories
    assert "editorial/media" in categories
    assert "ecommerce" in categories
    assert "weak/small business site" in categories
    assert "developer-first" in categories
    assert "wellness/lifestyle" in categories


def test_load_calibration_brands_from_csv(tmp_path):
    calibrator = _load_calibrator()
    csv_path = tmp_path / "brands.csv"
    csv_path.write_text(
        "brand_name,website_url,expected_category,notes\n"
        "Example,https://example.com,SaaS,fixture\n",
        encoding="utf-8",
    )

    brands = calibrator.load_calibration_brands(csv_path)

    assert len(brands) == 1
    assert brands[0].brand_name == "Example"
    assert brands[0].notes == "fixture"


def test_run_calibration_batch_writes_payload_summary_and_manifest(tmp_path):
    calibrator = _load_calibrator()
    brands = [
        calibrator.CalibrationBrand(
            brand_name="Example Brand",
            website_url="https://example.com",
            expected_category="SaaS",
            notes="fixture",
        )
    ]

    manifest = calibrator.run_calibration_batch(
        brands,
        output_dir=tmp_path,
        extractor=lambda brand_name, website_url: _payload(brand_name, website_url),
    )

    assert manifest["total"] == 1
    assert manifest["ok"] == 1
    assert manifest["not_interpretable"] == 0
    assert manifest["error"] == 0
    output_json = tmp_path / "example-brand.json"
    summary_txt = tmp_path / "summaries" / "example-brand.txt"
    assert output_json.exists()
    assert summary_txt.exists()
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "batch_summary.md").exists()
    assert (tmp_path / "obstruction_audit.json").exists()
    assert (tmp_path / "obstruction_audit.md").exists()
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["calibration"]["expected_category"] == "SaaS"
    assert payload["interpretation_status"] == "interpretable"
    assert "Extraction confidence: 0.82 (high)" in summary_txt.read_text(encoding="utf-8")


def test_run_calibration_batch_separates_not_interpretable_payloads(tmp_path):
    calibrator = _load_calibrator()
    brands = [
        calibrator.CalibrationBrand(
            brand_name="Failed Capture",
            website_url="https://failed.example",
            expected_category="SaaS",
            notes="fixture",
        )
    ]

    def extractor(brand_name: str, website_url: str):
        payload = _payload(brand_name, website_url)
        payload["interpretation_status"] = "not_interpretable"
        payload["acquisition"]["errors"] = ["fixture acquisition failure"]
        payload["extraction_confidence"]["score"] = 0.03
        payload["extraction_confidence"]["level"] = "low"
        payload["extraction_confidence"]["limitations"] = ["acquisition_errors_present"]
        return payload

    manifest = calibrator.run_calibration_batch(brands, output_dir=tmp_path, extractor=extractor)

    assert manifest["ok"] == 0
    assert manifest["not_interpretable"] == 1
    assert manifest["error"] == 0
    result = manifest["results"][0]
    assert result["status"] == "not_interpretable"
    assert result["interpretation_status"] == "not_interpretable"
    assert result["weak_signal_count"] == 0
    summary = (tmp_path / "batch_summary.md").read_text(encoding="utf-8")
    assert "- Not interpretable: 1" in summary
    assert "| Failed Capture | SaaS | not_interpretable | not_interpretable | 0.03" in summary


def test_run_calibration_batch_records_errors_without_stopping(tmp_path):
    calibrator = _load_calibrator()
    brands = [
        calibrator.CalibrationBrand("Good", "https://good.example", "SaaS", ""),
        calibrator.CalibrationBrand("Bad", "https://bad.example", "SaaS", ""),
    ]

    def extractor(brand_name: str, website_url: str):
        if brand_name == "Bad":
            raise RuntimeError("fixture failure")
        return _payload(brand_name, website_url)

    manifest = calibrator.run_calibration_batch(brands, output_dir=tmp_path, extractor=extractor)

    assert manifest["total"] == 2
    assert manifest["ok"] == 1
    assert manifest["error"] == 1
    assert (tmp_path / "good.json").exists()
    error_payload = json.loads((tmp_path / "bad.error.json").read_text(encoding="utf-8"))
    assert error_payload["status"] == "error"
    assert error_payload["error"] == "fixture failure"


def test_run_calibration_batch_with_vision_enriches_payload_and_manifest(tmp_path):
    calibrator = _load_calibrator()
    screenshot = tmp_path / "vision.png"
    _write_png(screenshot, 32, 24, _solid(32, 24, (255, 255, 255)))
    brands = [
        calibrator.CalibrationBrand(
            brand_name="Vision Brand",
            website_url="https://vision.example",
            expected_category="SaaS",
            notes="fixture",
            screenshot_path=str(screenshot),
            screenshot_payload={
                "capture_type": "viewport",
                "viewport_width": 32,
                "viewport_height": 24,
                "page_url": "https://vision.example",
            },
        )
    ]

    manifest = calibrator.run_calibration_batch(
        brands,
        output_dir=tmp_path,
        with_vision=True,
        extractor=lambda brand_name, website_url: _payload(brand_name, website_url),
    )

    assert manifest["with_vision"] is True
    assert manifest["vision_available"] == 1
    assert manifest["vision_missing"] == 0
    assert manifest["viewport_available"] == 1
    assert manifest["viewport_missing"] == 0
    assert manifest["vision_confidence_avg"] is not None
    assert manifest["viewport_confidence_avg"] is not None
    payload = json.loads((tmp_path / "vision-brand.json").read_text(encoding="utf-8"))
    assert payload["vision"]["screenshot"]["available"] is True
    assert payload["vision"]["screenshot"]["capture_type"] == "viewport"
    assert payload["vision"]["screenshot"]["quality"] == "blank"
    assert payload["vision"]["vision_confidence"]["score"] >= 0
    assert payload["vision"]["viewport_confidence"]["score"] >= 0
    summary = (tmp_path / "batch_summary.md").read_text(encoding="utf-8")
    assert "- Vision enabled: True" in summary
    assert "- Viewport available: 1" in summary
    assert "| Vision Brand | SaaS | ok | interpretable | 0.82 | 100% | 0 | blank |" in summary
    assert "Viewport confidence" in summary


def test_run_calibration_batch_with_vision_marks_missing_when_no_screenshot(tmp_path):
    calibrator = _load_calibrator()
    brands = [
        calibrator.CalibrationBrand(
            brand_name="No Screenshot",
            website_url="https://noshot.example",
            expected_category="SaaS",
            notes="fixture",
        )
    ]

    manifest = calibrator.run_calibration_batch(
        brands,
        output_dir=tmp_path,
        with_vision=True,
        extractor=lambda brand_name, website_url: _payload(brand_name, website_url),
    )

    assert manifest["vision_available"] == 0
    assert manifest["vision_missing"] == 1
    assert manifest["viewport_available"] == 0
    assert manifest["viewport_missing"] == 1
    payload = json.loads((tmp_path / "no-screenshot.json").read_text(encoding="utf-8"))
    assert payload["vision"]["screenshot"]["available"] is False
    assert payload["vision"]["screenshot"]["quality"] == "missing"
    assert payload["vision"]["viewport_confidence"]["score"] == 0.0


def test_run_calibration_batch_reports_agreement_in_summary(tmp_path):
    calibrator = _load_calibrator()
    screenshot = tmp_path / "agreement.png"
    _write_png(screenshot, 40, 80, _solid(40, 80, (255, 255, 255)))
    brands = [
        calibrator.CalibrationBrand(
            brand_name="Agreement Brand",
            website_url="https://agreement.example",
            expected_category="SaaS",
            notes="fixture",
            screenshot_path=str(screenshot),
            screenshot_payload={
                "capture_type": "full_page",
                "viewport_width": 40,
                "viewport_height": 40,
                "page_url": "https://agreement.example",
            },
        )
    ]

    def extractor(brand_name: str, website_url: str):
        payload = _payload(brand_name, website_url)
        payload["layout"]["visual_density"] = "dense"
        payload["consistency"]["overall_consistency"] = 0.8
        payload["colors"]["palette"] = [{"hex": f"#{idx}{idx}{idx}{idx}{idx}{idx}"} for idx in range(8)]
        return payload

    manifest = calibrator.run_calibration_batch(
        brands,
        output_dir=tmp_path / "outputs",
        with_vision=True,
        extractor=extractor,
    )

    assert manifest["agreement_low"] + manifest["agreement_medium"] + manifest["agreement_high"] == 1
    summary = (tmp_path / "outputs" / "batch_summary.md").read_text(encoding="utf-8")
    assert "Agreement" in summary
    assert "Flags" in summary


def test_run_calibration_batch_reads_capture_manifest_metadata(tmp_path, monkeypatch):
    calibrator = _load_calibrator()
    screenshot = tmp_path / "manifest.png"
    _write_png(screenshot, 24, 24, _solid(24, 24, (255, 255, 255)))
    capture_manifest = {
        "results": [
            {
                "brand_name": "Manifest Brand",
                "website_url": "https://manifest.example",
                "screenshot_path": str(screenshot),
                "capture_type": "viewport",
                "viewport_width": 24,
                "viewport_height": 24,
                "page_url": "https://manifest.example",
                "source": "playwright",
                "width": 24,
                "height": 24,
                "file_size_bytes": 123,
            }
        ]
    }
    manifest_path = tmp_path / "capture_manifest.json"
    manifest_path.write_text(json.dumps(capture_manifest), encoding="utf-8")
    monkeypatch.setattr(calibrator, "DEFAULT_CAPTURE_MANIFEST", manifest_path)

    brands = [
        calibrator.CalibrationBrand(
            brand_name="Manifest Brand",
            website_url="https://manifest.example",
            expected_category="SaaS",
            notes="fixture",
            screenshot_path=str(screenshot),
        )
    ]

    manifest = calibrator.run_calibration_batch(
        brands,
        output_dir=tmp_path / "outputs",
        with_vision=True,
        extractor=lambda brand_name, website_url: _payload(brand_name, website_url),
    )

    assert manifest["viewport_available"] == 1
    payload = json.loads((tmp_path / "outputs" / "manifest-brand.json").read_text(encoding="utf-8"))
    assert payload["vision"]["screenshot"]["capture_type"] == "viewport"
    assert payload["vision"]["screenshot"]["viewport_width"] == 24


def test_run_calibration_batch_writes_obstruction_audit(tmp_path):
    calibrator = _load_calibrator()
    width, height = 40, 30
    pixels = _solid(width, height, (255, 255, 255))
    for y in range(21, height):
        for x in range(width):
            pixels[y * width + x] = (230, 230, 230)
    screenshot = tmp_path / "obstructed.png"
    _write_png(screenshot, width, height, pixels)
    brands = [
        calibrator.CalibrationBrand(
            brand_name="Obstructed Brand",
            website_url="https://obstructed.example",
            expected_category="SaaS",
            notes="fixture",
            screenshot_path=str(screenshot),
            screenshot_payload={
                "capture_type": "viewport",
                "viewport_width": width,
                "viewport_height": height,
                "page_url": "https://obstructed.example",
            },
        )
    ]

    def extractor(brand_name: str, website_url: str):
        payload = _payload(brand_name, website_url)
        payload["acquisition"]["viewport_obstruction"] = {
            "present": True,
            "type": "cookie_banner",
            "severity": "moderate",
            "coverage_ratio": 0.22,
            "first_impression_valid": True,
            "confidence": 0.7,
            "signals": ["dom_keyword:cookie"],
            "limitations": [],
        }
        return payload

    manifest = calibrator.run_calibration_batch(
        brands,
        output_dir=tmp_path / "outputs",
        with_vision=True,
        extractor=extractor,
    )

    assert manifest["obstruction_present"] == 1
    assert manifest["invalid_first_impression"] == 0
    audit = json.loads((tmp_path / "outputs" / "obstruction_audit.json").read_text(encoding="utf-8"))
    assert audit["obstructed"] == 1
    assert audit["severity_distribution"]["moderate"] == 1
    assert audit["per_category"]["SaaS"]["obstruction_rate"] == 1.0
    summary = (tmp_path / "outputs" / "batch_summary.md").read_text(encoding="utf-8")
    assert "Viewport obstructions: 1" in summary
    assert "cookie_banner/moderate" in summary
