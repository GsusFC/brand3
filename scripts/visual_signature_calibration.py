#!/usr/bin/env python3
"""Build evidence-only calibration records for Visual Signature.

This joins Phase One / Phase Two outputs, review records, and obstruction /
affordance diagnostics into calibration artifacts for manual inspection.
It does not change scoring, rubric dimensions, reports, or UI.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.calibration import (  # noqa: E402
    CALIBRATION_ROOT,
    build_schema_versions,
    build_source_artifact_hashes,
    build_source_artifact_refs,
    build_calibration_records,
    build_calibration_summary,
    export_calibration_bundle,
)


DEFAULT_PHASE_ONE_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "phase_one"
DEFAULT_PHASE_TWO_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "phase_two"
DEFAULT_CAPTURE_MANIFEST = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "capture_manifest.json"
DEFAULT_DISMISSAL_AUDIT = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "dismissal_audit.json"
DEFAULT_BRAND_CATALOG = PROJECT_ROOT / "examples" / "visual_signature" / "calibration_brands.json"
DEFAULT_OUTPUT_ROOT = CALIBRATION_ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Visual Signature calibration evidence.")
    parser.add_argument("--phase-one-root", type=Path, default=DEFAULT_PHASE_ONE_ROOT)
    parser.add_argument("--phase-two-root", type=Path, default=DEFAULT_PHASE_TWO_ROOT)
    parser.add_argument("--capture-manifest", type=Path, default=DEFAULT_CAPTURE_MANIFEST)
    parser.add_argument("--dismissal-audit", type=Path, default=DEFAULT_DISMISSAL_AUDIT)
    parser.add_argument("--brand-catalog", type=Path, default=DEFAULT_BRAND_CATALOG)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)

    calibration_run_id = uuid4().hex
    generated_at = datetime.now(timezone.utc)
    source_artifact_refs = build_source_artifact_refs(
        source_phase_one_root=str(args.phase_one_root),
        source_phase_two_root=str(args.phase_two_root),
        source_capture_manifest_path=str(args.capture_manifest),
        source_dismissal_audit_path=str(args.dismissal_audit),
        source_brand_catalog_path=str(args.brand_catalog),
    )
    source_artifact_hashes = build_source_artifact_hashes(source_artifact_refs)
    schema_versions = build_schema_versions()

    records = build_calibration_records(
        phase_one_root=args.phase_one_root,
        phase_two_root=args.phase_two_root,
        brand_catalog_path=args.brand_catalog,
        capture_manifest_path=args.capture_manifest,
        dismissal_audit_path=args.dismissal_audit,
    )
    summary = build_calibration_summary(
        records,
        calibration_run_id=calibration_run_id,
        generated_at=generated_at,
        source_phase_one_root=str(args.phase_one_root),
        source_phase_two_root=str(args.phase_two_root),
        source_capture_manifest_path=str(args.capture_manifest),
        source_dismissal_audit_path=str(args.dismissal_audit),
        source_brand_catalog_path=str(args.brand_catalog),
        source_artifact_refs=source_artifact_refs,
        source_artifact_hashes=source_artifact_hashes,
        schema_versions=schema_versions,
    )
    outputs = export_calibration_bundle(
        output_root=args.output_root,
        calibration_run_id=calibration_run_id,
        records=records,
        summary=summary,
        source_phase_one_root=str(args.phase_one_root),
        source_phase_two_root=str(args.phase_two_root),
        source_capture_manifest_path=str(args.capture_manifest),
        source_dismissal_audit_path=str(args.dismissal_audit),
        source_brand_catalog_path=str(args.brand_catalog),
    )

    print(
        json.dumps(
            {
                "record_count": len(records),
                "summary_path": outputs["calibration_summary_json"],
                "records_path": outputs["calibration_records_json"],
                "manifest_path": outputs["calibration_manifest_json"],
                "output_root": str(args.output_root),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
