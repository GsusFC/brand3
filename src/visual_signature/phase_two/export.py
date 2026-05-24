"""Export Phase Two reviewed eligibility artifacts."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from src.visual_signature.phase_two.types import PhaseTwoCaptureBundle, PhaseTwoExportManifest


def export_phase_two_bundle(
    *,
    output_root: str | Path,
    bundles: list[PhaseTwoCaptureBundle],
    source_phase_one_root: str,
    source_reviews_path: str,
) -> PhaseTwoExportManifest:
    output_root = Path(output_root)
    reviews_root = output_root / "reviews"
    records_root = output_root / "records"
    manifests_root = output_root / "manifests"
    exports_root = output_root / "exports"
    for root in (reviews_root, records_root, manifests_root, exports_root):
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)

    review_records = [bundle.review_record for bundle in bundles if bundle.review_record is not None]
    _write_json(reviews_root / "review_records.json", {"version": "phase-two-review-records-1", "records": review_records})

    reviewed_rows: list[dict[str, Any]] = []
    capture_summaries: list[dict[str, Any]] = []
    counts = Counter()
    eligible_after_review_count = 0
    blocked_after_review_count = 0
    reviewed_captures = 0

    for bundle in bundles:
        slug = _slug(bundle.capture_id or bundle.brand_name)
        brand_root = records_root / slug
        brand_root.mkdir(parents=True, exist_ok=True)

        phase_one_path = brand_root / "phase_one_dataset_eligibility.json"
        reviewed_path = brand_root / "reviewed_dataset_eligibility.json"
        _write_json(phase_one_path, bundle.phase_one_eligibility_record)
        _write_json(reviewed_path, bundle.reviewed_eligibility_record)
        reviewed_rows.append(bundle.reviewed_eligibility_record)

        if bundle.review_record is not None:
            reviewed_captures += 1
            status = str(bundle.review_record.get("review_status") or "")
            counts[status] += 1
        else:
            counts["missing_review"] += 1

        eligible = bool(bundle.reviewed_eligibility_record.get("eligible"))
        if eligible:
            eligible_after_review_count += 1
        else:
            blocked_after_review_count += 1

        capture_summaries.append(
            {
                "capture_id": bundle.capture_id,
                "brand_name": bundle.brand_name,
                "phase_one_eligible": bool(bundle.phase_one_eligibility_record.get("eligible")),
                "review_status": bundle.review_record.get("review_status") if bundle.review_record else None,
                "reviewed_eligible": eligible,
                "record_paths": [str(phase_one_path), str(reviewed_path)],
            }
        )

    export_path = exports_root / "phase_two_reviewed_dataset_eligibility.jsonl"
    export_path.write_text("\n".join(json.dumps(row, sort_keys=True, default=_json_default) for row in reviewed_rows) + "\n", encoding="utf-8")

    manifest = PhaseTwoExportManifest(
        schema_version="phase-two-manifest-1",
        phase="phase_two",
        created_at=_utc_now(),
        source_phase_one_root=source_phase_one_root,
        source_reviews_path=source_reviews_path,
        output_root=str(output_root),
        total_captures=len(bundles),
        reviewed_captures=reviewed_captures,
        approved_count=counts["approved"],
        rejected_count=counts["rejected"],
        needs_more_evidence_count=counts["needs_more_evidence"],
        eligible_after_review_count=eligible_after_review_count,
        blocked_after_review_count=blocked_after_review_count,
        captures=capture_summaries,
        validation_passed=all(not bundle.validation_errors for bundle in bundles),
        validation_errors=[error for bundle in bundles for error in bundle.validation_errors],
    )
    _write_json(manifests_root / "phase_two_manifest.json", manifest.to_dict())
    return manifest


def _write_json(path: Path, payload: Any) -> None:
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
