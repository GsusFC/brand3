"""Types for evidence-only Visual Signature category baselines."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class VisualSignatureMetricRow:
    category: str
    brand_name: str
    website_url: str
    interpretation_status: str
    viewport_whitespace: float | None = None
    viewport_whitespace_band: str = "unknown"
    viewport_density: str = "unknown"
    viewport_density_score: float | None = None
    viewport_composition: str = "unknown"
    composition_stability: float | None = None
    palette_complexity: float | None = None
    dom_viewport_agreement_level: str = "unknown"
    dom_viewport_agreement_score: float | None = None
    dom_viewport_disagreement_severity: str = "none"
    dom_viewport_disagreement_severity_score: float | None = None
    structural_agreement_score: float | None = None
    density_agreement_score: float | None = None
    composition_agreement_score: float | None = None
    palette_agreement_score: float | None = None
    cta_density: float | None = None
    visible_cta_weight: float | None = None
    component_density: float | None = None
    typography_complexity: float | None = None
    extraction_confidence: float | None = None
    vision_confidence: float | None = None
    signal_availability: float | None = None
    signal_usability: float | None = None
    signal_coverage: float | None = None
    source_path: str | None = None
    limitations: list[str] = field(default_factory=list)

    @property
    def interpretable(self) -> bool:
        return self.interpretation_status != "not_interpretable"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NumericBaselineStats:
    average: float | None
    median: float | None
    q1: float | None
    q3: float | None
    iqr: float | None
    count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CategoryBaseline:
    category: str
    sample_count: int
    interpretable_count: int
    not_interpretable_count: int
    category_averages: dict[str, float | None]
    numeric_stats: dict[str, NumericBaselineStats]
    distributions: dict[str, dict[str, int]]
    confidence: dict[str, Any]
    version: str = "visual-signature-category-baseline-mvp-1"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["numeric_stats"] = {
            key: value.to_dict() if isinstance(value, NumericBaselineStats) else value
            for key, value in self.numeric_stats.items()
        }
        return payload


@dataclass
class BrandCategoryComparison:
    category: str
    brand_name: str
    website_url: str
    interpretation_status: str
    outlier_flags: list[str]
    category_relative_notes: list[str]
    confidence: dict[str, Any]
    metrics: dict[str, Any]
    version: str = "visual-signature-category-comparison-mvp-1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
