from __future__ import annotations

import struct
import zlib
from pathlib import Path

from src.visual_signature.vision import enrich_visual_signature_with_vision


def _payload() -> dict:
    return {
        "brand_name": "Vision Fixture",
        "website_url": "https://example.com",
        "version": "visual-signature-mvp-1",
        "interpretation_status": "interpretable",
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


def test_vision_enrichment_handles_missing_screenshot_without_mutating_payload():
    payload = _payload()

    enriched = enrich_visual_signature_with_vision(visual_signature_payload=payload)

    assert "vision" not in payload
    assert enriched["vision"]["screenshot"]["available"] is False
    assert enriched["vision"]["screenshot"]["quality"] == "missing"
    assert enriched["vision"]["vision_confidence"]["level"] == "low"
    assert enriched["vision"]["viewport_confidence"]["level"] == "low"
    assert "screenshot_not_available" in enriched["vision"]["vision_confidence"]["limitations"]


def test_vision_enrichment_detects_blank_screenshot(tmp_path):
    screenshot = tmp_path / "blank.png"
    _write_png(screenshot, 24, 16, _solid(24, 16, (255, 255, 255)))

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=_payload(),
        screenshot_path=str(screenshot),
        screenshot_payload={
            "capture_type": "viewport",
            "viewport_width": 24,
            "viewport_height": 16,
            "page_url": "https://example.com",
        },
    )

    vision = enriched["vision"]
    assert vision["screenshot"]["available"] is True
    assert vision["screenshot"]["width"] == 24
    assert vision["screenshot"]["height"] == 16
    assert vision["screenshot"]["capture_type"] == "viewport"
    assert vision["screenshot"]["viewport_width"] == 24
    assert vision["screenshot"]["viewport_height"] == 16
    assert vision["screenshot"]["quality"] == "blank"
    assert vision["composition"]["composition_classification"] == "blank"
    assert vision["composition"]["whitespace_ratio"] == 1.0
    assert vision["viewport_composition"]["composition_classification"] == "blank"


def test_vision_enrichment_classifies_sparse_screenshot(tmp_path):
    width, height = 80, 60
    pixels = _solid(width, height, (255, 255, 255))
    for y in range(24, 36):
        for x in range(28, 52):
            pixels[y * width + x] = (20, 40, 80)
    screenshot = tmp_path / "sparse.png"
    _write_png(screenshot, width, height, pixels)

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=_payload(),
        screenshot_payload={
            "path": str(screenshot),
            "capture_type": "viewport",
            "viewport_width": width,
            "viewport_height": height,
            "page_url": "https://example.com",
        },
    )

    vision = enriched["vision"]
    assert vision["composition"]["visual_density"] == "sparse"
    assert vision["composition"]["composition_classification"] == "sparse_single_focus"
    assert vision["composition"]["whitespace_ratio"] > 0.85
    assert vision["screenshot_palette"]["dominant_colors"][0]["hex"] == "#ffffff"
    assert vision["viewport_visual_density"] == "sparse"
    assert vision["viewport_whitespace_ratio"] > 0.85


def test_vision_enrichment_classifies_dense_screenshot(tmp_path):
    width, height = 64, 64
    colors = [(12, 20, 32), (230, 80, 40), (40, 120, 230), (245, 245, 245)]
    pixels = []
    for y in range(height):
        for x in range(width):
            pixels.append(colors[((x // 4) + (y // 4)) % len(colors)])
    screenshot = tmp_path / "dense.png"
    _write_png(screenshot, width, height, pixels)

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=_payload(),
        screenshot_path=str(screenshot),
        screenshot_payload={
            "capture_type": "viewport",
            "viewport_width": width,
            "viewport_height": height,
            "page_url": "https://example.com",
        },
    )

    vision = enriched["vision"]
    assert vision["composition"]["visual_density"] == "dense"
    assert vision["composition"]["composition_classification"] == "dense_grid"
    assert vision["screenshot"]["quality"] in {"low_detail", "usable"}
    assert vision["vision_confidence"]["score"] > 0
    assert vision["viewport_composition"]["visual_density"] == "dense"
    assert vision["viewport_confidence"]["score"] > 0


def test_vision_enrichment_extracts_mixed_color_palette(tmp_path):
    width, height = 40, 40
    pixels = []
    for y in range(height):
        for x in range(width):
            if x < 20 and y < 20:
                pixels.append((255, 0, 0))
            elif x >= 20 and y < 20:
                pixels.append((0, 255, 0))
            elif x < 20:
                pixels.append((0, 0, 255))
            else:
                pixels.append((255, 255, 0))
    screenshot = tmp_path / "mixed.png"
    _write_png(screenshot, width, height, pixels)

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=_payload(),
        screenshot_path=str(screenshot),
        screenshot_payload={
            "capture_type": "viewport",
            "viewport_width": width,
            "viewport_height": height,
            "page_url": "https://example.com",
        },
    )

    colors = {item["hex"] for item in enriched["vision"]["screenshot_palette"]["dominant_colors"]}
    assert {"#ff0000", "#00ff00", "#0000ff", "#ffff00"}.issubset(colors)
    assert enriched["vision"]["screenshot_palette"]["color_count"] >= 4


def test_vision_enrichment_uses_viewport_crop_for_full_page_screenshot(tmp_path):
    width, height = 40, 80
    pixels = _solid(width, height, (255, 255, 255))
    for y in range(40, 80):
        for x in range(width):
            pixels[y * width + x] = (20, 40, 80) if (x + y) % 2 == 0 else (200, 80, 40)
    screenshot = tmp_path / "full-page.png"
    _write_png(screenshot, width, height, pixels)

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=_payload(),
        screenshot_path=str(screenshot),
        screenshot_payload={
            "capture_type": "full_page",
            "viewport_width": width,
            "viewport_height": 40,
            "page_url": "https://example.com",
        },
    )

    vision = enriched["vision"]
    assert vision["screenshot"]["capture_type"] == "full_page"
    assert vision["screenshot"]["viewport_height"] == 40
    assert vision["viewport_composition"]["visual_density"] == "sparse"
    assert vision["viewport_whitespace_ratio"] > vision["composition"]["whitespace_ratio"]
    assert vision["viewport_palette"]["dominant_colors"][0]["hex"] == "#ffffff"


def test_vision_enrichment_produces_dom_viewport_agreement_flags_for_dense_dom(tmp_path):
    width, height = 40, 80
    pixels = _solid(width, height, (255, 255, 255))
    for y in range(40, 80):
        for x in range(width):
            pixels[y * width + x] = (20, 40, 80) if (x + y) % 2 == 0 else (200, 80, 40)
    screenshot = tmp_path / "agreement.png"
    _write_png(screenshot, width, height, pixels)

    payload = _payload()
    payload["layout"] = {"visual_density": "dense"}
    payload["consistency"] = {"overall_consistency": 0.8}
    payload["colors"] = {
        "confidence": 0.9,
        "palette": [
            {"hex": "#111111"},
            {"hex": "#222222"},
            {"hex": "#333333"},
            {"hex": "#444444"},
            {"hex": "#555555"},
            {"hex": "#666666"},
            {"hex": "#777777"},
            {"hex": "#888888"},
        ],
    }

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=payload,
        screenshot_path=str(screenshot),
        screenshot_payload={
            "capture_type": "full_page",
            "viewport_width": width,
            "viewport_height": 40,
            "page_url": "https://example.com",
        },
    )

    agreement = enriched["vision"]["agreement"]
    assert agreement["agreement_level"] in {"medium", "low"}
    assert "dom_density_disagrees_with_viewport_first_fold" in agreement["disagreement_flags"]
    assert agreement["disagreement_severity"] in {"minor", "moderate", "major"}
    assert agreement["disagreement_severity_score"] > 0
    assert agreement["typed_agreement"]["density"]["score"] < 1
    assert agreement["summary_notes"]


def test_viewport_obstruction_detects_bottom_cookie_bar(tmp_path):
    width, height = 80, 60
    pixels = _solid(width, height, (255, 255, 255))
    for y in range(46, height):
        for x in range(width):
            pixels[y * width + x] = (230, 230, 230)
    screenshot = tmp_path / "cookie-bar.png"
    _write_png(screenshot, width, height, pixels)
    payload = _payload()
    payload["acquisition"] = {
        "viewport_obstruction": {
            "present": True,
            "type": "cookie_banner",
            "severity": "moderate",
            "coverage_ratio": 0.23,
            "first_impression_valid": True,
            "confidence": 0.74,
            "page_level_signals": ["dom_keyword:cookie"],
            "overlay_level_signals": [],
            "visual_signals": [],
            "signals": ["dom_keyword:cookie", "dom_bottom_aligned_container_pattern"],
            "limitations": [],
        }
    }

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=payload,
        screenshot_path=str(screenshot),
        screenshot_payload={"capture_type": "viewport", "viewport_width": width, "viewport_height": height},
    )

    obstruction = enriched["vision"]["viewport_obstruction"]
    assert obstruction["present"] is True
    assert obstruction["type"] == "cookie_banner"
    assert obstruction["severity"] == "moderate"
    assert obstruction["first_impression_valid"] is True
    assert "viewport_bottom_bar_pattern" in obstruction["signals"]
    assert "dom_keyword:cookie" in obstruction["page_level_signals"]


def test_viewport_obstruction_detects_centered_modal(tmp_path):
    width, height = 90, 70
    pixels = _solid(width, height, (22, 22, 22))
    for y in range(18, 52):
        for x in range(24, 66):
            pixels[y * width + x] = (245, 245, 245)
    screenshot = tmp_path / "modal.png"
    _write_png(screenshot, width, height, pixels)
    payload = _payload()
    payload["acquisition"] = {
        "viewport_obstruction": {
            "present": True,
            "type": "cookie_modal",
            "coverage_ratio": 0.55,
            "page_level_signals": [],
            "overlay_level_signals": ["dom_keyword:consent"],
            "visual_signals": [],
            "signals": ["dom_keyword:consent", "dom_overlay_term:dialog"],
            "limitations": [],
        }
    }

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=payload,
        screenshot_path=str(screenshot),
        screenshot_payload={"capture_type": "viewport", "viewport_width": width, "viewport_height": height},
    )

    obstruction = enriched["vision"]["viewport_obstruction"]
    assert obstruction["present"] is True
    assert obstruction["type"] in {"cookie_banner", "cookie_modal"}
    assert obstruction["severity"] == "major"
    assert obstruction["first_impression_valid"] is False
    assert "viewport_centered_modal_with_backdrop" in obstruction["signals"]
    assert "dom_keyword:consent" in obstruction["overlay_level_signals"]


def test_viewport_obstruction_detects_fullscreen_login_overlay(tmp_path):
    width, height = 72, 54
    screenshot = tmp_path / "fullscreen.png"
    _write_png(screenshot, width, height, _solid(width, height, (12, 12, 12)))
    payload = _payload()
    payload["acquisition"] = {
        "viewport_obstruction": {
            "present": True,
            "type": "login_wall",
            "coverage_ratio": 0.92,
            "page_level_signals": [],
            "overlay_level_signals": ["dom_keyword:login"],
            "visual_signals": ["dom_full_viewport_container_pattern"],
            "signals": ["dom_keyword:login", "dom_full_viewport_container_pattern"],
            "limitations": [],
        }
    }

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=payload,
        screenshot_path=str(screenshot),
        screenshot_payload={"capture_type": "viewport", "viewport_width": width, "viewport_height": height},
    )

    obstruction = enriched["vision"]["viewport_obstruction"]
    assert obstruction["present"] is True
    assert obstruction["type"] == "login_wall"
    assert obstruction["severity"] == "blocking"
    assert obstruction["first_impression_valid"] is False
    assert "dom_keyword:login" in obstruction["overlay_level_signals"]
    assert "dom_full_viewport_container_pattern" in obstruction["visual_signals"]


def test_viewport_obstruction_marks_non_blocking_sticky_footer_minor(tmp_path):
    width, height = 100, 80
    pixels = _solid(width, height, (255, 255, 255))
    for y in range(75, height):
        for x in range(width):
            pixels[y * width + x] = (35, 35, 35)
    screenshot = tmp_path / "sticky-footer.png"
    _write_png(screenshot, width, height, pixels)

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=_payload(),
        screenshot_path=str(screenshot),
        screenshot_payload={"capture_type": "viewport", "viewport_width": width, "viewport_height": height},
    )

    obstruction = enriched["vision"]["viewport_obstruction"]
    assert obstruction["present"] is True
    assert obstruction["severity"] == "minor"
    assert obstruction["first_impression_valid"] is True


def test_cookie_modal_with_header_login_link_is_not_login_wall(tmp_path):
    width, height = 96, 72
    pixels = _solid(width, height, (255, 255, 255))
    for y in range(44, 72):
        for x in range(width):
            pixels[y * width + x] = (235, 235, 235)
    screenshot = tmp_path / "cookie-modal.png"
    _write_png(screenshot, width, height, pixels)
    payload = _payload()
    payload["acquisition"] = {
        "rendered_html": """
        <html>
          <body>
            <header><a href=\"/login\">Login</a></header>
            <div class=\"cookie-consent modal fixed bottom-0 z-50\" style=\"position: fixed; bottom: 0; z-index: 9999;\">
              We use cookies. Manage privacy preferences. Accept all cookies.
            </div>
          </body>
        </html>
        """
    }

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=payload,
        screenshot_path=str(screenshot),
        screenshot_payload={"capture_type": "viewport", "viewport_width": width, "viewport_height": height},
    )

    obstruction = enriched["vision"]["viewport_obstruction"]
    assert obstruction["type"] in {"cookie_banner", "cookie_modal"}
    assert obstruction["present"] is True
    assert obstruction["severity"] in {"moderate", "major"}
    assert "dom_keyword:login" in obstruction["page_level_signals"]
    assert "dom_keyword:cookie" in obstruction["overlay_level_signals"] or "dom_keyword:cookie" in obstruction["page_level_signals"]
    assert obstruction["confidence"] >= 0.55


def test_newsletter_modal_with_nav_signin_is_not_login_wall(tmp_path):
    width, height = 96, 72
    pixels = _solid(width, height, (255, 255, 255))
    for y in range(18, 58):
        for x in range(18, 78):
            pixels[y * width + x] = (245, 245, 245)
    screenshot = tmp_path / "newsletter-modal.png"
    _write_png(screenshot, width, height, pixels)
    payload = _payload()
    payload["acquisition"] = {
        "rendered_html": """
        <html>
          <body>
            <nav><a href=\"/signin\">Sign in</a></nav>
            <div class=\"newsletter modal overlay\" role=\"dialog\" aria-modal=\"true\">
              Subscribe to our newsletter for updates.
            </div>
          </body>
        </html>
        """
    }

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=payload,
        screenshot_path=str(screenshot),
        screenshot_payload={"capture_type": "viewport", "viewport_width": width, "viewport_height": height},
    )

    obstruction = enriched["vision"]["viewport_obstruction"]
    assert obstruction["type"] == "newsletter_modal"
    assert obstruction["present"] is True
    assert "dom_keyword:sign in" in obstruction["page_level_signals"] or "dom_keyword:signin" in obstruction["page_level_signals"]
    assert "dom_keyword:newsletter" in obstruction["overlay_level_signals"] or "dom_keyword:newsletter" in obstruction["page_level_signals"]


def test_true_login_wall_remains_login_wall(tmp_path):
    width, height = 96, 72
    screenshot = tmp_path / "login-wall.png"
    _write_png(screenshot, width, height, _solid(width, height, (18, 18, 18)))
    payload = _payload()
    payload["acquisition"] = {
        "rendered_html": """
        <html>
          <body>
            <div class=\"account-gate modal overlay fullscreen\" role=\"dialog\" aria-modal=\"true\" style=\"position: fixed; inset: 0; z-index: 9999;\">
              Sign in to continue. Create account or log in to access members only content.
            </div>
          </body>
        </html>
        """
    }

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=payload,
        screenshot_path=str(screenshot),
        screenshot_payload={"capture_type": "viewport", "viewport_width": width, "viewport_height": height},
    )

    obstruction = enriched["vision"]["viewport_obstruction"]
    assert obstruction["type"] == "login_wall"
    assert obstruction["present"] is True
    assert obstruction["severity"] == "blocking"
    assert obstruction["first_impression_valid"] is False
    assert "dom_keyword:sign in" in obstruction["overlay_level_signals"]
    assert "dom_keyword:create account" in obstruction["overlay_level_signals"]


def test_cookie_consent_modal_becomes_eligible_for_dismissal(tmp_path):
    width, height = 100, 80
    pixels = _solid(width, height, (250, 250, 250))
    for y in range(62, 80):
        for x in range(width):
            pixels[y * width + x] = (220, 220, 220)
    screenshot = tmp_path / "cookie-consent.png"
    _write_png(screenshot, width, height, pixels)
    payload = _payload()
    payload["acquisition"] = {
        "rendered_html": """
        <html>
          <body>
            <div class=\"cookie banner consent fixed bottom-0\" style=\"position: fixed; bottom: 0; height: 18vh; z-index: 9999;\">
              We use cookies. Accept all cookies or manage choices.
            </div>
          </body>
        </html>
        """
    }

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=payload,
        screenshot_path=str(screenshot),
        screenshot_payload={"capture_type": "viewport", "viewport_width": width, "viewport_height": height},
    )

    obstruction = enriched["vision"]["viewport_obstruction"]
    assert obstruction["type"] in {"cookie_banner", "cookie_modal"}
    assert obstruction["present"] is True
    assert obstruction["confidence"] >= 0.55
    assert "cookie" in " ".join(obstruction["signals"])


def test_viewport_obstruction_resists_privacy_text_false_positive(tmp_path):
    width, height = 80, 60
    screenshot = tmp_path / "clean.png"
    _write_png(screenshot, width, height, _solid(width, height, (255, 255, 255)))
    payload = _payload()
    payload["acquisition"] = {
        "rendered_html": "<main><h1>Privacy-first analytics</h1><p>No banner in this fixture.</p></main>"
    }

    enriched = enrich_visual_signature_with_vision(
        visual_signature_payload=payload,
        screenshot_path=str(screenshot),
        screenshot_payload={"capture_type": "viewport", "viewport_width": width, "viewport_height": height},
    )

    obstruction = enriched["vision"]["viewport_obstruction"]
    assert obstruction["present"] is False
    assert obstruction["severity"] == "none"
    assert obstruction["first_impression_valid"] is True
