"""SV9 result models.

One record per component (not a monolithic blob) so individual components can
be retried and re-evaluated from the persisted snapshot. See design doc
section 10.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.sv9.rubric import (
    COMPONENTS,
    RUBRIC_VERSION,
    STATUS_NOT_DETECTED,
    STATUS_NOT_EVALUATED,
    STATUS_SCORED,
    component_points,
)


@dataclass
class RungVerdict:
    """One boolean verdict per ladder rung, with mandatory evidence."""

    rung: int
    passed: bool
    evidence: str = ""
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rung": self.rung,
            "passed": self.passed,
            "evidence": self.evidence,
            "reasoning": self.reasoning,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RungVerdict":
        return cls(
            rung=int(payload.get("rung", 0)),
            passed=bool(payload.get("passed", False)),
            evidence=str(payload.get("evidence") or ""),
            reasoning=str(payload.get("reasoning") or ""),
        )


@dataclass
class ComponentResult:
    """Evaluation outcome for one SV9 component."""

    component: str
    status: str  # STATUS_SCORED | STATUS_NOT_DETECTED | STATUS_NOT_EVALUATED
    score: int = 0
    rung_profile: list[RungVerdict] = field(default_factory=list)
    detected_content: str | None = None
    detection_mode: str | None = None
    detection_confidence: str | None = None
    evidence: list[str] = field(default_factory=list)
    error: str | None = None  # populated for STATUS_NOT_EVALUATED

    @property
    def scale(self) -> int:
        return COMPONENTS[self.component]["scale"]

    @property
    def points(self) -> int:
        """Points contributed to the Brand3 Score (multiplier applied)."""
        if self.status != STATUS_SCORED:
            return 0
        return component_points(self.component, self.score)

    @property
    def non_monotonic_rungs(self) -> list[int]:
        """Rungs passed above the first failure: rubric or evaluator smell."""
        first_fail = None
        anomalies = []
        for verdict in sorted(self.rung_profile, key=lambda v: v.rung):
            if first_fail is None and not verdict.passed:
                first_fail = verdict.rung
            elif first_fail is not None and verdict.passed:
                anomalies.append(verdict.rung)
        return anomalies

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status,
            "score": self.score,
            "scale": self.scale,
            "points": self.points,
            "rung_profile": [v.to_dict() for v in self.rung_profile],
            "non_monotonic_rungs": self.non_monotonic_rungs,
            "detected_content": self.detected_content,
            "detection_mode": self.detection_mode,
            "detection_confidence": self.detection_confidence,
            "evidence": list(self.evidence),
            "error": self.error,
        }


@dataclass
class Sv9ScanResult:
    """Aggregated SV9 scan: 9 components + Coherencia + Brand3 Score."""

    brand_name: str
    url: str
    source_run_id: int | None
    components: dict[str, ComponentResult]
    brand3_score: int = 0
    base_average: float | None = None
    magnetism_capped: bool = False
    immediate_margin: int = 0
    most_painful_gap: str | None = None
    needs_review: bool = False
    rubric_version: str = RUBRIC_VERSION
    evaluator_model: str | None = None

    @property
    def is_complete(self) -> bool:
        """Complete scans have no technical failures; only these enter the ranking."""
        return all(c.status != STATUS_NOT_EVALUATED for c in self.components.values())

    @property
    def not_detected(self) -> list[str]:
        return [k for k, c in self.components.items() if c.status == STATUS_NOT_DETECTED]

    @property
    def not_evaluated(self) -> list[str]:
        return [k for k, c in self.components.items() if c.status == STATUS_NOT_EVALUATED]

    def to_dict(self) -> dict[str, Any]:
        return {
            "brand_name": self.brand_name,
            "url": self.url,
            "source_run_id": self.source_run_id,
            "rubric_version": self.rubric_version,
            "evaluator_model": self.evaluator_model,
            "brand3_score": self.brand3_score,
            "base_average": self.base_average,
            "magnetism_capped": self.magnetism_capped,
            "immediate_margin": self.immediate_margin,
            "most_painful_gap": self.most_painful_gap,
            "needs_review": self.needs_review,
            "is_complete": self.is_complete,
            "not_detected": self.not_detected,
            "not_evaluated": self.not_evaluated,
            "components": {k: c.to_dict() for k, c in self.components.items()},
        }


__all__ = [
    "ComponentResult",
    "RungVerdict",
    "Sv9ScanResult",
    "STATUS_SCORED",
    "STATUS_NOT_DETECTED",
    "STATUS_NOT_EVALUATED",
]
