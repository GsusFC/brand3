"""Export helpers for Phase One outputs."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from src.visual_signature.phase_one.types import PhaseOneCaptureBundle, PhaseOneExportManifest


def export_phase_one_bundle(
    *,
    output_root: str | Path,
    bundles: list[PhaseOneCaptureBundle],
    source_capture_manifest_path: str,
    source_dismissal_audit_path: str | None = None,
) -> PhaseOneExportManifest:
    output_root = Path(output_root)
    records_root = output_root / "records"
    manifests_root = output_root / "manifests"
    exports_root = output_root / "exports"
    for root in (records_root, manifests_root, exports_root):
        if root.exists():
            shutil.rmtree(root)
    for root in (records_root, manifests_root, exports_root):
        root.mkdir(parents=True, exist_ok=True)

    record_counts: Counter[str] = Counter()
    brands: list[dict[str, Any]] = []
    jsonl_rows: list[dict[str, Any]] = []
    eligible_count = 0
    blocked_count = 0

    for bundle in bundles:
        slug = _slug(bundle.source.brand_name)
        brand_root = records_root / slug
        brand_root.mkdir(parents=True, exist_ok=True)
        created_paths: list[str] = []

        for record in bundle.observation_records:
            path = brand_root / f"{record['observation_key']}.json"
            _write_json(path, record)
            created_paths.append(str(path))
            record_counts["perceptual_observation"] += 1
            jsonl_rows.append(record)

        state_path = brand_root / "state.json"
        _write_json(state_path, bundle.state_record)
        created_paths.append(str(state_path))
        record_counts["perceptual_state"] += 1
        jsonl_rows.append(bundle.state_record)

        for index, transition in enumerate(bundle.transition_records, start=1):
            path = brand_root / f"transition_{index}_{transition['reason']}.json"
            _write_json(path, transition)
            created_paths.append(str(path))
            record_counts["transition_record"] += 1
            jsonl_rows.append(transition)

        if bundle.mutation_audit_record:
            path = brand_root / "mutation_audit.json"
            _write_json(path, bundle.mutation_audit_record)
            created_paths.append(str(path))
            record_counts["mutation_audit"] += 1
            jsonl_rows.append(bundle.mutation_audit_record)

        eligibility_path = brand_root / "dataset_eligibility.json"
        _write_json(eligibility_path, bundle.dataset_eligibility_record)
        created_paths.append(str(eligibility_path))
        record_counts["dataset_eligibility"] += 1
        jsonl_rows.append(bundle.dataset_eligibility_record)

        eligible = bool(bundle.dataset_eligibility_record.get("eligible"))
        if eligible:
            eligible_count += 1
        else:
            blocked_count += 1

        brands.append(
            {
                "brand_name": bundle.source.brand_name,
                "capture_id": bundle.source.capture_id,
                "eligible": eligible,
                "record_paths": created_paths,
                "validation_errors": bundle.validation_errors,
            }
        )

    export_path = exports_root / "phase_one_records.jsonl"
    export_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in jsonl_rows) + "\n", encoding="utf-8")

    manifest = PhaseOneExportManifest(
        schema_version="phase-one-manifest-1",
        phase="phase_one",
        created_at=_utc_now(),
        source_capture_manifest_path=source_capture_manifest_path,
        source_dismissal_audit_path=source_dismissal_audit_path,
        output_root=str(output_root),
        brands=brands,
        record_counts=dict(record_counts),
        eligible_count=eligible_count,
        blocked_count=blocked_count,
        validation_passed=all(not bundle.validation_errors for bundle in bundles),
        validation_errors=[error for bundle in bundles for error in bundle.validation_errors],
    )
    _write_json(manifests_root / "phase_one_manifest.json", manifest.to_dict())
    return manifest


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    value = value.lower().strip()
    out = []
    for char in value:
        if char.isalnum():
            out.append(char)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-") or "capture"


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_default(value: Any) -> str:
    from datetime import datetime

    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)
