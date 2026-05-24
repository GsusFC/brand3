"""Validation helpers for Phase One outputs."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.visual_signature.phase_zero.validation import validate_record_schema


def validate_phase_one_output_root(root: str | Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []

    manifest = _load_json(root / "manifests" / "phase_one_manifest.json")
    if manifest.get("phase") != "phase_one":
        errors.append("manifest_phase_invalid")
    if manifest.get("validation_passed") is False:
        errors.append("manifest_validation_failed")
    if not isinstance(manifest.get("record_counts"), dict):
        errors.append("manifest_record_counts_missing")

    record_files = sorted((root / "records").rglob("*.json")) if (root / "records").exists() else []
    counts: Counter[str] = Counter()
    for path in record_files:
        if path.name == "phase_one_manifest.json":
            continue
        payload = _load_json(path)
        validation_errors = validate_record_schema(payload)
        if validation_errors:
            errors.extend(f"{path.relative_to(root)}:{item}" for item in validation_errors)
            continue
        record_type = str(payload.get("record_type") or "")
        if record_type:
            counts[record_type] += 1

    jsonl_path = root / "exports" / "phase_one_records.jsonl"
    if jsonl_path.exists():
        for line_no, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"exports/phase_one_records.jsonl:{line_no}:{exc}")
                continue
            validation_errors = validate_record_schema(payload)
            if validation_errors:
                errors.extend(f"exports/phase_one_records.jsonl:{line_no}:{item}" for item in validation_errors)

    manifest_counts = manifest.get("record_counts")
    if isinstance(manifest_counts, dict):
        for key, value in counts.items():
            if manifest_counts.get(key) != value:
                errors.append(f"manifest_count_mismatch:{key}:{manifest_counts.get(key)}!={value}")

    return errors


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
