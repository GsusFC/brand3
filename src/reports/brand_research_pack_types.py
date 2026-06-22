"""Dataclasses and serialization helpers for Brand Research Pack."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.reports.brand_research_pack_sources import ALLOWED_ENTITY_TYPES, EntityResolution, ResearchSource, _validate_entity_type

ALLOWED_EVIDENCE_KINDS = {"evidence", "proof", "context", "noise"}

FIELD_DESCRIPTIONS: dict[str, str] = {
    "input_url": "Original URL supplied for analysis.",
    "resolved_entity": "Canonical entity resolution object for the analysis target.",
    "entity_type": "Coarse entity class such as company, product, or content.",
    "parent_brand": "Parent brand when the target is a product, lab, or sub-brand.",
    "official_urls": "Official or owned URLs associated with the entity.",
    "analyzed_urls": "URLs actually inspected while building the pack.",
    "source_map": "Stable source metadata keyed by source identifier or URL.",
    "company_summary": "Short company-level synthesis.",
    "product_summary": "Short product-level synthesis.",
    "audience": "Audience inferred from the evidence.",
    "offer": "What the brand or product is offering.",
    "outcome": "What changes for the audience.",
    "category": "Category or market framing.",
    "declared_purpose": "Explicit purpose language declared by the brand.",
    "declared_mission": "Explicit mission language declared by the brand.",
    "future_direction": "Future or category-change direction language.",
    "tone_of_voice": "Observed tone of voice.",
    "personality_signals": "Concise personality signals extracted from evidence.",
    "visual_or_conceptual_signals": "Visual or conceptual metaphors and signals.",
    "values_signals": "Value or belief signals repeated in the evidence.",
    "attributes_signals": "Repeated attribute signals describing the brand.",
    "proof_points": "Evidence that supports credibility or claims.",
    "founder_or_press_context": "Founder, press, or contextual evidence that should not become the main claim by default.",
    "competitive_context": "Competitor or alternative evidence kept as context; it must not redefine the audited entity.",
    "noise_rejected": "Noise or fragments explicitly rejected during analysis.",
    "evidence_gaps": "Important gaps still blocking a stronger reading.",
    "confidence_notes": "Short notes explaining confidence or uncertainty.",
}


@dataclass(slots=True)
class ResearchEvidence:
    """One evidence item, annotated by its analytic role."""

    text: str
    kind: str = "evidence"
    source_url: str = ""
    source_type: str = ""
    source_label: str = ""
    surface_role: str = ""
    entity_scope: str = ""
    topic: str = ""
    confidence: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_evidence_kind(self.kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "kind": self.kind,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "source_label": self.source_label,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
            "topic": self.topic,
            "confidence": self.confidence,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchEvidence":
        return cls(
            text=str(data.get("text") or ""),
            kind=str(data.get("kind") or "evidence"),
            source_url=str(data.get("source_url") or ""),
            source_type=str(data.get("source_type") or ""),
            source_label=str(data.get("source_label") or ""),
            surface_role=str(data.get("surface_role") or ""),
            entity_scope=str(data.get("entity_scope") or ""),
            topic=str(data.get("topic") or ""),
            confidence=str(data.get("confidence") or ""),
            notes=_str_list(data.get("notes")),
        )


@dataclass(slots=True)
class BrandResearchPack:
    """Canonical organized evidence bundle for Brand3 analysis."""

    version: str
    input_url: str
    resolved_entity: EntityResolution
    entity_type: str
    parent_brand: str = ""
    official_urls: list[str] = field(default_factory=list)
    analyzed_urls: list[str] = field(default_factory=list)
    source_map: dict[str, ResearchSource] = field(default_factory=dict)
    company_summary: str = ""
    product_summary: str = ""
    audience: str = ""
    offer: str = ""
    outcome: str = ""
    category: str = ""
    declared_purpose: str = ""
    declared_mission: str = ""
    future_direction: str = ""
    tone_of_voice: str = ""
    personality_signals: list[str] = field(default_factory=list)
    visual_or_conceptual_signals: list[str] = field(default_factory=list)
    values_signals: list[str] = field(default_factory=list)
    attributes_signals: list[str] = field(default_factory=list)
    proof_points: list[ResearchEvidence] = field(default_factory=list)
    founder_or_press_context: list[ResearchEvidence] = field(default_factory=list)
    competitive_context: list[ResearchEvidence] = field(default_factory=list)
    noise_rejected: list[ResearchEvidence] = field(default_factory=list)
    shadow_sources: list[dict[str, Any]] = field(default_factory=list)
    evidence_gaps: list[str] = field(default_factory=list)
    confidence_notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_entity_type(self.entity_type)
        if self.resolved_entity.entity_type != self.entity_type:
            raise ValueError("resolved_entity.entity_type must match pack entity_type")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "input_url": self.input_url,
            "resolved_entity": self.resolved_entity.to_dict(),
            "entity_type": self.entity_type,
            "parent_brand": self.parent_brand,
            "official_urls": list(self.official_urls),
            "analyzed_urls": list(self.analyzed_urls),
            "source_map": {key: value.to_dict() for key, value in self.source_map.items()},
            "company_summary": self.company_summary,
            "product_summary": self.product_summary,
            "audience": self.audience,
            "offer": self.offer,
            "outcome": self.outcome,
            "category": self.category,
            "declared_purpose": self.declared_purpose,
            "declared_mission": self.declared_mission,
            "future_direction": self.future_direction,
            "tone_of_voice": self.tone_of_voice,
            "personality_signals": list(self.personality_signals),
            "visual_or_conceptual_signals": list(self.visual_or_conceptual_signals),
            "values_signals": list(self.values_signals),
            "attributes_signals": list(self.attributes_signals),
            "proof_points": [item.to_dict() for item in self.proof_points],
            "founder_or_press_context": [item.to_dict() for item in self.founder_or_press_context],
            "competitive_context": [item.to_dict() for item in self.competitive_context],
            "noise_rejected": [item.to_dict() for item in self.noise_rejected],
            "shadow_sources": [dict(item) for item in self.shadow_sources if isinstance(item, dict)],
            "evidence_gaps": list(self.evidence_gaps),
            "confidence_notes": list(self.confidence_notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrandResearchPack":
        resolved_entity = _require_dict(data.get("resolved_entity"), "resolved_entity")
        source_map_raw = data.get("source_map") or {}
        if not isinstance(source_map_raw, dict):
            source_map_raw = {}
        source_map = {
            str(key): ResearchSource.from_dict(value)
            for key, value in source_map_raw.items()
            if isinstance(value, dict)
        }
        return cls(
            version=str(data.get("version") or "brand_research_pack_v0_1"),
            input_url=str(data.get("input_url") or ""),
            resolved_entity=EntityResolution.from_dict(resolved_entity),
            entity_type=str(data.get("entity_type") or "unknown"),
            parent_brand=str(data.get("parent_brand") or ""),
            official_urls=_str_list(data.get("official_urls")),
            analyzed_urls=_str_list(data.get("analyzed_urls")),
            source_map=source_map,
            company_summary=str(data.get("company_summary") or ""),
            product_summary=str(data.get("product_summary") or ""),
            audience=str(data.get("audience") or ""),
            offer=str(data.get("offer") or ""),
            outcome=str(data.get("outcome") or ""),
            category=str(data.get("category") or ""),
            declared_purpose=str(data.get("declared_purpose") or ""),
            declared_mission=str(data.get("declared_mission") or ""),
            future_direction=str(data.get("future_direction") or ""),
            tone_of_voice=str(data.get("tone_of_voice") or ""),
            personality_signals=_str_list(data.get("personality_signals")),
            visual_or_conceptual_signals=_str_list(data.get("visual_or_conceptual_signals")),
            values_signals=_str_list(data.get("values_signals")),
            attributes_signals=_str_list(data.get("attributes_signals")),
            proof_points=_evidence_list(data.get("proof_points")),
            founder_or_press_context=_evidence_list(data.get("founder_or_press_context")),
            competitive_context=_evidence_list(data.get("competitive_context")),
            noise_rejected=_evidence_list(data.get("noise_rejected")),
            shadow_sources=_dict_list(data.get("shadow_sources")),
            evidence_gaps=_str_list(data.get("evidence_gaps")),
            confidence_notes=_str_list(data.get("confidence_notes")),
        )


def _evidence_list(value: Any) -> list[ResearchEvidence]:
    if not isinstance(value, list):
        return []
    return [ResearchEvidence.from_dict(item) for item in value if isinstance(item, dict)]


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    return value


def _validate_evidence_kind(value: str) -> None:
    if value not in ALLOWED_EVIDENCE_KINDS:
        raise ValueError(f"evidence kind must be one of {sorted(ALLOWED_EVIDENCE_KINDS)}")

