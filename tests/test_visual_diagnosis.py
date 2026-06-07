from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

from scripts.visual_diagnosis_lab import (
    contextdev_candidate_summary_to_visual_signature,
    extract_coherence_breakdown,
    run_lab,
)
from src.visual_diagnosis import build_visual_diagnosis
from src.visual_diagnosis.evidence import build_visual_evidence_from_local_inputs


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


def _web_payload() -> dict:
    return {
        "url": "https://example.com",
        "canonical_url": "https://example.com",
        "title": "Example",
        "meta_description": "Example design system",
        "html": """
        <html>
          <head>
            <style>
              body { font-family: Inter, sans-serif; color: #111111; background: #ffffff; }
              h1 { font-size: 56px; color: #2255ff; }
              .grid { display: grid; }
            </style>
          </head>
          <body>
            <header><nav><a>Product</a><a>Pricing</a></nav></header>
            <main>
              <section class="hero grid">
                <h1>Build faster</h1>
                <a class="button primary cta">Get started</a>
              </section>
              <article class="card">Proof</article>
              <article class="card">Proof</article>
              <article class="card">Proof</article>
            </main>
          </body>
        </html>
        """,
        "markdown_content": "[Get started](https://example.com/start)",
        "images": [],
        "links": ["https://example.com/start"],
        "tech_stack": [],
        "error": "",
    }


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
    path.write_bytes(
        b"".join(
            [
                b"\x89PNG\r\n\x1a\n",
                chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
                chunk(b"IDAT", zlib.compress(b"".join(rows))),
                chunk(b"IEND", b""),
            ]
        )
    )


def _dense_pixels(width: int, height: int) -> list[tuple[int, int, int]]:
    colors = [
        (20, 20, 20),
        (240, 240, 240),
        (80, 120, 200),
        (200, 90, 60),
        (40, 160, 120),
        (120, 80, 180),
        (230, 180, 70),
        (90, 90, 90),
        (10, 70, 120),
        (180, 40, 120),
    ]
    return [colors[(x // 4 + y // 4) % len(colors)] for y in range(height) for x in range(width)]


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
    assert result["summary"]["results"][0]["magnetism"]["visual_identity"] == 82


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
    assert result["signals"]["antipatterns"] == ["visual_analysis_not_interpretable"]
    assert "visual_analysis_not_interpretable" in result["limitations"]


def test_extract_coherence_breakdown_from_scanner_methodology_payload():
    payload = {
        "methodology": {
            "score_breakdown": {
                "coherence": {
                    "visual_identity": 72,
                    "message_consistency": 90,
                }
            }
        }
    }

    assert extract_coherence_breakdown(payload) == {
        "visual_identity": 72,
        "message_consistency": 90,
    }


def test_extract_coherence_breakdown_from_normalized_payload():
    payload = {
        "scanner": {
            "score_coherence_breakdown": {
                "visual_identity": 68,
                "tactical_alignment": 80,
            }
        }
    }

    assert extract_coherence_breakdown(payload) == {
        "visual_identity": 68,
        "tactical_alignment": 80,
    }


def test_extract_coherence_breakdown_from_batch_row_fallback():
    assert extract_coherence_breakdown({"coherence_score": 66}) == {
        "visual_identity": 66,
        "source": "coherence_score_fallback",
    }


def test_visual_diagnosis_lab_summary_renders_magnetism_comparison(tmp_path):
    visual_path = tmp_path / "visual.json"
    visual_path.write_text(json.dumps(_visual_signature_payload()), encoding="utf-8")
    magnetism_path = tmp_path / "magnetism.json"
    magnetism_path.write_text(
        json.dumps(
            {
                "methodology": {
                    "score_breakdown": {
                        "coherence": {
                            "visual_identity": 61,
                            "message_consistency": 92,
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "brands": [
                    {
                        "brand_name": "Example",
                        "website_url": "https://example.com",
                        "visual_signature_path": str(visual_path),
                        "magnetism_payload_path": str(magnetism_path),
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
    summary_md = next((tmp_path / "out").glob("*/summary.md")).read_text(encoding="utf-8")

    assert result["summary"]["results"][0]["magnetism"]["visual_identity"] == 61
    assert "| Example | usable | template_saas | weak_or_inconsistent | 61 | low | high |" in summary_md
    assert "visual_promise_mismatch" in summary_md


def test_contextdev_candidate_summary_maps_visual_candidates_for_matching_domain():
    payload = {
        "candidates": [
            {
                "candidate_id": "ctx_colors",
                "candidate_type": "visual_colors",
                "supports_channel": "visual_identity",
                "source_url": "https://example.com",
                "text": json.dumps(
                    {
                        "background": "#ffffff",
                        "text": "#111111",
                        "accent": "#ff537a",
                    }
                ),
            },
            {
                "candidate_id": "ctx_type",
                "candidate_type": "visual_typography",
                "supports_channel": "visual_identity",
                "source_url": "https://example.com",
                "text": json.dumps(
                    {
                        "headings": {
                            "h1": {"fontFamily": "Jokker Bold", "fontSize": "58px"},
                            "h2": {"fontFamily": "Jokker Bold", "fontSize": "34px"},
                        },
                        "p": {"fontFamily": "Inter"},
                    }
                ),
            },
            {
                "candidate_id": "ctx_other",
                "candidate_type": "visual_colors",
                "supports_channel": "visual_identity",
                "source_url": "https://other.example",
                "text": json.dumps({"background": "#000000"}),
            },
        ]
    }

    result = contextdev_candidate_summary_to_visual_signature(
        payload,
        website_url="https://www.example.com",
    )

    assert result["source"] == "contextdev_candidate_summary"
    assert result["interpretation_status"] == "interpretable"
    assert result["colors"]["dominant_colors"] == ["#ffffff", "#111111"]
    assert result["colors"]["accent_candidates"] == ["#ff537a"]
    assert result["typography"]["heading_font"] == "Jokker Bold"
    assert result["contextdev"]["candidate_ids"] == ["ctx_colors", "ctx_type"]


def test_visual_evidence_builds_from_local_web_payload_without_provider_call():
    evidence = build_visual_evidence_from_local_inputs(
        brand_name="Example",
        website_url="https://example.com",
        web_payload=_web_payload(),
    )

    payload = evidence.visual_signature_payload or {}
    assert evidence.source_mode == "dom_css_visual_lab"
    assert evidence.evidence_refs == ["raw_inputs:web"]
    assert payload["source"] == "dom_css_visual_lab"
    assert payload["interpretation_status"] == "interpretable"
    assert payload["layout"]["has_navigation"] is True
    assert payload["components"]["primary_ctas"] == ["Get started"]
    assert "raw_inputs:web" in evidence.evidence_refs


def test_visual_diagnosis_lab_accepts_contextdev_candidate_summary(tmp_path):
    contextdev_path = tmp_path / "contextdev.json"
    contextdev_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "candidate_id": "ctx_colors",
                        "candidate_type": "visual_colors",
                        "supports_channel": "visual_identity",
                        "source_url": "https://developer.example",
                        "text": json.dumps(
                            {
                                "background": "#050505",
                                "text": "#ffffff",
                                "accent": "#4b8cff",
                            }
                        ),
                    },
                    {
                        "candidate_id": "ctx_components",
                        "candidate_type": "visual_components",
                        "supports_channel": "visual_identity",
                        "source_url": "https://developer.example",
                        "text": "button and card components use substantial call-to-action controls",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "brands": [
                    {
                        "brand_name": "Developer Example",
                        "website_url": "https://developer.example",
                        "category_hint": "developer infrastructure",
                        "contextdev_candidate_summary_path": str(contextdev_path),
                        "coherence_breakdown": {"visual_identity": 88},
                        "screenshot_capture": {
                            "screenshot_url": "file:///tmp/developer-example.png",
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
    diagnosis = result["summary"]["results"][0]["diagnosis"]

    assert diagnosis["diagnosis"]["reference_profile"] == "developer_first"
    assert diagnosis["diagnosis"]["identity_read"] == "functionally_clear"
    assert "raw_inputs:contextdev_candidate_summary" in diagnosis["evidence_refs"]
    assert "raw_inputs:visual_signature" not in diagnosis["evidence_refs"]


def test_visual_diagnosis_lab_accepts_web_payload_path(tmp_path):
    web_path = tmp_path / "web.json"
    web_path.write_text(json.dumps(_web_payload()), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "brands": [
                    {
                        "brand_name": "Web Example",
                        "website_url": "https://example.com",
                        "category_hint": "developer infrastructure",
                        "web_payload_path": str(web_path),
                        "coherence_breakdown": {"visual_identity": 86},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_lab(manifest_path, output_root=tmp_path / "out")
    diagnosis = result["summary"]["results"][0]["diagnosis"]

    assert diagnosis["diagnosis"]["reference_profile"] == "developer_first"
    assert diagnosis["diagnosis"]["identity_read"] == "functionally_clear"
    assert "raw_inputs:web_visual_evidence" in diagnosis["evidence_refs"]


def test_visual_diagnosis_lab_normalizes_db_screenshot_capture_payload(tmp_path):
    visual_path = tmp_path / "visual.json"
    visual_path.write_text(json.dumps(_visual_signature_payload()), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "brands": [
                    {
                        "brand_name": "DB Capture",
                        "website_url": "https://db-capture.example",
                        "visual_signature_path": str(visual_path),
                        "coherence_breakdown": {"visual_identity": 80},
                        "screenshot_capture": {
                            "version": "screenshot_capture_v1",
                            "capture": {
                                "success": True,
                                "status": "captured",
                                "source": "playwright",
                                "screenshot_url": "file:///tmp/db-capture.png",
                            },
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_lab(manifest_path, output_root=tmp_path / "out")
    capture = result["summary"]["results"][0]["diagnosis"]["capture"]

    assert capture["available"] is True
    assert capture["quality"] == "good"


def test_visual_diagnosis_lab_can_derive_visual_evidence_from_local_screenshot(tmp_path):
    screenshot = tmp_path / "shot.png"
    _write_png(screenshot, 80, 60, _dense_pixels(80, 60))
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "brands": [
                    {
                        "brand_name": "Screenshot Only",
                        "website_url": "https://screenshot-only.example",
                        "category_hint": "ecommerce retail",
                        "derive_visual_signature_from_screenshot": True,
                        "coherence_breakdown": {"visual_identity": 78},
                        "screenshot_capture": {
                            "screenshot_url": f"file://{screenshot}",
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
    diagnosis = result["summary"]["results"][0]["diagnosis"]

    assert diagnosis["status"] in {"usable", "limited"}
    assert diagnosis["diagnosis"]["reference_profile"] == "ecommerce_mass_market"
    assert diagnosis["diagnosis"]["identity_read"] == "commerce_clear"
    assert "weak_cta_weight" not in diagnosis["signals"]["antipatterns"]
    assert "raw_inputs:screenshot_vision_lab" in diagnosis["evidence_refs"]
    assert "raw_inputs:visual_signature" not in diagnosis["evidence_refs"]


def test_visual_diagnosis_labels_viewport_obstruction_separately_from_capture_failure():
    payload = _visual_signature_payload()
    payload["vision"]["viewport_obstruction"] = {"present": True, "type": "cookie_banner"}

    diagnosis = build_visual_diagnosis(
        brand_name="Obstructed",
        website_url="https://obstructed.example",
        screenshot_capture={
            "screenshot_url": "file:///tmp/obstructed.png",
            "capture_type": "viewport",
            "quality": "usable",
        },
        visual_signature_payload=payload,
        coherence_breakdown={"visual_identity": 80},
    ).to_dict()

    assert "viewport_obstruction_cookie_banner" in diagnosis["signals"]["antipatterns"]
    assert "capture_not_evaluable" not in diagnosis["signals"]["antipatterns"]
