"""Export helpers for Visual Signature calibration evidence."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from src.visual_signature.calibration.calibration_metrics import calibration_summary_markdown
from src.visual_signature.calibration.calibration_models import (
    CalibrationManifest,
    CalibrationRecord,
    CalibrationRecordsFile,
    CalibrationSummary,
    GeneratedFile,
    validate_calibration_manifest,
    validate_calibration_record,
    validate_calibration_summary,
)


def export_calibration_bundle(
    *,
    output_root: str | Path,
    calibration_run_id: str,
    records: list[CalibrationRecord],
    summary: CalibrationSummary,
    source_phase_one_root: str,
    source_phase_two_root: str,
    source_capture_manifest_path: str | None = None,
    source_dismissal_audit_path: str | None = None,
    source_brand_catalog_path: str | None = None,
) -> dict[str, str]:
    output_path = Path(output_root)
    output_path.mkdir(parents=True, exist_ok=True)
    source_artifact_refs = _source_artifact_refs(
        source_phase_one_root=source_phase_one_root,
        source_phase_two_root=source_phase_two_root,
        source_capture_manifest_path=source_capture_manifest_path,
        source_dismissal_audit_path=source_dismissal_audit_path,
        source_brand_catalog_path=source_brand_catalog_path,
    )
    source_artifact_hashes = _source_artifact_hashes(source_artifact_refs)
    schema_versions = _schema_versions()
    generated_at = summary.generated_at
    records_file = CalibrationRecordsFile(
        schema_version="visual-signature-calibration-records-1",
        taxonomy_version="phase-zero-taxonomy-1",
        record_type="calibration_records",
        calibration_run_id=calibration_run_id,
        generated_at=generated_at,
        source_phase_one_root=source_phase_one_root,
        source_phase_two_root=source_phase_two_root,
        source_capture_manifest_path=source_capture_manifest_path,
        source_dismissal_audit_path=source_dismissal_audit_path,
        source_brand_catalog_path=source_brand_catalog_path,
        source_artifact_refs=source_artifact_refs,
        source_artifact_hashes=source_artifact_hashes,
        record_count=len(records),
        schema_versions=schema_versions,
        records=records,
    )

    summary = summary.model_copy(
        update={
            "calibration_run_id": calibration_run_id,
            "generated_at": generated_at,
            "source_artifact_refs": source_artifact_refs,
            "source_artifact_hashes": source_artifact_hashes,
            "record_count": len(records),
            "summary_count_consistency": len(records) == summary.total_claims,
            "schema_versions": schema_versions,
        }
    )

    _write_json(output_path / "calibration_records.json", records_file.model_dump(mode="json"))
    _write_json(output_path / "calibration_summary.json", summary.model_dump(mode="json"))
    (output_path / "calibration_summary.md").write_text(calibration_summary_markdown(summary) + "\n", encoding="utf-8")
    manifest = CalibrationManifest(
        schema_version="visual-signature-calibration-manifest-1",
        taxonomy_version="phase-zero-taxonomy-1",
        record_type="calibration_manifest",
        calibration_run_id=calibration_run_id,
        generated_at=generated_at,
        source_phase_one_root=source_phase_one_root,
        source_phase_two_root=source_phase_two_root,
        source_capture_manifest_path=source_capture_manifest_path,
        source_dismissal_audit_path=source_dismissal_audit_path,
        source_brand_catalog_path=source_brand_catalog_path,
        source_artifact_refs=source_artifact_refs,
        source_artifact_hashes=source_artifact_hashes,
        record_count=len(records),
        summary_count_consistency=len(records) == summary.total_claims,
        schema_versions=schema_versions,
        generated_files=_generated_files(output_path, ("calibration_records.json", "calibration_summary.json", "calibration_summary.md")),
        validation_status="valid",
        validation_errors=[],
        notes=[
            "Calibration is evidence-only.",
            "Missing review is marked as insufficient_review, not contradicted.",
            "Unclear review is marked as unresolved, not contradicted.",
            "No scoring, rubric dimensions, production reports, or UI are modified.",
        ],
    )
    _write_json(output_path / "calibration_manifest.json", manifest.model_dump(mode="json"))
    return {
        "calibration_records_json": str(output_path / "calibration_records.json"),
        "calibration_summary_json": str(output_path / "calibration_summary.json"),
        "calibration_summary_md": str(output_path / "calibration_summary.md"),
        "calibration_manifest_json": str(output_path / "calibration_manifest.json"),
    }


def validate_calibration_output_root(root: str | Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    records_path = root / "calibration_records.json"
    summary_path = root / "calibration_summary.json"
    summary_md_path = root / "calibration_summary.md"
    manifest_path = root / "calibration_manifest.json"
    if not records_path.exists():
        errors.append("calibration_records_missing")
    if not summary_path.exists():
        errors.append("calibration_summary_missing")
    if not summary_md_path.exists():
        errors.append("calibration_summary_md_missing")
    if not manifest_path.exists():
        errors.append("calibration_manifest_missing")
    if errors:
        return errors

    try:
        records_payload = _load_json(records_path)
        summary_payload = _load_json(summary_path)
        manifest_payload = _load_json(manifest_path)
        records_file = CalibrationRecordsFile.model_validate(records_payload)
        summary = CalibrationSummary.model_validate(summary_payload)
        manifest = CalibrationManifest.model_validate(manifest_payload)
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]

    errors.extend(_validate_counts(records_file, summary))
    errors.extend(_validate_bundle_consistency(records_file, summary, manifest))

    for artifact_ref in manifest.source_artifact_refs:
        artifact_path = Path(artifact_ref)
        if not artifact_path.exists():
            errors.append(f"source_artifact_missing:{artifact_ref}")
        else:
            expected_hash = manifest.source_artifact_hashes.get(artifact_ref)
            if expected_hash and _sha256_file(artifact_path) != expected_hash:
                errors.append(f"source_artifact_hash_mismatch:{artifact_ref}")

    for generated_file in manifest.generated_files:
        file_path = Path(generated_file.path)
        if not file_path.exists():
            errors.append(f"generated_file_missing:{generated_file.path}")
            continue
        if _sha256_file(file_path) != generated_file.sha256:
            errors.append(f"generated_file_hash_mismatch:{generated_file.path}")

    if manifest.validation_status != "valid":
        errors.append(f"manifest_validation_status:{manifest.validation_status}")
    if not manifest.summary_count_consistency:
        errors.append("manifest_summary_count_inconsistent")

    if records_file.record_count != len(records_file.records):
        errors.append("records_count_mismatch")
    if summary.total_claims != len(records_file.records):
        errors.append("summary_total_claims_mismatch")
    if summary.reviewed_claims != sum(1 for record in records_file.records if record.review_outcome is not None):
        errors.append("summary_reviewed_claims_mismatch")
    if summary.confirmed_count != sum(1 for record in records_file.records if record.agreement_state == "confirmed"):
        errors.append("summary_confirmed_count_mismatch")
    if summary.contradicted_count != sum(1 for record in records_file.records if record.agreement_state == "contradicted"):
        errors.append("summary_contradicted_count_mismatch")
    if summary.unresolved_count != sum(1 for record in records_file.records if record.agreement_state == "unresolved"):
        errors.append("summary_unresolved_count_mismatch")
    if summary.insufficient_review_count != sum(
        1 for record in records_file.records if record.agreement_state == "insufficient_review"
    ):
        errors.append("summary_insufficient_review_count_mismatch")
    if sum(summary.agreement_distribution.values()) != summary.total_claims:
        errors.append("summary_agreement_distribution_mismatch")
    if sum(summary.confidence_bucket_distribution.values()) != summary.total_claims:
        errors.append("summary_confidence_bucket_distribution_mismatch")
    if sum(row["total_claims"] for row in summary.category_breakdown.values()) != summary.total_claims:
        errors.append("summary_category_breakdown_mismatch")
    if sum(row["total_claims"] for row in summary.claim_kind_breakdown.values()) != summary.total_claims:
        errors.append("summary_claim_kind_breakdown_mismatch")
    if not summary.summary_count_consistency:
        errors.append("summary_count_consistency_false")
    if summary.record_count != len(records_file.records):
        errors.append("summary_record_count_mismatch")
    if len(summary.source_artifact_refs) != len(records_file.source_artifact_refs):
        errors.append("summary_source_artifact_refs_mismatch")
    if summary.source_artifact_hashes != records_file.source_artifact_hashes:
        errors.append("summary_source_artifact_hashes_mismatch")
    if summary.calibration_run_id != records_file.calibration_run_id or summary.calibration_run_id != manifest.calibration_run_id:
        errors.append("bundle_run_id_mismatch")
    if summary.schema_versions != records_file.schema_versions or summary.schema_versions != manifest.schema_versions:
        errors.append("bundle_schema_versions_mismatch")

    for index, record in enumerate(records_file.records, start=1):
        validation_errors = validate_calibration_record(record.model_dump(mode="json"))
        if validation_errors:
            errors.extend(f"calibration_records.json:record_{index}:{item}" for item in validation_errors)
    validation_errors = validate_calibration_summary(summary.model_dump(mode="json"))
    if validation_errors:
        errors.extend(f"calibration_summary.json:{item}" for item in validation_errors)
    validation_errors = validate_calibration_manifest(manifest.model_dump(mode="json"))
    if validation_errors:
        errors.extend(f"calibration_manifest.json:{item}" for item in validation_errors)

    return list(dict.fromkeys(errors))


def build_source_artifact_refs(
    *,
    source_phase_one_root: str,
    source_phase_two_root: str,
    source_capture_manifest_path: str | None = None,
    source_dismissal_audit_path: str | None = None,
    source_brand_catalog_path: str | None = None,
) -> list[str]:
    return _source_artifact_refs(
        source_phase_one_root=source_phase_one_root,
        source_phase_two_root=source_phase_two_root,
        source_capture_manifest_path=source_capture_manifest_path,
        source_dismissal_audit_path=source_dismissal_audit_path,
        source_brand_catalog_path=source_brand_catalog_path,
    )


def build_source_artifact_hashes(source_artifact_refs: list[str]) -> dict[str, str]:
    return _source_artifact_hashes(source_artifact_refs)


def build_schema_versions() -> dict[str, str]:
    return _schema_versions()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _json_default(value: Any) -> str:
    from datetime import datetime

    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def _schema_versions() -> dict[str, str]:
    return {
        "calibration_claim": "visual-signature-calibration-claim-1",
        "calibration_generated_file": "visual-signature-calibration-generated-file-1",
        "calibration_manifest": "visual-signature-calibration-manifest-1",
        "calibration_record": "visual-signature-calibration-record-1",
        "calibration_records": "visual-signature-calibration-records-1",
        "calibration_summary": "visual-signature-calibration-summary-1",
        "review_outcome": "visual-signature-calibration-review-outcome-1",
    }


def _generated_files(output_path: Path, filenames: tuple[str, ...]) -> list[GeneratedFile]:
    files: list[GeneratedFile] = []
    for filename in filenames:
        path = output_path / filename
        files.append(
            GeneratedFile(
                schema_version="visual-signature-calibration-generated-file-1",
                taxonomy_version="phase-zero-taxonomy-1",
                record_type="generated_file",
                path=str(path),
                sha256=_sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        )
    return files


def _source_artifact_refs(
    *,
    source_phase_one_root: str,
    source_phase_two_root: str,
    source_capture_manifest_path: str | None = None,
    source_dismissal_audit_path: str | None = None,
    source_brand_catalog_path: str | None = None,
) -> list[str]:
    refs = [source_phase_one_root, source_phase_two_root]
    for path in (source_capture_manifest_path, source_dismissal_audit_path, source_brand_catalog_path):
        if path:
            refs.append(path)
    return refs


def _source_artifact_hashes(source_artifact_refs: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for ref in source_artifact_refs:
        path = Path(ref)
        if path.is_file():
            hashes[ref] = _sha256_file(path)
    return hashes


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_counts(records_file: CalibrationRecordsFile, summary: CalibrationSummary) -> list[str]:
    errors: list[str] = []
    if records_file.record_count != len(records_file.records):
        errors.append("records_count_mismatch")
    if summary.record_count != len(records_file.records):
        errors.append("summary_record_count_mismatch")
    if summary.total_claims != records_file.record_count:
        errors.append("summary_total_claims_mismatch")
    return errors


def _validate_bundle_consistency(
    records_file: CalibrationRecordsFile,
    summary: CalibrationSummary,
    manifest: CalibrationManifest,
) -> list[str]:
    errors: list[str] = []
    if summary.summary_count_consistency is not True:
        errors.append("summary_count_consistency_false")
    if manifest.summary_count_consistency is not True:
        errors.append("manifest_summary_count_inconsistent")
    if summary.record_count != records_file.record_count or manifest.record_count != records_file.record_count:
        errors.append("bundle_record_count_mismatch")
    if summary.source_artifact_refs != records_file.source_artifact_refs or manifest.source_artifact_refs != records_file.source_artifact_refs:
        errors.append("bundle_source_artifact_refs_mismatch")
    if summary.source_artifact_hashes != records_file.source_artifact_hashes or manifest.source_artifact_hashes != records_file.source_artifact_hashes:
        errors.append("bundle_source_artifact_hashes_mismatch")
    if summary.schema_versions != records_file.schema_versions or manifest.schema_versions != records_file.schema_versions:
        errors.append("bundle_schema_versions_mismatch")
    return errors
