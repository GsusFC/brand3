"""Constants for Visual Signature platform generation."""

from pathlib import Path

VISUAL_SIGNATURE_PLATFORM_RECORD_TYPE = "brand3_platform_bundle"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VISUAL_SIGNATURE_ROOT = PROJECT_ROOT / "examples" / "visual_signature"
DEFAULT_SCORING_OUTPUT_ROOT = PROJECT_ROOT / "output"
DEFAULT_OUTPUT_ROOT = DEFAULT_VISUAL_SIGNATURE_ROOT / "platform"

GUARDRAILS = [
    "read-only local navigation surface",
    "Initial Scoring and Visual Signature remain separate layers",
    "no Visual Signature to scoring integration",
    "no scoring logic changes",
    "no rubric dimension changes",
    "no production UI or report impact",
    "no runtime behavior changes",
    "no provider execution",
    "no model training",
    "no runtime mutation enablement",
    "no capture behavior changes",
    "JSON remains source of truth",
    "Markdown remains audit/export",
]

VISUAL_SIGNATURE_ARTIFACT_SPECS = [
    ("capture_manifest", "Capture manifest", "screenshots/capture_manifest.json", "json", True),
    ("dismissal_audit", "Dismissal audit", "screenshots/dismissal_audit.json", "json", True),
    ("screenshots_readme", "Screenshots README", "screenshots/README.md", "markdown", False),
    ("review_queue", "Review queue", "corpus_expansion/review_queue.json", "json", True),
    ("reviewer_workflow_pilot", "Reviewer workflow pilot", "corpus_expansion/reviewer_workflow_pilot.json", "json", True),
    ("reviewer_packet_index", "Reviewer packet index", "corpus_expansion/reviewer_packets/reviewer_packet_index.md", "markdown", False),
    ("reviewer_viewer", "Reviewer viewer", "corpus_expansion/reviewer_viewer/index.html", "html", True),
    ("calibration_manifest", "Calibration manifest", "calibration/calibration_manifest.json", "json", True),
    ("calibration_records", "Calibration records", "calibration/calibration_records.json", "json", True),
    ("calibration_summary", "Calibration summary", "calibration/calibration_summary.json", "json", True),
    ("calibration_reliability_report", "Calibration reliability report", "calibration/calibration_reliability_report.md", "markdown", False),
    ("calibration_readiness", "Calibration readiness", "calibration/calibration_readiness.json", "json", True),
    ("calibration_governance_checkpoint", "Calibration governance checkpoint", "calibration/calibration_governance_checkpoint.md", "markdown", False),
    ("capability_registry", "Capability registry", "governance/capability_registry.json", "json", True),
    ("runtime_policy_matrix", "Runtime policy matrix", "governance/runtime_policy_matrix.json", "json", True),
    ("governance_integrity_report", "Governance integrity report", "governance/governance_integrity_report.json", "json", True),
    ("three_track_validation_plan", "Three-track validation plan", "governance/three_track_validation_plan.json", "json", True),
    ("technical_checkpoint", "Technical checkpoint", "technical_checkpoint.md", "markdown", False),
    ("reliable_visual_perception", "Reliable visual perception", "reliable_visual_perception.md", "markdown", False),
    ("corpus_expansion_manifest", "Corpus expansion manifest", "corpus_expansion/corpus_expansion_manifest.json", "json", True),
    ("pilot_metrics", "Pilot metrics", "corpus_expansion/pilot_metrics.json", "json", True),
    ("corpus_expansion_markdown", "Corpus expansion markdown", "corpus_expansion/corpus_expansion_manifest.md", "markdown", False),
]

SCORING_ARTIFACT_SPECS = [
    ("scoring_output_root", "Scoring output root", "output", "directory", False),
    ("scoring_reports_root", "Scoring reports root", "output/reports", "directory", False),
    ("brand3_sqlite", "Brand3 SQLite store", "data/brand3.sqlite3", "sqlite", False),
    ("brand3_legacy_db", "Brand3 legacy DB", "data/brand3.db", "sqlite", False),
    ("scoring_dimensions_source", "Scoring rubric dimensions source", "src/dimensions.py", "python", False),
]
