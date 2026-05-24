"""Evidence-only calibration joins for Visual Signature.

This package compares machine perception claims against reviewed outcomes
without affecting scoring, rubric dimensions, production reports, or UI.
"""

from pathlib import Path

from src.visual_signature.calibration.calibration_export import (
    build_schema_versions,
    build_source_artifact_hashes,
    build_source_artifact_refs,
    export_calibration_bundle,
    validate_calibration_output_root,
)
from src.visual_signature.calibration.calibration_join import (
    build_calibration_records,
    load_brand_category_map,
    load_capture_manifest_index,
    load_dismissal_audit_index,
    load_phase_one_capture_sources,
    load_phase_two_review_index,
)
from src.visual_signature.calibration.calibration_metrics import build_calibration_summary, calibration_summary_markdown
from src.visual_signature.calibration.calibration_reliability_report import (
    build_calibration_reliability_report,
    write_calibration_reliability_report,
)
from src.visual_signature.calibration.calibration_readiness import (
    DEFAULT_READINESS_THRESHOLDS,
    CoverageStats,
    build_calibration_readiness,
    calibration_readiness_markdown,
    ReadinessResult,
    ReadinessScope,
    ReadinessThresholds,
    validate_calibration_readiness_result,
    write_calibration_readiness,
)
from src.visual_signature.calibration.calibration_models import (
    AgreementState,
    CalibrationRecord,
    CalibrationRecordsFile,
    CalibrationManifest,
    CalibrationSummary,
    ConfidenceBucket,
    GeneratedFile,
    PerceptionClaim,
    ReviewOutcome,
    UncertaintyAlignment,
    validate_calibration_manifest,
)

CALIBRATION_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "calibration"

__all__ = [
    "AgreementState",
    "CALIBRATION_ROOT",
    "CalibrationRecord",
    "CalibrationRecordsFile",
    "CalibrationManifest",
    "CalibrationSummary",
    "ConfidenceBucket",
    "CoverageStats",
    "GeneratedFile",
    "DEFAULT_READINESS_THRESHOLDS",
    "PerceptionClaim",
    "ReadinessResult",
    "ReadinessScope",
    "ReadinessThresholds",
    "ReviewOutcome",
    "UncertaintyAlignment",
    "build_calibration_records",
    "build_calibration_summary",
    "build_calibration_reliability_report",
    "build_calibration_readiness",
    "build_schema_versions",
    "build_source_artifact_hashes",
    "build_source_artifact_refs",
    "calibration_summary_markdown",
    "calibration_readiness_markdown",
    "export_calibration_bundle",
    "load_brand_category_map",
    "load_capture_manifest_index",
    "load_dismissal_audit_index",
    "load_phase_one_capture_sources",
    "load_phase_two_review_index",
    "validate_calibration_readiness_result",
    "validate_calibration_manifest",
    "validate_calibration_output_root",
    "write_calibration_readiness",
    "write_calibration_reliability_report",
]
