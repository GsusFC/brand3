from __future__ import annotations

import importlib.util
import json
import struct
import sys
import zlib
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "visual_signature_calibrate.py"
VISION_EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "visual_signature" / "vision_calibration_brands.json"


def _load_calibrator():
    spec = importlib.util.spec_from_file_location("visual_signature_calibrate", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_png(path: Path, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row.extend(pixels[y * width + x])
        rows.append(bytes(row))
    png = b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            chunk("IHDR".encode(), struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            chunk("IDAT".encode(), zlib.compress(b"".join(rows))),
            chunk("IEND".encode(), b""),
        ]
    )
    path.write_bytes(png)


def _solid(width: int, height: int, color: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    return [color for _ in range(width * height)]


def _sparse(width: int, height: int) -> list[tuple[int, int, int]]:
    pixels = _solid(width, height, (255, 255, 255))
    for y in range(height // 3, height // 2):
        for x in range(width // 3, width // 2):
            pixels[y * width + x] = (32, 48, 96)
    return pixels


def _dense(width: int, height: int) -> list[tuple[int, int, int]]:
    colors = [(18, 22, 36), (224, 90, 29), (61, 105, 241), (244, 244, 244)]
    pixels = []
    for y in range(height):
        for x in range(width):
            pixels.append(colors[((x // 2) + (y // 2)) % len(colors)])
    return pixels


def _mixed(width: int, height: int) -> list[tuple[int, int, int]]:
    pixels = []
    palette = [(242, 242, 242), (0, 0, 0), (64, 160, 90), (245, 196, 66)]
    for y in range(height):
        for x in range(width):
            pixels.append(palette[(x // (width // 2)) + 2 * (y // (height // 2))])
    return pixels


def _balanced(width: int, height: int) -> list[tuple[int, int, int]]:
    pixels = _solid(width, height, (248, 246, 242))
    for y in range(height // 4, 3 * height // 4):
        for x in range(width // 4, 3 * width // 4):
            pixels[y * width + x] = (234, 180, 80)
    return pixels


def test_vision_calibration_example_set_uses_local_screenshots(tmp_path):
    calibrator = _load_calibrator()
    brands = calibrator.load_calibration_brands(VISION_EXAMPLE_PATH)
    assert len(brands) == 5
    assert all(brand.screenshot_path for brand in brands)

    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()
    patterns = {
        "linear.png": _sparse(64, 48),
        "openai.png": _solid(64, 48, (255, 255, 255)),
        "the-verge.png": _dense(64, 48),
        "allbirds.png": _mixed(64, 48),
        "headspace.png": _balanced(64, 48),
    }
    for filename, pixels in patterns.items():
        _write_png(screenshot_dir / filename, 64, 48, pixels)

    brands = [
        calibrator.CalibrationBrand(
            brand_name=brand.brand_name,
            website_url=brand.website_url,
            expected_category=brand.expected_category,
            notes=brand.notes,
            screenshot_path=str(tmp_path / Path(brand.screenshot_path).name),
        )
        for brand in brands
    ]
    for brand in brands:
        source = screenshot_dir / Path(brand.screenshot_path).name
        target = Path(brand.screenshot_path)
        target.write_bytes(source.read_bytes())

    manifest = calibrator.run_calibration_batch(
        brands,
        output_dir=tmp_path / "outputs",
        with_vision=True,
        extractor=lambda brand_name, website_url: {
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
        },
    )

    assert manifest["with_vision"] is True
    assert manifest["vision_available"] == 5
    assert manifest["vision_missing"] == 0
    assert manifest["error"] == 0
    summary = (tmp_path / "outputs" / "batch_summary.md").read_text(encoding="utf-8")
    assert "- Vision enabled: True" in summary
    assert "- Vision available: 5" in summary
    assert "Vision confidence avg:" in summary
    payload = json.loads((tmp_path / "outputs" / "linear.json").read_text(encoding="utf-8"))
    assert payload["vision"]["screenshot"]["available"] is True
    assert payload["vision"]["vision_confidence"]["level"] in {"low", "medium", "high"}
    assert payload["vision"]["composition"]["composition_classification"] in {
        "blank",
        "sparse_single_focus",
        "balanced_blocks",
        "dense_grid",
        "unknown",
    }
