from __future__ import annotations

from pathlib import Path

from src.visual_signature.phase_two import (
    PHASE_TWO_ROOT,
    build_phase_two_bundle,
    export_phase_two_bundle,
    join_phase_one_and_reviews,
    load_phase_one_eligibility_records,
    load_review_records,
    validate_phase_two_output_root,
)
from src.visual_signature.phase_zero.validation import validate_record_schema


PHASE_ONE_ROOT = Path(__file__).resolve().parents[1] / "examples" / "visual_signature" / "phase_one"


def test_approved_review_makes_capture_eligible_when_gates_pass() -> None:
    phase_one = _phase_one_by_capture_id("the-verge")
    review = _review_by_capture_id("the-verge")

    bundle = build_phase_two_bundle(phase_one, review)

    assert bundle.review_record is not None
    assert bundle.reviewed_eligibility_record["eligible"] is True
    assert bundle.reviewed_eligibility_record["review_completed"] is True
    assert "review_required_not_completed" not in bundle.reviewed_eligibility_record["blocked_reasons"]
    assert validate_record_schema(bundle.reviewed_eligibility_record) == []


def test_rejected_review_blocks_eligibility() -> None:
    phase_one = _phase_one_by_capture_id("linear")
    review = _review_by_capture_id("linear")

    bundle = build_phase_two_bundle(phase_one, review)

    assert bundle.review_record is not None
    assert bundle.reviewed_eligibility_record["eligible"] is False
    assert "review_rejected" in bundle.reviewed_eligibility_record["blocked_reasons"]


def test_needs_more_evidence_blocks_eligibility() -> None:
    phase_one = _phase_one_by_capture_id("openai")
    review = _review_by_capture_id("openai")

    bundle = build_phase_two_bundle(phase_one, review)

    assert bundle.review_record is not None
    assert bundle.reviewed_eligibility_record["eligible"] is False
    assert "needs_more_evidence" in bundle.reviewed_eligibility_record["blocked_reasons"]


def test_unsupported_inference_blocks_eligibility() -> None:
    phase_one = _phase_one_by_capture_id("allbirds")
    review = _review_by_capture_id("allbirds")
    review.unsupported_inference_present = True

    bundle = build_phase_two_bundle(phase_one, review)

    assert bundle.review_record is not None
    assert bundle.reviewed_eligibility_record["eligible"] is False
    assert "unsupported_inference_present" in bundle.reviewed_eligibility_record["blocked_reasons"]


def test_uncertainty_not_accepted_blocks_eligibility() -> None:
    phase_one = _phase_one_by_capture_id("allbirds")
    review = _review_by_capture_id("allbirds")
    review.uncertainty_accepted = False

    bundle = build_phase_two_bundle(phase_one, review)

    assert bundle.review_record is not None
    assert bundle.reviewed_eligibility_record["eligible"] is False
    assert "uncertainty_not_accepted" in bundle.reviewed_eligibility_record["blocked_reasons"]


def test_missing_review_blocks_eligibility() -> None:
    phase_one = _phase_one_by_capture_id("headspace")

    bundle = build_phase_two_bundle(phase_one, None)

    assert bundle.review_record is None
    assert bundle.reviewed_eligibility_record["eligible"] is False
    assert "missing_review_record" in bundle.reviewed_eligibility_record["blocked_reasons"]


def test_reviewed_exports_pass_schema_validation(tmp_path: Path) -> None:
    phase_one_records = load_phase_one_eligibility_records(PHASE_ONE_ROOT)
    review_records = load_review_records(PHASE_TWO_ROOT / "reviews" / "review_records.json")
    bundles = join_phase_one_and_reviews(phase_one_records, review_records)

    manifest = export_phase_two_bundle(
        output_root=tmp_path / "phase_two",
        bundles=bundles,
        source_phase_one_root=str(PHASE_ONE_ROOT),
        source_reviews_path=str(PHASE_TWO_ROOT / "reviews" / "review_records.json"),
    )

    assert manifest.validation_passed is True
    assert validate_phase_two_output_root(tmp_path / "phase_two") == []


def _phase_one_by_capture_id(capture_id: str) -> dict[str, object]:
    for record in load_phase_one_eligibility_records(PHASE_ONE_ROOT):
        if str(record.get("capture_id")) == capture_id:
            return record
    raise AssertionError(f"missing phase one record: {capture_id}")


def _review_by_capture_id(capture_id: str):
    for record in load_review_records(PHASE_TWO_ROOT / "reviews" / "review_records.json"):
        if record.capture_id == capture_id:
            return record
    raise AssertionError(f"missing review record: {capture_id}")
