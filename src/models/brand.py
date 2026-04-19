"""Data models for Brand3 Scoring."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeatureValue:
    """A single extracted feature with metadata."""
    name: str
    value: float
    raw_value: Optional[str] = None
    confidence: float = 1.0  # 0-1, how confident we are in this data
    source: str = ""  # where this came from


@dataclass
class DimensionScore:
    """Score breakdown for a single dimension."""
    name: str
    score: Optional[float]  # 0-100
    features: dict = field(default_factory=dict)
    insights: list = field(default_factory=list)
    rules_applied: list = field(default_factory=list)  # heuristic rules that fired


@dataclass
class BrandScore:
    """Complete brand score."""
    url: str
    brand_name: str
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    composite_score: Optional[float] = 0.0
    timestamp: str = ""

    @property
    def breakdown(self) -> dict[str, Optional[float]]:
        return {name: d.score for name, d in self.dimensions.items()}
