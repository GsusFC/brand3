"""Artifact catalog and artifact-backed filesystem helpers for Visual Signature web views."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VISUAL_SIGNATURE_ROOT = PROJECT_ROOT / "examples" / "visual_signature"

ARTIFACTS: dict[str, dict[str, str]] = {
    "capture_manifest": {
        "label": "Capture manifest",
        "path": "screenshots/capture_manifest.json",
        "type": "json",
        "section": "overview",
    },
    "dismissal_audit": {
        "label": "Dismissal audit",
        "path": "screenshots/dismissal_audit.json",
        "type": "json",
        "section": "overview",
    },
    "governance_integrity_report": {
        "label": "Governance integrity report",
        "path": "governance/governance_integrity_report.json",
        "type": "json",
        "section": "governance",
    },
    "capability_registry": {
        "label": "Capability registry",
        "path": "governance/capability_registry.json",
        "type": "json",
        "section": "governance",
    },
    "runtime_policy_matrix": {
        "label": "Runtime policy matrix",
        "path": "governance/runtime_policy_matrix.json",
        "type": "json",
        "section": "governance",
    },
    "three_track_validation_plan": {
        "label": "Three-track validation plan",
        "path": "governance/three_track_validation_plan.json",
        "type": "json",
        "section": "governance",
    },
    "calibration_readiness": {
        "label": "Calibration readiness",
        "path": "calibration/calibration_readiness.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_manifest": {
        "label": "Calibration manifest",
        "path": "calibration/calibration_manifest.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_summary": {
        "label": "Calibration summary",
        "path": "calibration/calibration_summary.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_records": {
        "label": "Calibration records",
        "path": "calibration/calibration_records.json",
        "type": "json",
        "section": "calibration",
    },
    "calibration_reliability_report": {
        "label": "Calibration reliability report",
        "path": "calibration/calibration_reliability_report.md",
        "type": "markdown",
        "section": "calibration",
    },
    "corpus_expansion_manifest": {
        "label": "Corpus expansion manifest",
        "path": "corpus_expansion/corpus_expansion_manifest.json",
        "type": "json",
        "section": "corpus",
    },
    "pilot_metrics": {
        "label": "Pilot metrics",
        "path": "corpus_expansion/pilot_metrics.json",
        "type": "json",
        "section": "corpus",
    },
    "review_queue": {
        "label": "Review queue",
        "path": "corpus_expansion/review_queue.json",
        "type": "json",
        "section": "reviewer",
    },
    "reviewer_workflow_pilot": {
        "label": "Reviewer workflow pilot",
        "path": "corpus_expansion/reviewer_workflow_pilot.json",
        "type": "json",
        "section": "reviewer",
    },
    "reviewer_packet_index": {
        "label": "Reviewer packet index",
        "path": "corpus_expansion/reviewer_packets/reviewer_packet_index.md",
        "type": "markdown",
        "section": "reviewer",
    },
    "reviewer_viewer": {
        "label": "Reviewer viewer",
        "path": "corpus_expansion/reviewer_viewer/index.html",
        "type": "html",
        "section": "reviewer",
    },
}

HUMAN_REVIEW_DESIGN_PATH = DEFAULT_VISUAL_SIGNATURE_ROOT / "human_review_ui_design.json"
REVIEW_SEMANTICS_PATH = DEFAULT_VISUAL_SIGNATURE_ROOT / "review_semantics.json"


def visual_signature_root() -> Path:
    return Path(os.environ.get("BRAND3_VISUAL_SIGNATURE_ROOT", str(DEFAULT_VISUAL_SIGNATURE_ROOT)))


def artifact_path(key: str, *, root: Path | None = None) -> Path | None:
    spec = ARTIFACTS.get(key)
    if not spec:
        return None
    root = root or visual_signature_root()
    return root / spec["path"]


def artifact_file_response_payload(key: str) -> tuple[Path, str] | None:
    spec = ARTIFACTS.get(key)
    path = artifact_path(key)
    if not spec or path is None or not path.exists() or not _is_under_root(path):
        return None
    media_type = {
        "json": "application/json",
        "markdown": "text/markdown; charset=utf-8",
        "html": "text/html; charset=utf-8",
    }.get(spec["type"], "text/plain; charset=utf-8")
    return path, media_type


def screenshot_file_response_payload(filename: str) -> tuple[Path, str] | None:
    path = visual_signature_root() / "screenshots" / filename
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return None
    if not path.exists() or not _is_under_root(path):
        return None
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }[path.suffix.lower()]
    return path, media_type


def _is_under_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(visual_signature_root().resolve())
    except ValueError:
        return False
    return True
