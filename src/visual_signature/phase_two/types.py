"""Types for Phase Two human review joins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PhaseTwoCaptureBundle:
    capture_id: str
    brand_name: str
    phase_one_eligibility_record: dict[str, Any]
    review_record: dict[str, Any] | None
    reviewed_eligibility_record: dict[str, Any]
    validation_errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PhaseTwoExportManifest:
    schema_version: str
    phase: str
    created_at: str
    source_phase_one_root: str
    source_reviews_path: str
    output_root: str
    total_captures: int
    reviewed_captures: int
    approved_count: int
    rejected_count: int
    needs_more_evidence_count: int
    eligible_after_review_count: int
    blocked_after_review_count: int
    captures: list[dict[str, Any]]
    validation_errors: list[str] = field(default_factory=list)
    validation_passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "created_at": self.created_at,
            "source_phase_one_root": self.source_phase_one_root,
            "source_reviews_path": self.source_reviews_path,
            "output_root": self.output_root,
            "total_captures": self.total_captures,
            "reviewed_captures": self.reviewed_captures,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "needs_more_evidence_count": self.needs_more_evidence_count,
            "eligible_after_review_count": self.eligible_after_review_count,
            "blocked_after_review_count": self.blocked_after_review_count,
            "captures": self.captures,
            "validation_errors": self.validation_errors,
            "validation_passed": self.validation_passed,
        }
