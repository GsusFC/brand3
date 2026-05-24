from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.visual_signature.calibration import (
    build_calibration_readiness,
    build_calibration_summary,
    build_schema_versions,
    build_source_artifact_hashes,
    build_source_artifact_refs,
    calibration_readiness_markdown,
    export_calibration_bundle,
    validate_calibration_output_root,
    validate_calibration_readiness_result,
    write_calibration_readiness,
)
from src.visual_signature.calibration.calibration_models import (
    CalibrationRecord,
    PerceptionClaim,
    ReviewOutcome,
    confidence_bucket_for_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "calibration"
PHASE_ONE_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "phase_one"
PHASE_TWO_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "phase_two"
CAPTURE_MANIFEST = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "capture_manifest.json"
DISMISSAL_AUDIT = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "dismissal_audit.json"
BRAND_CATALOG = PROJECT_ROOT / "examples" / "visual_signature" / "calibration_brands.json"
CORPUS_MANIFEST = PROJECT_ROOT / "examples" / "visual_signature" / "calibration_corpus" / "corpus_manifest.json"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_calibration_readiness.py"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_current_small_bundle_returns_not_ready():
    result = build_calibration_readiness(CALIBRATION_ROOT, corpus_manifest_path=CORPUS_MANIFEST)

    assert result.status == "not_ready"
    assert result.readiness_scope == "broader_corpus_use"
    assert "small_sample_size" in result.block_reasons
    assert "insufficient_category_depth" in result.block_reasons
    assert result.bundle_valid is True
    assert result.summary_count_consistency is True
    assert result.record_count == 5
    assert result.reviewed_claims == 5
    assert result.confidence_bucket_coverage["high"].count == 5
    assert result.confidence_bucket_coverage["low"].count == 0


def test_synthetic_larger_bundle_can_be_ready(tmp_path: Path):
    bundle_root = _build_ready_bundle(tmp_path)
    result = build_calibration_readiness(bundle_root, corpus_manifest_path=CORPUS_MANIFEST)

    assert result.status == "ready"
    assert result.block_reasons == []
    assert result.bundle_valid is True
    assert result.record_count == 15
    assert result.reviewed_claims == 15
    assert result.confidence_bucket_coverage["low"].count > 0
    assert result.confidence_bucket_coverage["medium"].count > 0
    assert result.confidence_bucket_coverage["high"].count > 0
    assert result.category_coverage["ecommerce"].count == 5
    assert result.category_coverage["SaaS"].count == 5
    assert result.category_coverage["media"].count == 5


def test_invalid_bundle_returns_not_ready(tmp_path: Path):
    bundle_root = _build_ready_bundle(tmp_path)
    (bundle_root / "calibration_summary.md").unlink()

    result = build_calibration_readiness(bundle_root, corpus_manifest_path=CORPUS_MANIFEST)

    assert result.status == "not_ready"
    assert "bundle_validation_failed" in result.block_reasons
    assert result.bundle_valid is False


def test_high_contradiction_rate_blocks_readiness(tmp_path: Path):
    bundle_root = _build_bundle(
        tmp_path,
        records=[
            _record(category="ecommerce", confidence=0.2, review_status="approved"),
            _record(category="ecommerce", confidence=0.55, review_status="approved"),
            _record(category="ecommerce", confidence=0.9, review_status="approved"),
            _record(category="ecommerce", confidence=0.2, review_status="approved"),
            _record(category="ecommerce", confidence=0.55, review_status="approved"),
            _record(category="SaaS", confidence=0.2, review_status="approved"),
            _record(category="SaaS", confidence=0.55, review_status="approved"),
            _record(category="SaaS", confidence=0.9, review_status="approved"),
            _record(category="SaaS", confidence=0.2, review_status="approved"),
            _record(category="SaaS", confidence=0.55, review_status="approved"),
            _record(category="media", confidence=0.2, review_status="rejected"),
            _record(category="media", confidence=0.2, review_status="rejected"),
            _record(category="media", confidence=0.2, review_status="rejected"),
            _record(category="media", confidence=0.2, review_status="rejected"),
            _record(category="media", confidence=0.2, review_status="rejected"),
        ],
    )
    result = build_calibration_readiness(bundle_root, corpus_manifest_path=CORPUS_MANIFEST)

    assert result.status == "not_ready"
    assert "contradiction_rate_too_high" in result.block_reasons
    assert result.contradiction_rate > result.minimum_thresholds_used.maximum_contradiction_rate


def test_insufficient_confidence_spread_blocks_readiness(tmp_path: Path):
    bundle_root = _build_bundle(
        tmp_path,
        records=[
            _record(category="ecommerce", confidence=0.9, review_status="approved")
            for _ in range(5)
        ]
        + [
            _record(category="SaaS", confidence=0.9, review_status="approved")
            for _ in range(5)
        ]
        + [
            _record(category="media", confidence=0.9, review_status="approved")
            for _ in range(5)
        ],
    )
    result = build_calibration_readiness(bundle_root, corpus_manifest_path=CORPUS_MANIFEST)

    assert result.status == "not_ready"
    assert "insufficient_confidence_spread" in result.block_reasons
    assert sum(1 for row in result.confidence_bucket_coverage.values() if row.count > 0) == 1


def test_markdown_export_contains_block_reasons():
    result = build_calibration_readiness(CALIBRATION_ROOT, corpus_manifest_path=CORPUS_MANIFEST)
    markdown = calibration_readiness_markdown(result)

    assert "Block Reasons" in markdown
    assert "Scope evaluated: `broader_corpus_use`" in markdown
    assert "This `ready` / `not_ready` result applies only to the scope above." in markdown
    assert "small_sample_size" in markdown
    assert "insufficient_category_depth" in markdown
    assert "Confidence Bucket Coverage" in markdown


def test_readiness_json_includes_scope():
    result = build_calibration_readiness(CALIBRATION_ROOT, corpus_manifest_path=CORPUS_MANIFEST)
    payload = result.model_dump(mode="json")

    assert payload["readiness_scope"] == "broader_corpus_use"
    assert payload["status"] == "not_ready"


def test_unsupported_scope_warns_without_reusing_default_thresholds():
    result = build_calibration_readiness(
        CALIBRATION_ROOT,
        corpus_manifest_path=CORPUS_MANIFEST,
        readiness_scope="provider_pilot_use",
    )

    assert result.readiness_scope == "provider_pilot_use"
    assert "unsupported_scope:provider_pilot_use" in result.warning_reasons
    assert "unsupported_scopes_do_not_reuse_broader_corpus_use_thresholds" in result.warning_reasons
    assert result.status == "not_ready"


def test_readiness_script_runs_end_to_end(tmp_path: Path):
    script = _load_script(SCRIPT_PATH, "visual_signature_calibration_readiness")
    output_json = tmp_path / "calibration_readiness.json"
    output_md = tmp_path / "calibration_readiness.md"

    assert (
        script.main(
            [
                "--bundle-root",
                str(CALIBRATION_ROOT),
                "--corpus-manifest",
                str(CORPUS_MANIFEST),
                "--output-json",
                str(output_json),
                "--output-md",
                str(output_md),
            ]
        )
        == 0
    )
    assert output_json.exists()
    assert output_md.exists()
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"] == "not_ready"
    assert payload["readiness_scope"] == "broader_corpus_use"
    assert "small_sample_size" in payload["block_reasons"]
    assert validate_calibration_readiness_result(payload) == []


def _build_ready_bundle(tmp_path: Path) -> Path:
    records = []
    categories = ["ecommerce", "SaaS", "media"]
    confidences = [0.2, 0.55, 0.9, 0.2, 0.55]
    for category in categories:
        for index, confidence in enumerate(confidences, start=1):
            records.append(
                _record(
                    category=category,
                    confidence=confidence,
                    review_status="approved",
                    capture_suffix=f"{category}-{index}",
                )
            )
    return _build_bundle(tmp_path, records=records)


def _build_bundle(tmp_path: Path, *, records: list[CalibrationRecord]) -> Path:
    bundle_root = tmp_path / "calibration"
    phase_one_root = tmp_path / "phase_one"
    phase_two_root = tmp_path / "phase_two"
    phase_one_root.mkdir(parents=True, exist_ok=True)
    phase_two_root.mkdir(parents=True, exist_ok=True)
    summary = build_calibration_summary(
        records,
        calibration_run_id="synthetic-readiness-run",
        generated_at=datetime(2026, 5, 12, 10, 45, 0, tzinfo=timezone.utc),
        source_phase_one_root=str(phase_one_root),
        source_phase_two_root=str(phase_two_root),
        source_artifact_refs=build_source_artifact_refs(
            source_phase_one_root=str(phase_one_root),
            source_phase_two_root=str(phase_two_root),
        ),
        source_artifact_hashes=build_source_artifact_hashes(
            build_source_artifact_refs(
                source_phase_one_root=str(phase_one_root),
                source_phase_two_root=str(phase_two_root),
            )
        ),
        schema_versions=build_schema_versions(),
    )
    export_calibration_bundle(
        output_root=bundle_root,
        calibration_run_id="synthetic-readiness-run",
        records=records,
        summary=summary,
        source_phase_one_root=str(phase_one_root),
        source_phase_two_root=str(phase_two_root),
    )
    assert validate_calibration_output_root(bundle_root) == []
    return bundle_root


def _record(
    *,
    category: str,
    confidence: float,
    review_status: str,
    capture_suffix: str | None = None,
) -> CalibrationRecord:
    confidence_bucket = confidence_bucket_for_score(confidence)
    claim = PerceptionClaim(
        schema_version="visual-signature-calibration-claim-1",
        taxonomy_version="phase-zero-taxonomy-1",
        record_type="perception_claim",
        claim_id=f"claim_{capture_suffix or category}_{confidence_bucket}",
        claim_kind="capture_state",
        claim_value="RAW_STATE",
        confidence=confidence,
        confidence_bucket=confidence_bucket,
        evidence_refs=[f"evidence:{capture_suffix or category}"],
        lineage_refs=[f"lineage:{capture_suffix or category}"],
        notes=[f"synthetic:{category}"],
    )
    review = ReviewOutcome(
        schema_version="visual-signature-calibration-review-outcome-1",
        taxonomy_version="phase-zero-taxonomy-1",
        record_type="review_outcome",
        review_id=f"review_{capture_suffix or category}",
        capture_id=f"capture_{capture_suffix or category}",
        reviewer_id="reviewer-1",
        reviewed_at=datetime(2026, 5, 12, 10, 45, 0, tzinfo=timezone.utc),
        review_status=review_status,  # type: ignore[arg-type]
        visually_supported="yes",
        unsupported_inference_present=False,
        uncertainty_accepted=True,
        notes=[f"synthetic-review:{category}"],
    )
    agreement_state = "confirmed" if review_status == "approved" else "contradicted"
    uncertainty_alignment = "underconfident" if confidence_bucket == "low" else "calibrated"
    if agreement_state == "contradicted" and confidence_bucket == "high":
        uncertainty_alignment = "overconfident"
    return CalibrationRecord(
        schema_version="visual-signature-calibration-record-1",
        taxonomy_version="phase-zero-taxonomy-1",
        record_type="calibration_record",
        calibration_id=f"calibration_{capture_suffix or category}",
        capture_id=f"capture_{capture_suffix or category}",
        brand_name=f"{category.title()} Brand",
        website_url=f"https://{category}.example.com",
        category=category,
        claim=claim,
        review_outcome=review,
        agreement_state=agreement_state,  # type: ignore[arg-type]
        confidence_bucket=confidence_bucket,
        uncertainty_alignment=uncertainty_alignment,  # type: ignore[arg-type]
        evidence_refs=[f"evidence:{capture_suffix or category}"],
        lineage_refs=[f"lineage:{capture_suffix or category}"],
        source_breakdown={
            "phase_one_state": 1,
            "phase_one_eligibility": 1,
            "phase_one_transition_records": 1,
            "phase_one_mutation_audit": 0,
            "phase_two_review": 1,
            "capture_manifest": 0,
            "dismissal_audit": 0,
            "affordance_targets": 0,
        },
        diagnostics={"synthetic": True},
        notes=[f"synthetic-record:{category}"],
    )
