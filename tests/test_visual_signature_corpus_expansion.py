from __future__ import annotations

import json
from pathlib import Path

from src.visual_signature.corpus_expansion import (
    assess_corpus_expansion_bundle,
    build_corpus_expansion_manifest,
    build_corpus_expansion_manifest_markdown,
    build_corpus_expansion_metrics,
    build_corpus_expansion_review_queue,
    build_default_corpus_expansion_seed,
    corpus_expansion_metrics_markdown,
    validate_corpus_expansion_bundle,
    write_corpus_expansion_bundle,
)


def test_current_small_bundle_is_not_ready(tmp_path: Path) -> None:
    outputs = write_corpus_expansion_bundle(output_root=tmp_path)
    manifest = json.loads(Path(outputs["corpus_expansion_manifest_json"]).read_text(encoding="utf-8"))

    assert manifest["readiness_scope"] == "human_review_scaling"
    assert manifest["readiness_status"] == "not_ready"
    assert manifest["current_capture_count"] == 5
    assert manifest["reviewed_capture_count"] == 2

    assessment = assess_corpus_expansion_bundle(tmp_path)
    assert assessment.readiness_status == "not_ready"
    assert "small_sample_size" in assessment.block_reasons
    assert "insufficient_category_depth" in assessment.block_reasons


def test_valid_larger_bundle_can_be_ready(tmp_path: Path) -> None:
    seed_items = _build_ready_seed()
    outputs = write_corpus_expansion_bundle(
        output_root=tmp_path,
        target_capture_count=24,
        seed_items=seed_items,
        pilot_run_id="visual-signature-corpus-expansion-ready-test",
    )
    manifest = json.loads(Path(outputs["corpus_expansion_manifest_json"]).read_text(encoding="utf-8"))
    metrics = json.loads(Path(outputs["pilot_metrics_json"]).read_text(encoding="utf-8"))

    assert manifest["readiness_status"] == "ready"
    assert metrics["readiness_status"] == "ready"
    assert manifest["current_capture_count"] == 24
    assert manifest["reviewed_capture_count"] == 24
    assert validate_corpus_expansion_bundle(tmp_path) == []


def test_invalid_bundle_returns_not_ready(tmp_path: Path) -> None:
    outputs = write_corpus_expansion_bundle(output_root=tmp_path)
    queue_path = Path(outputs["review_queue_json"])
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    payload["queue_items"][0]["queue_state"] = "invalid_state"
    queue_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assessment = assess_corpus_expansion_bundle(tmp_path)
    assert assessment.readiness_status == "not_ready"
    assert "bundle_validation_failed" in assessment.block_reasons
    assert validate_corpus_expansion_bundle(tmp_path)


def test_high_contradiction_rate_blocks_readiness(tmp_path: Path) -> None:
    seed_items = _build_ready_seed(contradicted_every=3)
    outputs = write_corpus_expansion_bundle(
        output_root=tmp_path,
        target_capture_count=24,
        seed_items=seed_items,
        pilot_run_id="visual-signature-corpus-expansion-contradiction-test",
    )
    manifest = json.loads(Path(outputs["corpus_expansion_manifest_json"]).read_text(encoding="utf-8"))

    assert manifest["readiness_status"] == "not_ready"
    assert manifest["contradiction_rate"] > 0.25


def test_insufficient_confidence_spread_blocks_readiness(tmp_path: Path) -> None:
    seed_items = _build_ready_seed(confidence_bucket="high")
    outputs = write_corpus_expansion_bundle(
        output_root=tmp_path,
        target_capture_count=24,
        seed_items=seed_items,
        pilot_run_id="visual-signature-corpus-expansion-confidence-test",
    )
    manifest = json.loads(Path(outputs["corpus_expansion_manifest_json"]).read_text(encoding="utf-8"))
    assessment = assess_corpus_expansion_bundle(tmp_path)

    assert manifest["readiness_status"] == "not_ready"
    assert "insufficient_confidence_spread" in assessment.block_reasons


def test_markdown_contains_block_reasons(tmp_path: Path) -> None:
    outputs = write_corpus_expansion_bundle(output_root=tmp_path)
    markdown = Path(outputs["corpus_expansion_manifest_md"]).read_text(encoding="utf-8")

    assert "Scope evaluated: `human_review_scaling`" in markdown
    assert "This result applies only to the evaluated scope." in markdown
    assert "It does not imply production, scoring, runtime, provider-pilot, or model-training readiness." in markdown
    assert "## Block Reasons" in markdown
    assert "small_sample_size" in markdown


def test_metrics_and_manifest_share_counts(tmp_path: Path) -> None:
    outputs = write_corpus_expansion_bundle(output_root=tmp_path)
    manifest = json.loads(Path(outputs["corpus_expansion_manifest_json"]).read_text(encoding="utf-8"))
    metrics = json.loads(Path(outputs["pilot_metrics_json"]).read_text(encoding="utf-8"))

    assert manifest["current_capture_count"] == metrics["current_capture_count"]
    assert manifest["reviewed_capture_count"] == metrics["reviewed_capture_count"]
    assert manifest["category_distribution"] == metrics["category_distribution"]
    assert manifest["confidence_distribution"] == metrics["confidence_distribution"]
    assert manifest["queue_state_distribution"] == metrics["queue_state_distribution"]
    assert manifest["readiness_scope"] == metrics["readiness_scope"]
    assert manifest["readiness_status"] == metrics["readiness_status"]


def test_default_bundle_outputs_are_present(tmp_path: Path) -> None:
    outputs = write_corpus_expansion_bundle(output_root=tmp_path)

    for key in ("corpus_expansion_manifest_json", "corpus_expansion_manifest_md", "review_queue_json", "pilot_metrics_json"):
        assert Path(outputs[key]).exists()


def test_metrics_markdown_mentions_evidence_only() -> None:
    queue = build_corpus_expansion_review_queue(pilot_run_id="test-pilot")
    metrics = build_corpus_expansion_metrics(queue)
    markdown = corpus_expansion_metrics_markdown(metrics)

    assert "Evidence-only: yes" in markdown
    assert "No scoring integration: yes" in markdown
    assert "No runtime enablement: yes" in markdown
    assert "No model-training enablement: yes" in markdown


def test_manifest_markdown_mentions_limitations() -> None:
    queue = build_corpus_expansion_review_queue(pilot_run_id="test-pilot")
    metrics = build_corpus_expansion_metrics(queue)
    markdown = build_corpus_expansion_manifest_markdown(
        build_corpus_expansion_manifest(queue, metrics), metrics
    )

    assert "This pilot is sized for 20-50 reviewed captures." in markdown
    assert "Readiness remains `not_ready` until the reviewed corpus is expanded." in markdown


def _build_ready_seed(
    *,
    contradicted_every: int | None = None,
    confidence_bucket: str | None = None,
) -> list[dict[str, object]]:
    categories = ["SaaS", "editorial/media", "AI-native", "ecommerce"]
    confidence_buckets = ["low", "medium", "high"]
    items: list[dict[str, object]] = []
    for index in range(24):
        category = categories[index % len(categories)]
        confidence = confidence_bucket or confidence_buckets[index % len(confidence_buckets)]
        review_outcome = "confirmed"
        if contradicted_every and (index + 1) % contradicted_every == 0:
            review_outcome = "contradicted"
        items.append(
            {
                "queue_id": f"queue_{index + 1}",
                "capture_id": f"capture_{index + 1}",
                "brand_name": f"Brand {index + 1}",
                "website_url": f"https://example{index + 1}.com",
                "category": category,
                "queue_state": "reviewed",
                "review_outcome": review_outcome,
                "confidence_bucket": confidence,
                "reviewer_id": f"reviewer-{(index % 4) + 1}",
                "reviewed_at": f"2026-05-12T10:{index:02d}:00Z",
                "evidence_refs": ["examples/visual_signature/calibration_records.json"],
                "notes": ["synthetic-ready-capture"],
            }
        )
    return items
