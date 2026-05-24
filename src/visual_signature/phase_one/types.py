"""Types for the minimal Phase One pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PhaseOneSourceCapture:
    brand_name: str
    website_url: str
    capture_id: str
    captured_at: str
    viewport_width: int | None
    viewport_height: int | None
    raw_screenshot_path: str | None
    page_url: str | None
    source_manifest_path: str
    source_dismissal_audit_path: str | None = None
    perceptual_state: str | None = None
    perceptual_transitions: list[dict[str, Any]] = field(default_factory=list)
    mutation_audit: dict[str, Any] | None = None
    raw_viewport_metrics: dict[str, Any] | None = None
    before_obstruction: dict[str, Any] | None = None
    after_obstruction: dict[str, Any] | None = None
    dismissal_eligibility: str | None = None
    dismissal_block_reason: str | None = None
    dismissal_attempted: bool = False
    dismissal_successful: bool = False
    clean_attempt_screenshot_path: str | None = None
    capture_variant: str | None = None
    clean_attempt_capture_variant: str | None = None
    capture_type: str | None = None


@dataclass(slots=True)
class PhaseOneCaptureBundle:
    source: PhaseOneSourceCapture
    observation_records: list[dict[str, Any]]
    state_record: dict[str, Any]
    transition_records: list[dict[str, Any]]
    mutation_audit_record: dict[str, Any] | None
    dataset_eligibility_record: dict[str, Any]
    validation_errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PhaseOneExportManifest:
    schema_version: str
    phase: str
    created_at: str
    source_capture_manifest_path: str
    source_dismissal_audit_path: str | None
    output_root: str
    brands: list[dict[str, Any]]
    record_counts: dict[str, int]
    eligible_count: int
    blocked_count: int
    validation_errors: list[str] = field(default_factory=list)
    validation_passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "created_at": self.created_at,
            "source_capture_manifest_path": self.source_capture_manifest_path,
            "source_dismissal_audit_path": self.source_dismissal_audit_path,
            "output_root": self.output_root,
            "brands": self.brands,
            "record_counts": self.record_counts,
            "eligible_count": self.eligible_count,
            "blocked_count": self.blocked_count,
            "validation_errors": self.validation_errors,
            "validation_passed": self.validation_passed,
        }
