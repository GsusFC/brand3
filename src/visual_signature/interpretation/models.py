"""Contracts for the Lab-only multimodal visual interpretation pass."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


VISUAL_EVIDENCE_PACK_SCHEMA_VERSION = "visual-evidence-pack-v1"
VISUAL_INTERPRETATION_SCHEMA_VERSION = "visual-interpretation-v1"

PackStatus = Literal["ready", "limited", "not_evaluable"]
CaptureQuality = Literal["clean", "usable", "partial", "blocked", "missing", "unknown"]
InterpretationStatus = Literal["usable", "limited", "not_evaluable"]
ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass
class VisualEvidencePack:
    brand_name: str
    website_url: str
    category_hint: str = ""
    status: PackStatus = "not_evaluable"
    capture_quality: CaptureQuality = "unknown"
    screenshot_path: str | None = None
    screenshot_mime_type: str | None = None
    screenshot_available: bool = False
    page_state: dict[str, Any] = field(default_factory=dict)
    clean_capture_decision: dict[str, Any] = field(default_factory=dict)
    visual_signature_summary: dict[str, Any] = field(default_factory=dict)
    computed_style_summary: dict[str, Any] = field(default_factory=dict)
    human_review: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    schema_version: Literal["visual-evidence-pack-v1"] = VISUAL_EVIDENCE_PACK_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceUse:
    ref: str
    observation: str


@dataclass
class VisualInterpretation:
    brand_name: str
    website_url: str
    status: InterpretationStatus
    reference_profile: str = "unknown"
    identity_read: str = "not_evaluable"
    confidence: ConfidenceLevel = "low"
    visual_positioning: str = ""
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    antipatterns: list[str] = field(default_factory=list)
    evidence_used: list[EvidenceUse] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    model: str = ""
    adjudicator_model: str | None = None
    schema_version: Literal["visual-interpretation-v1"] = VISUAL_INTERPRETATION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, model: str = "", adjudicator_model: str | None = None) -> "VisualInterpretation":
        evidence_items = []
        for item in payload.get("evidence_used") or []:
            if isinstance(item, dict):
                evidence_items.append(
                    EvidenceUse(
                        ref=str(item.get("ref") or "").strip(),
                        observation=str(item.get("observation") or "").strip(),
                    )
                )
        return cls(
            brand_name=str(payload.get("brand_name") or "").strip(),
            website_url=str(payload.get("website_url") or "").strip(),
            status=_status(payload.get("status")),
            reference_profile=str(payload.get("reference_profile") or "unknown").strip() or "unknown",
            identity_read=str(payload.get("identity_read") or "not_evaluable").strip() or "not_evaluable",
            confidence=_confidence(payload.get("confidence")),
            visual_positioning=str(payload.get("visual_positioning") or "").strip(),
            strengths=_string_list(payload.get("strengths")),
            risks=_string_list(payload.get("risks")),
            antipatterns=_string_list(payload.get("antipatterns")),
            evidence_used=evidence_items,
            recommendations=_string_list(payload.get("recommendations")),
            limitations=_string_list(payload.get("limitations")),
            model=str(payload.get("model") or model or "").strip(),
            adjudicator_model=payload.get("adjudicator_model") or adjudicator_model,
        )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def _status(value: Any) -> InterpretationStatus:
    text = str(value or "").strip()
    if text in {"usable", "limited", "not_evaluable"}:
        return text  # type: ignore[return-value]
    return "not_evaluable"


def _confidence(value: Any) -> ConfidenceLevel:
    text = str(value or "").strip()
    if text in {"high", "medium", "low"}:
        return text  # type: ignore[return-value]
    return "low"
