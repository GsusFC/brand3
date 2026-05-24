from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.visual_signature.annotations.review.viewer import (
    append_viewer_review_record,
    build_viewer_review_record,
    create_review_viewer_app,
    load_review_cases,
    load_viewer_review_records,
)


def _write_fixture(tmp_path: Path) -> tuple[Path, Path, str]:
    screenshot = tmp_path / "screenshot.png"
    screenshot.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    annotation_path = tmp_path / "linear.json"
    payload = {
        "brand_name": "Linear",
        "website_url": "https://linear.app",
        "calibration": {"expected_category": "saas"},
        "vision": {
            "screenshot": {
                "available": True,
                "quality": "usable",
                "path": str(screenshot),
            }
        },
        "annotations": {
            "status": "annotated",
            "overall_confidence": {"score": 0.74},
            "targets": {
                "logo_prominence": {
                    "label": "clear",
                    "confidence": 0.8,
                    "evidence": ["Header wordmark is visible."],
                    "source": "viewport_screenshot",
                    "limitations": [],
                },
                "human_presence": {
                    "label": "unknown",
                    "confidence": 0.2,
                    "evidence": [],
                    "source": "viewport_screenshot",
                    "limitations": ["No people visible."],
                },
            },
        },
    }
    annotation_path.write_text(json.dumps(payload), encoding="utf-8")
    sample_path = tmp_path / "review_sample.json"
    sample_path.write_text(
        json.dumps(
            {
                "version": "visual-signature-review-batch-1",
                "sample_strategy": "fixture",
                "source_dir": str(tmp_path),
                "items": [
                    {
                        "annotation_id": "linear",
                        "brand_name": "Linear",
                        "website_url": "https://linear.app",
                        "expected_category": "saas",
                        "annotation_path": str(annotation_path),
                        "sampling_reasons": ["high_confidence_annotation"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return sample_path, screenshot, "linear"


def test_review_viewer_loads_review_sample_cases(tmp_path):
    sample_path, _, _ = _write_fixture(tmp_path)

    cases = load_review_cases(sample_path)

    assert len(cases) == 1
    assert cases[0].brand_name == "Linear"
    assert cases[0].expected_category == "saas"
    assert cases[0].targets["logo_prominence"]["label"] == "clear"


def test_review_viewer_serves_case_and_saves_review_record(tmp_path):
    sample_path, _, annotation_id = _write_fixture(tmp_path)
    records_path = tmp_path / "review_records.json"
    app = create_review_viewer_app(sample_path=sample_path, review_records_path=records_path)
    client = TestClient(app)

    index_response = client.get("/")
    case_response = client.get(f"/case/{annotation_id}")
    screenshot_response = client.get(f"/case/{annotation_id}/screenshot")
    post_response = client.post(
        f"/case/{annotation_id}/review",
        data={
            "reviewer_id": "reviewer-a",
            "visually_supported": "yes",
            "useful": "useful",
            "hallucination_or_overreach": "no",
            "most_reliable_target": "logo_prominence",
            "most_confusing_target": "human_presence",
            "adds_value_beyond_heuristics": "yes",
            "reviewer_notes": "Logo label is supported by the viewport.",
        },
        follow_redirects=False,
    )

    assert index_response.status_code == 200
    assert "visual signature annotation review" in index_response.text
    assert case_response.status_code == 200
    assert "Header wordmark is visible." in case_response.text
    assert screenshot_response.status_code == 200
    assert screenshot_response.headers["content-type"] == "image/png"
    assert post_response.status_code == 303
    records = load_viewer_review_records(records_path)
    assert len(records) == 1
    assert records[0]["annotation_id"] == "linear"
    assert records[0]["visually_supported"] == "yes"
    assert records[0]["reviewer_notes"] == "Logo label is supported by the viewport."


def test_review_viewer_supports_spanish_language_selector(tmp_path):
    sample_path, _, annotation_id = _write_fixture(tmp_path)
    records_path = tmp_path / "review_records.json"
    app = create_review_viewer_app(sample_path=sample_path, review_records_path=records_path)
    client = TestClient(app)

    index_response = client.get("/?lang=es")
    case_response = client.get(f"/case/{annotation_id}?lang=es")
    post_response = client.post(
        f"/case/{annotation_id}/review",
        data={
            "reviewer_id": "reviewer-a",
            "visually_supported": "partial",
            "useful": "neutral",
            "hallucination_or_overreach": "no",
            "most_reliable_target": "logo_prominence",
            "most_confusing_target": "human_presence",
            "adds_value_beyond_heuristics": "unsure",
            "reviewer_notes": "La anotación está parcialmente soportada.",
            "lang": "es",
        },
        follow_redirects=False,
    )

    assert index_response.status_code == 200
    assert 'lang="es"' in index_response.text
    assert "revisión de anotaciones de Visual Signature" in index_response.text
    assert "/?lang=en" in index_response.text
    assert "/?lang=es" in index_response.text
    assert case_response.status_code == 200
    assert "revision_rapida" in case_response.text
    assert "soporte_visual" in case_response.text
    assert "prominencia_logo" in case_response.text
    assert post_response.status_code == 303
    assert post_response.headers["location"] == f"/case/{annotation_id}?saved=1&lang=es"


def test_review_viewer_persistence_helpers_append_records(tmp_path):
    sample_path, _, _ = _write_fixture(tmp_path)
    case = load_review_cases(sample_path)[0]
    path = tmp_path / "review_records.json"
    record = build_viewer_review_record(
        case,
        reviewer_id="reviewer-a",
        visually_supported="partial",
        useful="neutral",
        hallucination_or_overreach="yes",
        most_reliable_target="logo_prominence",
        most_confusing_target="human_presence",
        adds_value_beyond_heuristics="unsure",
        reviewer_notes="Human presence is unsupported by screenshot.",
    )

    append_viewer_review_record(path, record)
    append_viewer_review_record(path, record)

    records = load_viewer_review_records(path)
    assert len(records) == 2
    assert records[0]["hallucination_or_overreach"] == "yes"
