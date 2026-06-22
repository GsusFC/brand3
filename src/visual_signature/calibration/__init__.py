"""Evidence-only calibration joins for Visual Signature.

This package compares machine perception claims against reviewed outcomes
without affecting scoring, rubric dimensions, production reports, or UI.
"""

from pathlib import Path

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

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

_EXPORTS = {
    "AgreementState": ("src.visual_signature.calibration.calibration_models", "AgreementState"),
    "CalibrationRecord": ("src.visual_signature.calibration.calibration_models", "CalibrationRecord"),
    "CalibrationRecordsFile": ("src.visual_signature.calibration.calibration_models", "CalibrationRecordsFile"),
    "CalibrationManifest": ("src.visual_signature.calibration.calibration_models", "CalibrationManifest"),
    "CalibrationSummary": ("src.visual_signature.calibration.calibration_models", "CalibrationSummary"),
    "ConfidenceBucket": ("src.visual_signature.calibration.calibration_models", "ConfidenceBucket"),
    "CoverageStats": ("src.visual_signature.calibration.calibration_readiness", "CoverageStats"),
    "GeneratedFile": ("src.visual_signature.calibration.calibration_models", "GeneratedFile"),
    "DEFAULT_READINESS_THRESHOLDS": ("src.visual_signature.calibration.calibration_readiness", "DEFAULT_READINESS_THRESHOLDS"),
    "PerceptionClaim": ("src.visual_signature.calibration.calibration_models", "PerceptionClaim"),
    "ReadinessResult": ("src.visual_signature.calibration.calibration_readiness", "ReadinessResult"),
    "ReadinessScope": ("src.visual_signature.calibration.calibration_readiness", "ReadinessScope"),
    "ReadinessThresholds": ("src.visual_signature.calibration.calibration_readiness", "ReadinessThresholds"),
    "ReviewOutcome": ("src.visual_signature.calibration.calibration_models", "ReviewOutcome"),
    "UncertaintyAlignment": ("src.visual_signature.calibration.calibration_models", "UncertaintyAlignment"),
    "build_calibration_records": ("src.visual_signature.calibration.calibration_join", "build_calibration_records"),
    "build_calibration_summary": ("src.visual_signature.calibration.calibration_metrics", "build_calibration_summary"),
    "build_calibration_reliability_report": (
        "src.visual_signature.calibration.calibration_reliability_report",
        "build_calibration_reliability_report",
    ),
    "build_calibration_readiness": ("src.visual_signature.calibration.calibration_readiness", "build_calibration_readiness"),
    "build_schema_versions": ("src.visual_signature.calibration.calibration_export", "build_schema_versions"),
    "build_source_artifact_hashes": ("src.visual_signature.calibration.calibration_export", "build_source_artifact_hashes"),
    "build_source_artifact_refs": ("src.visual_signature.calibration.calibration_export", "build_source_artifact_refs"),
    "calibration_summary_markdown": ("src.visual_signature.calibration.calibration_metrics", "calibration_summary_markdown"),
    "calibration_readiness_markdown": (
        "src.visual_signature.calibration.calibration_readiness",
        "calibration_readiness_markdown",
    ),
    "export_calibration_bundle": ("src.visual_signature.calibration.calibration_export", "export_calibration_bundle"),
    "load_brand_category_map": ("src.visual_signature.calibration.calibration_join", "load_brand_category_map"),
    "load_capture_manifest_index": ("src.visual_signature.calibration.calibration_join", "load_capture_manifest_index"),
    "load_dismissal_audit_index": ("src.visual_signature.calibration.calibration_join", "load_dismissal_audit_index"),
    "load_phase_one_capture_sources": (
        "src.visual_signature.calibration.calibration_join",
        "load_phase_one_capture_sources",
    ),
    "load_phase_two_review_index": ("src.visual_signature.calibration.calibration_join", "load_phase_two_review_index"),
    "validate_calibration_readiness_result": (
        "src.visual_signature.calibration.calibration_readiness",
        "validate_calibration_readiness_result",
    ),
    "validate_calibration_manifest": ("src.visual_signature.calibration.calibration_models", "validate_calibration_manifest"),
    "validate_calibration_output_root": ("src.visual_signature.calibration.calibration_export", "validate_calibration_output_root"),
    "write_calibration_readiness": ("src.visual_signature.calibration.calibration_readiness", "write_calibration_readiness"),
    "write_calibration_reliability_report": (
        "src.visual_signature.calibration.calibration_reliability_report",
        "write_calibration_reliability_report",
    ),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
