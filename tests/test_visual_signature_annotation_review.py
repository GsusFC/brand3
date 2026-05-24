from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.visual_signature.annotations import annotate_visual_signature
from src.visual_signature.annotations.review import (
    ReviewRecord,
    TargetReviewDecision,
    build_review_reports,
    build_review_sample,
    load_review_batch,
    load_review_records,
    save_review_batch,
    save_review_records,
)
from src.visual_signature.annotations.review.persistence import validate_review_record


SAMPLE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "visual_signature_sample_annotation_reviews.py"
REPORT_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "visual_signature_build_review_reports.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _payload(name: str, category: str, *, confidence: float = 0.8, flags: list[str] | None = None) -> dict:
    payload = {
        "brand_name": name,
        "website_url": f"https://{name.lower().replace(' ', '-')}.example",
        "interpretation_status": "interpretable",
        "calibration": {"expected_category": category},
        "logo": {"logo_detected": True},
        "assets": {"image_count": 2},
        "vision": {
            "viewport_visual_density": "balanced",
            "screenshot": {"available": True, "quality": "usable", "path": "/tmp/mock.png"},
            "agreement": {
                "agreement_level": "low" if flags else "high",
                "disagreement_flags": flags or [],
                "disagreement_severity_score": 0.9 if flags else 0.0,
            },
        },
    }
    annotated = annotate_visual_signature(visual_signature_payload=payload)
    annotated["annotations"]["overall_confidence"]["score"] = confidence
    return annotated


def _write_annotations(root: Path) -> None:
    root.mkdir()
    rows = [
        _payload("High SaaS", "saas", confidence=0.9),
        _payload("Low SaaS", "saas", confidence=0.2),
        _payload("Disagree AI", "ai_native", confidence=0.7, flags=["dom_density_disagrees_with_viewport_first_fold"]),
        _payload("Media", "editorial_media", confidence=0.75),
    ]
    for row in rows:
        slug = row["brand_name"].lower().replace(" ", "-")
        (root / f"{slug}.json").write_text(json.dumps(row), encoding="utf-8")


def _review_record(reviewer_id: str, annotation_id: str, *, disagree: bool = False) -> ReviewRecord:
    return ReviewRecord(
        reviewer_id=reviewer_id,
        annotation_id=annotation_id,
        brand_name="High SaaS",
        website_url="https://high-saas.example",
        expected_category="saas",
        annotation_path="/tmp/high-saas.json",
        overall_usefulness=4,
        target_reviews={
            "logo_prominence": TargetReviewDecision(
                target="logo_prominence",
                decision="disagree" if disagree else "agree",
                usefulness=4,
                hallucination=disagree,
                uncertainty="medium" if disagree else "low",
                notes="fixture review",
            ),
            "imagery_style": TargetReviewDecision(
                target="imagery_style",
                decision="uncertain",
                usefulness=3,
                hallucination=False,
                uncertainty="high",
            ),
        },
    )


def test_review_sample_selects_required_sampling_reasons(tmp_path):
    annotation_dir = tmp_path / "annotations"
    _write_annotations(annotation_dir)

    batch = build_review_sample(
        annotation_dir=annotation_dir,
        output_size=4,
        high_confidence_count=1,
        low_confidence_count=1,
        disagreement_heavy_count=1,
        category_diverse_count=2,
    )

    reasons = {reason for item in batch.items for reason in item.sampling_reasons}
    assert "high_confidence_annotation" in reasons
    assert "low_confidence_annotation" in reasons
    assert "disagreement_heavy_case" in reasons
    assert "category_diverse_sample" in reasons
    assert len(batch.items) == 4


def test_review_batch_and_records_persist_round_trip(tmp_path):
    annotation_dir = tmp_path / "annotations"
    _write_annotations(annotation_dir)
    batch = build_review_sample(annotation_dir=annotation_dir, output_size=2)
    batch_path = tmp_path / "review_sample.json"
    records_path = tmp_path / "review_records.json"

    save_review_batch(batch_path, batch)
    loaded_batch = load_review_batch(batch_path)
    records = [_review_record("reviewer-a", loaded_batch.items[0].annotation_id)]
    save_review_records(records_path, records)
    loaded_records = load_review_records(records_path)

    assert loaded_batch.items[0].annotation_id == batch.items[0].annotation_id
    assert loaded_records[0].reviewer_id == "reviewer-a"
    assert validate_review_record(loaded_records[0])["valid"] is True


def test_review_reports_include_agreement_hallucination_uncertainty_and_usefulness():
    records = [
        _review_record("reviewer-a", "high-saas"),
        _review_record("reviewer-b", "high-saas", disagree=True),
    ]

    reports = build_review_reports(records)

    agreement = reports["reviewer_agreement_report"]
    target_quality = reports["target_quality_summary"]
    hallucination = reports["hallucination_summary"]
    usefulness = reports["annotation_usefulness_summary"]
    assert agreement["reviewer_count"] == 2
    assert agreement["comparable_annotation_targets"] == 2
    assert agreement["conflicts"]
    assert target_quality["logo_prominence"]["hallucination_rate"] == 0.5
    assert hallucination["hallucination_count"] == 1
    assert usefulness["high_uncertainty_rate"] > 0


def test_review_scripts_write_sample_and_reports(tmp_path):
    annotation_dir = tmp_path / "annotations"
    _write_annotations(annotation_dir)
    sample_script = _load_script(SAMPLE_SCRIPT, "visual_signature_sample_annotation_reviews")
    report_script = _load_script(REPORT_SCRIPT, "visual_signature_build_review_reports")
    sample_path = tmp_path / "review_sample.json"
    records_path = tmp_path / "review_records.json"
    reports_dir = tmp_path / "reports"

    assert sample_script.main([
        "--annotation-dir",
        str(annotation_dir),
        "--output",
        str(sample_path),
        "--size",
        "3",
    ]) == 0
    sample = load_review_batch(sample_path)
    save_review_records(records_path, [_review_record("reviewer-a", sample.items[0].annotation_id)])

    assert report_script.main(["--input", str(records_path), "--output-dir", str(reports_dir)]) == 0
    assert (reports_dir / "reviewer_agreement_report.json").exists()
    assert (reports_dir / "target_quality_summary.md").exists()
    assert (reports_dir / "hallucination_summary.json").exists()
    assert (reports_dir / "annotation_usefulness_summary.md").exists()
