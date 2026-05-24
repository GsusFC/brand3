"""Validation helpers for Phase Two outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.visual_signature.phase_zero.validation import validate_record_schema


def validate_phase_two_output_root(root: str | Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []

    manifest = _load_json(root / "manifests" / "phase_two_manifest.json")
    if manifest.get("phase") != "phase_two":
        errors.append("manifest_phase_invalid")
    if not isinstance(manifest.get("captures"), list):
        errors.append("manifest_captures_missing")

    review_path = root / "reviews" / "review_records.json"
    review_record_count = 0
    if review_path.exists():
        review_payload = _load_json(review_path)
        rows = review_payload.get("records") if isinstance(review_payload, dict) else review_payload
        if not isinstance(rows, list):
            errors.append("review_records_invalid")
        else:
            for index, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    errors.append(f"review_records.json:row_{index}:not_an_object")
                    continue
                validation_errors = validate_record_schema(row)
                if validation_errors:
                    errors.extend(f"review_records.json:row_{index}:{item}" for item in validation_errors)
                else:
                    review_record_count += 1
    else:
        errors.append("review_records_missing")

    record_files = sorted((root / "records").rglob("*.json")) if (root / "records").exists() else []
    reviewed_eligibility_count = 0
    for path in record_files:
        payload = _load_json(path)
        validation_errors = validate_record_schema(payload)
        if validation_errors:
            errors.extend(f"{path.relative_to(root)}:{item}" for item in validation_errors)
            continue
        if path.name == "reviewed_dataset_eligibility.json":
            reviewed_eligibility_count += 1

    export_path = root / "exports" / "phase_two_reviewed_dataset_eligibility.jsonl"
    if export_path.exists():
        export_count = 0
        for line_no, line in enumerate(export_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"exports/phase_two_reviewed_dataset_eligibility.jsonl:{line_no}:{exc}")
                continue
            validation_errors = validate_record_schema(payload)
            if validation_errors:
                errors.extend(f"exports/phase_two_reviewed_dataset_eligibility.jsonl:{line_no}:{item}" for item in validation_errors)
            export_count += 1
        if manifest.get("total_captures") is not None and export_count != manifest.get("total_captures"):
            errors.append("export_count_mismatch")

    if isinstance(manifest.get("reviewed_captures"), int) and review_record_count != manifest["reviewed_captures"]:
        errors.append("reviewed_count_mismatch")
    if isinstance(manifest.get("total_captures"), int) and reviewed_eligibility_count != manifest["total_captures"]:
        errors.append("reviewed_eligibility_count_mismatch")
    if (
        isinstance(manifest.get("approved_count"), int)
        and isinstance(manifest.get("rejected_count"), int)
        and isinstance(manifest.get("needs_more_evidence_count"), int)
        and isinstance(manifest.get("reviewed_captures"), int)
        and manifest["approved_count"] + manifest["rejected_count"] + manifest["needs_more_evidence_count"] != manifest["reviewed_captures"]
    ):
        errors.append("review_status_count_mismatch")
    if (
        isinstance(manifest.get("eligible_after_review_count"), int)
        and isinstance(manifest.get("blocked_after_review_count"), int)
        and isinstance(manifest.get("total_captures"), int)
        and manifest["eligible_after_review_count"] + manifest["blocked_after_review_count"] != manifest["total_captures"]
    ):
        errors.append("reviewed_outcome_count_mismatch")

    return errors


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
