"""Schemas for human review of Visual Signature annotation overlays."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ReviewDecision = Literal["agree", "disagree", "uncertain", "not_applicable"]
UsefulnessScore = Literal[1, 2, 3, 4, 5]
UncertaintyLevel = Literal["none", "low", "medium", "high"]


@dataclass
class TargetReviewDecision:
    target: str
    decision: ReviewDecision
    usefulness: int
    hallucination: bool = False
    uncertainty: UncertaintyLevel = "none"
    corrected_label: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewRecord:
    reviewer_id: str
    annotation_id: str
    brand_name: str
    website_url: str
    expected_category: str
    annotation_path: str
    target_reviews: dict[str, TargetReviewDecision]
    overall_usefulness: int | None = None
    overall_notes: str = ""
    reviewed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["target_reviews"] = {
            key: value.to_dict() for key, value in self.target_reviews.items()
        }
        return payload


@dataclass
class ReviewSampleItem:
    annotation_id: str
    brand_name: str
    website_url: str
    expected_category: str
    annotation_path: str
    sampling_reasons: list[str] = field(default_factory=list)
    annotation_status: str = ""
    annotation_confidence: float | None = None
    disagreement_level: str = ""
    disagreement_flags: list[str] = field(default_factory=list)
    target_labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewBatch:
    version: str
    sample_strategy: str
    items: list[ReviewSampleItem]
    source_dir: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "sample_strategy": self.sample_strategy,
            "source_dir": self.source_dir,
            "notes": self.notes,
            "items": [item.to_dict() for item in self.items],
        }
