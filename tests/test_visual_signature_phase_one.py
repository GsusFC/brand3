from __future__ import annotations

from pathlib import Path

from src.visual_signature.phase_one import (
    PHASE_ONE_ROOT,
    build_phase_one_bundle,
    export_phase_one_bundle,
    load_phase_one_sources,
    validate_phase_one_output_root,
)
from src.visual_signature.phase_one.types import PhaseOneSourceCapture
from src.visual_signature.phase_zero.validation import validate_record_schema


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "examples" / "visual_signature" / "phase_one" / "fixtures"


def test_successful_conversion_from_fixture_to_phase_zero_records(tmp_path: Path) -> None:
    sources = load_phase_one_sources(
        FIXTURE_ROOT / "capture_manifest.fixture.json",
        FIXTURE_ROOT / "dismissal_audit.fixture.json",
    )
    assert len(sources) == 1

    bundle = build_phase_one_bundle(sources[0])
    assert not bundle.validation_errors
    assert bundle.mutation_audit_record is not None
    assert bundle.dataset_eligibility_record["record_type"] == "dataset_eligibility"
    assert bundle.dataset_eligibility_record["review_required"] is True

    records = [
        *bundle.observation_records,
        bundle.state_record,
        *bundle.transition_records,
        bundle.mutation_audit_record,
        bundle.dataset_eligibility_record,
    ]
    for record in records:
        if record is None:
            continue
        assert validate_record_schema(record) == []


def test_missing_raw_evidence_blocks_eligibility() -> None:
    source = _source(
        brand_name="No Raw",
        raw_screenshot_path=None,
        perceptual_state="RAW_STATE",
        raw_viewport_metrics={"composition_confidence": 0.95, "viewport_visual_density": "sparse"},
        before_obstruction={"present": False, "confidence": 1.0, "severity": "minor", "type": "none"},
        perceptual_transitions=[],
    )
    bundle = build_phase_one_bundle(source)
    assert bundle.dataset_eligibility_record["eligible"] is False
    assert "raw_evidence_missing" in bundle.dataset_eligibility_record["blocked_reasons"]


def test_mutation_without_lineage_blocks_eligibility() -> None:
    source = _source(
        brand_name="Broken Mutation",
        raw_screenshot_path="/tmp/raw.png",
        clean_attempt_screenshot_path=None,
        perceptual_state="REVIEW_REQUIRED_STATE",
        raw_viewport_metrics={"composition_confidence": 0.9, "viewport_visual_density": "dense"},
        before_obstruction={"present": True, "confidence": 0.9, "severity": "blocking", "type": "newsletter_modal"},
        perceptual_transitions=[],
        mutation_audit={
            "mutation_id": "mut_001",
            "mutation_type": "newsletter_modal_dismissal",
            "before_state": "ELIGIBLE_FOR_SAFE_INTERVENTION",
            "after_state": "REVIEW_REQUIRED_STATE",
            "attempted": True,
            "successful": False,
            "reversible": True,
            "risk_level": "low",
            "trigger": "close",
            "evidence_preserved": True,
            "before_artifact_ref": "/tmp/raw.png",
            "after_artifact_ref": None,
            "integrity_notes": ["raw_viewport_preserved_as_primary_evidence"],
        },
    )
    bundle = build_phase_one_bundle(source)
    assert bundle.dataset_eligibility_record["eligible"] is False
    assert "mutation_lineage_missing" in bundle.dataset_eligibility_record["blocked_reasons"]


def test_unknown_observation_key_fails_validation() -> None:
    errors = validate_record_schema(
        {
            "schema_version": "phase-zero-perceptual-observation-1",
            "taxonomy_version": "phase-zero-taxonomy-1",
            "record_type": "perceptual_observation",
            "record_id": "obs_1",
            "created_at": "2026-05-11T10:00:00Z",
            "capture_id": "cap_1",
            "brand_name": "Example",
            "website_url": "https://example.com",
            "perception_layer": "functional",
            "observation_key": "unknown_signal",
            "observation_value": "none",
            "confidence": 0.9,
            "uncertainty": {
                "schema_version": "phase-zero-uncertainty-profile-1",
                "taxonomy_version": "phase-zero-taxonomy-1",
                "record_type": "uncertainty_profile",
                "confidence": 0.9,
                "confidence_level": "high",
                "known_unknowns": [],
                "uncertainty_reasons": [],
                "reviewer_required": False,
                "unsupported_inference": False,
            },
            "evidence_refs": ["/tmp/raw.png"],
            "reasoning_trace": {
                "schema_version": "phase-zero-reasoning-trace-1",
                "taxonomy_version": "phase-zero-taxonomy-1",
                "record_type": "reasoning_trace",
                "trace_id": "trace_1",
                "created_at": "2026-05-11T10:00:00Z",
                "summary": "Example",
                "statements": [
                    {
                        "statement": "Example",
                        "confidence": 0.9,
                        "evidence_refs": ["/tmp/raw.png"],
                        "warnings": [],
                    }
                ],
                "unsupported_inference_warnings": [],
                "review_required": False,
                "lineage_refs": [],
            },
            "lineage_refs": [],
        }
    )
    assert any("unknown_observation_key" in error for error in errors)


def test_reviewer_required_state_is_not_exportable_until_reviewed() -> None:
    sources = load_phase_one_sources(
        FIXTURE_ROOT / "capture_manifest.fixture.json",
        FIXTURE_ROOT / "dismissal_audit.fixture.json",
    )
    bundle = build_phase_one_bundle(sources[0])
    assert bundle.state_record["perceptual_state"] == "REVIEW_REQUIRED_STATE"
    assert bundle.dataset_eligibility_record["review_required"] is True
    assert bundle.dataset_eligibility_record["review_completed"] is False
    assert bundle.dataset_eligibility_record["eligible"] is False
    assert "review_required_not_completed" in bundle.dataset_eligibility_record["blocked_reasons"]


def test_generated_records_pass_schema_validation(tmp_path: Path) -> None:
    sources = load_phase_one_sources(
        FIXTURE_ROOT / "capture_manifest.fixture.json",
        FIXTURE_ROOT / "dismissal_audit.fixture.json",
    )
    bundle = build_phase_one_bundle(sources[0])
    manifest = export_phase_one_bundle(
        output_root=tmp_path / "phase_one",
        bundles=[bundle],
        source_capture_manifest_path=str(FIXTURE_ROOT / "capture_manifest.fixture.json"),
        source_dismissal_audit_path=str(FIXTURE_ROOT / "dismissal_audit.fixture.json"),
    )
    assert manifest.validation_passed is True
    assert validate_phase_one_output_root(tmp_path / "phase_one") == []


def _source(**overrides: object) -> PhaseOneSourceCapture:
    base = dict(
        brand_name="Example",
        website_url="https://example.com",
        capture_id="cap_1",
        captured_at="2026-05-11T10:00:00Z",
        viewport_width=1440,
        viewport_height=900,
        raw_screenshot_path="/tmp/raw.png",
        page_url="https://example.com",
        source_manifest_path="/tmp/capture_manifest.json",
        source_dismissal_audit_path=None,
        perceptual_state="RAW_STATE",
        perceptual_transitions=[],
        mutation_audit=None,
        raw_viewport_metrics={"composition_confidence": 0.95, "viewport_visual_density": "sparse"},
        before_obstruction={"present": False, "confidence": 1.0, "severity": "minor", "type": "none"},
        after_obstruction=None,
        dismissal_eligibility="none",
        dismissal_block_reason="none",
        dismissal_attempted=False,
        dismissal_successful=False,
        clean_attempt_screenshot_path=None,
        capture_variant="raw_viewport",
        clean_attempt_capture_variant=None,
        capture_type="viewport",
    )
    base.update(overrides)
    return PhaseOneSourceCapture(**base)
