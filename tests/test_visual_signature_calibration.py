from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.visual_signature.calibration import (
    build_calibration_records,
    build_calibration_summary,
    build_schema_versions,
    build_source_artifact_hashes,
    build_source_artifact_refs,
    export_calibration_bundle,
    validate_calibration_output_root,
)
from src.visual_signature.calibration.calibration_models import (
    CalibrationRecord,
    CalibrationSummary,
    validate_calibration_record,
    validate_calibration_summary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_calibration.py"
VALIDATE_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "visual_signature_calibration_validate.py"
PHASE_ONE_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "phase_one"
PHASE_TWO_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "phase_two"
CAPTURE_MANIFEST = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "capture_manifest.json"
DISMISSAL_AUDIT = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "dismissal_audit.json"
BRAND_CATALOG = PROJECT_ROOT / "examples" / "visual_signature" / "calibration_brands.json"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_calibration_records_from_real_phase_outputs():
    records = build_calibration_records(
        phase_one_root=PHASE_ONE_ROOT,
        phase_two_root=PHASE_TWO_ROOT,
        brand_catalog_path=BRAND_CATALOG,
        capture_manifest_path=CAPTURE_MANIFEST,
        dismissal_audit_path=DISMISSAL_AUDIT,
    )

    assert len(records) == 5
    by_brand = {record.brand_name: record for record in records}
    assert by_brand["Linear"].agreement_state == "confirmed"
    assert by_brand["OpenAI"].agreement_state == "unresolved"
    assert by_brand["The Verge"].agreement_state == "contradicted"
    assert by_brand["Allbirds"].agreement_state == "contradicted"
    assert by_brand["Headspace"].agreement_state == "confirmed"
    assert by_brand["Allbirds"].confidence_bucket == "high"
    assert by_brand["Allbirds"].uncertainty_alignment == "overconfident"
    assert by_brand["OpenAI"].uncertainty_alignment == "uncertainty_accepted"
    assert by_brand["Linear"].source_breakdown["phase_two_review"] == 1
    assert by_brand["Allbirds"].source_breakdown["phase_one_mutation_audit"] == 1
    assert by_brand["Allbirds"].diagnostics["capture_manifest"]["safe_to_dismiss_candidates_not_clicked"] == 1
    assert by_brand["Linear"].diagnostics["capture_manifest"]["safe_to_dismiss_candidates_not_clicked"] == 1


def test_confirmed_claim_uses_reviewed_outcome():
    record = _synthetic_record(claim_value="OBSTRUCTED_STATE", confidence=0.89, review_status="rejected")

    assert record.agreement_state == "confirmed"
    assert record.confidence_bucket == "high"
    assert record.uncertainty_alignment == "calibrated"


def test_contradicted_claim_is_reported():
    record = _synthetic_record(claim_value="OBSTRUCTED_STATE", confidence=0.89, review_status="approved")

    assert record.agreement_state == "contradicted"
    assert record.uncertainty_alignment == "overconfident"


def test_unresolved_claim_uses_needs_more_evidence():
    record = _synthetic_record(claim_value="OBSTRUCTED_STATE", confidence=0.65, review_status="needs_more_evidence")

    assert record.agreement_state == "unresolved"
    assert record.uncertainty_alignment == "uncertainty_accepted"


def test_missing_review_becomes_insufficient_review_not_contradiction():
    record = _synthetic_record(claim_value="OBSTRUCTED_STATE", confidence=0.65, review_status=None)

    assert record.agreement_state == "insufficient_review"
    assert record.uncertainty_alignment == "insufficient_data"


def test_high_confidence_contradiction_is_overconfident():
    record = _synthetic_record(claim_value="OBSTRUCTED_STATE", confidence=0.91, review_status="approved")

    assert record.agreement_state == "contradicted"
    assert record.confidence_bucket == "high"
    assert record.uncertainty_alignment == "overconfident"


def test_missing_review_does_not_become_contradiction():
    record = _synthetic_record(claim_value="OBSTRUCTED_STATE", confidence=0.91, review_status=None)

    assert record.agreement_state == "insufficient_review"
    assert record.agreement_state != "contradicted"


def test_export_json_and_markdown_summary(tmp_path: Path):
    records = build_calibration_records(
        phase_one_root=PHASE_ONE_ROOT,
        phase_two_root=PHASE_TWO_ROOT,
        brand_catalog_path=BRAND_CATALOG,
        capture_manifest_path=CAPTURE_MANIFEST,
        dismissal_audit_path=DISMISSAL_AUDIT,
    )
    summary = build_calibration_summary(
        records,
        calibration_run_id="test-run",
        generated_at=datetime(2026, 5, 11, 22, 17, 48, tzinfo=timezone.utc),
        source_phase_one_root=str(PHASE_ONE_ROOT),
        source_phase_two_root=str(PHASE_TWO_ROOT),
        source_capture_manifest_path=str(CAPTURE_MANIFEST),
        source_dismissal_audit_path=str(DISMISSAL_AUDIT),
        source_brand_catalog_path=str(BRAND_CATALOG),
        source_artifact_refs=build_source_artifact_refs(
            source_phase_one_root=str(PHASE_ONE_ROOT),
            source_phase_two_root=str(PHASE_TWO_ROOT),
            source_capture_manifest_path=str(CAPTURE_MANIFEST),
            source_dismissal_audit_path=str(DISMISSAL_AUDIT),
            source_brand_catalog_path=str(BRAND_CATALOG),
        ),
        source_artifact_hashes=build_source_artifact_hashes(
            build_source_artifact_refs(
                source_phase_one_root=str(PHASE_ONE_ROOT),
                source_phase_two_root=str(PHASE_TWO_ROOT),
                source_capture_manifest_path=str(CAPTURE_MANIFEST),
                source_dismissal_audit_path=str(DISMISSAL_AUDIT),
                source_brand_catalog_path=str(BRAND_CATALOG),
            )
        ),
        schema_versions=build_schema_versions(),
    )

    outputs = export_calibration_bundle(
        output_root=tmp_path / "calibration",
        calibration_run_id="test-run",
        records=records,
        summary=summary,
        source_phase_one_root=str(PHASE_ONE_ROOT),
        source_phase_two_root=str(PHASE_TWO_ROOT),
        source_capture_manifest_path=str(CAPTURE_MANIFEST),
        source_dismissal_audit_path=str(DISMISSAL_AUDIT),
        source_brand_catalog_path=str(BRAND_CATALOG),
    )

    assert Path(outputs["calibration_records_json"]).exists()
    assert Path(outputs["calibration_summary_json"]).exists()
    assert Path(outputs["calibration_summary_md"]).exists()
    assert Path(outputs["calibration_manifest_json"]).exists()
    assert validate_calibration_output_root(tmp_path / "calibration") == []
    assert validate_calibration_record(records[0].model_dump(mode="json")) == []
    assert validate_calibration_summary(summary.model_dump(mode="json")) == []

    records_payload = json.loads((tmp_path / "calibration" / "calibration_records.json").read_text(encoding="utf-8"))
    summary_payload = json.loads((tmp_path / "calibration" / "calibration_summary.json").read_text(encoding="utf-8"))
    manifest_payload = json.loads((tmp_path / "calibration" / "calibration_manifest.json").read_text(encoding="utf-8"))
    assert records_payload["record_count"] == 5
    assert summary_payload["total_claims"] == 5
    assert summary_payload["summary_count_consistency"] is True
    assert summary_payload["calibration_run_id"] == "test-run"
    assert manifest_payload["validation_status"] == "valid"
    assert manifest_payload["record_count"] == 5
    markdown = (tmp_path / "calibration" / "calibration_summary.md").read_text(encoding="utf-8")
    assert "Visual Signature Calibration Summary" in markdown
    assert "Evidence-only" in markdown


def test_category_and_source_breakdowns_present():
    records = build_calibration_records(
        phase_one_root=PHASE_ONE_ROOT,
        phase_two_root=PHASE_TWO_ROOT,
        brand_catalog_path=BRAND_CATALOG,
        capture_manifest_path=CAPTURE_MANIFEST,
        dismissal_audit_path=DISMISSAL_AUDIT,
    )
    summary = build_calibration_summary(
        records,
        calibration_run_id="test-run",
        generated_at=datetime(2026, 5, 11, 22, 17, 48, tzinfo=timezone.utc),
        source_phase_one_root=str(PHASE_ONE_ROOT),
        source_phase_two_root=str(PHASE_TWO_ROOT),
        source_capture_manifest_path=str(CAPTURE_MANIFEST),
        source_dismissal_audit_path=str(DISMISSAL_AUDIT),
        source_brand_catalog_path=str(BRAND_CATALOG),
        source_artifact_refs=build_source_artifact_refs(
            source_phase_one_root=str(PHASE_ONE_ROOT),
            source_phase_two_root=str(PHASE_TWO_ROOT),
            source_capture_manifest_path=str(CAPTURE_MANIFEST),
            source_dismissal_audit_path=str(DISMISSAL_AUDIT),
            source_brand_catalog_path=str(BRAND_CATALOG),
        ),
        source_artifact_hashes=build_source_artifact_hashes(
            build_source_artifact_refs(
                source_phase_one_root=str(PHASE_ONE_ROOT),
                source_phase_two_root=str(PHASE_TWO_ROOT),
                source_capture_manifest_path=str(CAPTURE_MANIFEST),
                source_dismissal_audit_path=str(DISMISSAL_AUDIT),
                source_brand_catalog_path=str(BRAND_CATALOG),
            )
        ),
        schema_versions=build_schema_versions(),
    )

    assert "ecommerce" in summary.category_breakdown
    assert "SaaS" in summary.category_breakdown
    assert "capture_state" in summary.claim_kind_breakdown
    assert summary.source_breakdown["phase_one_state"]["count"] == 5
    assert summary.source_breakdown["phase_two_review"]["count"] == 5
    assert summary.source_breakdown["dismissal_audit"]["count"] == 5
    assert summary.record_count == 5
    assert summary.summary_count_consistency is True
    assert summary.source_artifact_refs
    assert summary.source_artifact_hashes


def test_calibration_scripts_run_end_to_end(tmp_path: Path):
    generate = _load_script(SCRIPT_PATH, "visual_signature_calibration")
    validate = _load_script(VALIDATE_SCRIPT_PATH, "visual_signature_calibration_validate")
    output_root = tmp_path / "calibration"

    assert generate.main(
        [
            "--phase-one-root",
            str(PHASE_ONE_ROOT),
            "--phase-two-root",
            str(PHASE_TWO_ROOT),
            "--capture-manifest",
            str(CAPTURE_MANIFEST),
            "--dismissal-audit",
            str(DISMISSAL_AUDIT),
            "--brand-catalog",
            str(BRAND_CATALOG),
            "--output-root",
            str(output_root),
        ]
    ) == 0

    assert validate.main(["--output-root", str(output_root)]) == 0
    assert (output_root / "calibration_records.json").exists()
    assert (output_root / "calibration_summary.json").exists()
    assert (output_root / "calibration_summary.md").exists()
    assert (output_root / "calibration_manifest.json").exists()


def test_missing_summary_markdown_fails_validation(tmp_path: Path):
    output_root = _build_bundle(tmp_path)
    (output_root / "calibration_summary.md").unlink()
    errors = validate_calibration_output_root(output_root)
    assert "calibration_summary_md_missing" in errors


def test_record_count_mismatch_fails_validation(tmp_path: Path):
    output_root = _build_bundle(tmp_path)
    payload_path = output_root / "calibration_records.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["record_count"] = payload["record_count"] + 1
    payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_calibration_output_root(output_root)
    assert "records_count_mismatch" in errors or "summary_record_count_mismatch" in errors


def test_summary_total_mismatch_fails_validation(tmp_path: Path):
    output_root = _build_bundle(tmp_path)
    payload_path = output_root / "calibration_summary.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["total_claims"] = payload["total_claims"] + 1
    payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_calibration_output_root(output_root)
    assert "summary_total_claims_mismatch" in errors


def test_distribution_sum_mismatch_fails_validation(tmp_path: Path):
    output_root = _build_bundle(tmp_path)
    payload_path = output_root / "calibration_summary.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["agreement_distribution"]["confirmed"] = payload["agreement_distribution"]["confirmed"] + 1
    payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    errors = validate_calibration_output_root(output_root)
    assert "summary_agreement_distribution_mismatch" in errors


def test_manifest_hash_generation(tmp_path: Path):
    output_root = _build_bundle(tmp_path)
    manifest_payload = json.loads((output_root / "calibration_manifest.json").read_text(encoding="utf-8"))
    generated = {row["path"]: row["sha256"] for row in manifest_payload["generated_files"]}
    for path_str, expected_hash in generated.items():
        path = Path(path_str)
        assert path.exists()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash


def _synthetic_record(
    *,
    claim_value: str,
    confidence: float,
    review_status: str | None,
):
    claim = {
        "schema_version": "visual-signature-calibration-claim-1",
        "taxonomy_version": "phase-zero-taxonomy-1",
        "record_type": "perception_claim",
        "claim_id": "claim_example",
        "claim_kind": "capture_state",
        "claim_value": claim_value,
        "confidence": confidence,
        "confidence_bucket": "high" if confidence >= 0.75 else "medium" if confidence >= 0.45 else "low",
        "evidence_refs": ["/tmp/example.png"],
        "lineage_refs": ["capture:example"],
        "notes": [],
    }
    review = None
    if review_status is not None:
        visually_supported = "yes" if review_status == "approved" else "no" if review_status == "rejected" else "partial"
        review = {
            "schema_version": "visual-signature-calibration-review-outcome-1",
            "taxonomy_version": "phase-zero-taxonomy-1",
            "record_type": "review_outcome",
            "review_id": "review_example",
            "capture_id": "example",
            "reviewer_id": "reviewer",
            "review_status": review_status,
            "visually_supported": visually_supported,
            "unsupported_inference_present": False,
            "uncertainty_accepted": review_status == "needs_more_evidence",
            "notes": [],
        }
    record = CalibrationRecord(
        schema_version="visual-signature-calibration-record-1",
        taxonomy_version="phase-zero-taxonomy-1",
        record_type="calibration_record",
        calibration_id="calibration_example",
        capture_id="example",
        brand_name="Example",
        website_url="https://example.com",
        category="SaaS",
        claim=claim,  # type: ignore[arg-type]
        review_outcome=review,  # type: ignore[arg-type]
        agreement_state="insufficient_review",
        confidence_bucket=claim["confidence_bucket"],
        uncertainty_alignment="insufficient_data",
        evidence_refs=["/tmp/example.png"],
        lineage_refs=["capture:example"],
        source_breakdown={"phase_one_state": 1},
        diagnostics={},
        notes=[],
    )
    if review_status is None:
        record.agreement_state = "insufficient_review"
        record.uncertainty_alignment = "insufficient_data"
    else:
        claim_positive = claim_value in {"RAW_STATE", "ELIGIBLE_FOR_SAFE_INTERVENTION", "MINIMALLY_MUTATED_STATE"}
        review_positive = review_status == "approved"
        if review_status == "needs_more_evidence":
            record.agreement_state = "unresolved"
            record.uncertainty_alignment = "uncertainty_accepted"
        elif claim_positive == review_positive:
            record.agreement_state = "confirmed"
            record.uncertainty_alignment = "underconfident" if confidence < 0.45 else "calibrated"
        else:
            record.agreement_state = "contradicted"
            record.uncertainty_alignment = "overconfident" if confidence >= 0.75 else "underconfident"
    return record


def _build_bundle(tmp_path: Path) -> Path:
    records = build_calibration_records(
        phase_one_root=PHASE_ONE_ROOT,
        phase_two_root=PHASE_TWO_ROOT,
        brand_catalog_path=BRAND_CATALOG,
        capture_manifest_path=CAPTURE_MANIFEST,
        dismissal_audit_path=DISMISSAL_AUDIT,
    )
    metadata_refs = build_source_artifact_refs(
        source_phase_one_root=str(PHASE_ONE_ROOT),
        source_phase_two_root=str(PHASE_TWO_ROOT),
        source_capture_manifest_path=str(CAPTURE_MANIFEST),
        source_dismissal_audit_path=str(DISMISSAL_AUDIT),
        source_brand_catalog_path=str(BRAND_CATALOG),
    )
    summary = build_calibration_summary(
        records,
        calibration_run_id="test-run",
        generated_at=datetime(2026, 5, 11, 22, 17, 48, tzinfo=timezone.utc),
        source_phase_one_root=str(PHASE_ONE_ROOT),
        source_phase_two_root=str(PHASE_TWO_ROOT),
        source_capture_manifest_path=str(CAPTURE_MANIFEST),
        source_dismissal_audit_path=str(DISMISSAL_AUDIT),
        source_brand_catalog_path=str(BRAND_CATALOG),
        source_artifact_refs=metadata_refs,
        source_artifact_hashes=build_source_artifact_hashes(metadata_refs),
        schema_versions=build_schema_versions(),
    )
    output_root = tmp_path / f"calibration-{uuid4().hex}"
    export_calibration_bundle(
        output_root=output_root,
        calibration_run_id="test-run",
        records=records,
        summary=summary,
        source_phase_one_root=str(PHASE_ONE_ROOT),
        source_phase_two_root=str(PHASE_TWO_ROOT),
        source_capture_manifest_path=str(CAPTURE_MANIFEST),
        source_dismissal_audit_path=str(DISMISSAL_AUDIT),
        source_brand_catalog_path=str(BRAND_CATALOG),
    )
    return output_root
