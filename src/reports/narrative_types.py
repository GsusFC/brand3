"""Shared narrative data types."""

from __future__ import annotations

from dataclasses import dataclass, field

from .derivation import DimensionEvidences, Evidence


@dataclass
class Finding:
    """One §3 sub-block. Four-part editorial structure plus URLs."""

    title: str
    observation: str = ""
    implication: str = ""
    typical_decision: str = ""
    evidence_urls: list[str] = field(default_factory=list)

    @property
    def prose(self) -> str:
        parts = [p for p in (self.observation, self.implication) if p]
        return " ".join(parts)


@dataclass
class SynthesisContext:
    """Input bundle for §1 generation."""

    brand: str
    url: str
    composite_score: float | None
    dimensions: list[DimensionEvidences]
    data_quality: str
    top_evidences: list[Evidence]
    analysis_date: str | None = None
    tension_text: str | None = None
