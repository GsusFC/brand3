"""Evidence graph primitives for Brand Research.

The first implementation is intentionally deterministic and network-free. It
adapts an existing Brand Audit snapshot into a traceable graph of sources and
claims so the research contract can stabilize before adding new acquisition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.reports.strategic_evidence_packet import build_strategic_evidence_packet
from src.research.evidence_graph_sources import ALLOWED_SOURCE_TYPES, ResearchSource, build_sources
from src.research.evidence_graph_sources import _dict, _host, _is_social, _normalize_url, _root_domain, _source_id, _str_list, _unique, _validate
from src.research.evidence_graph_support import (
    _dict_list,
    _entity_boundary_warnings,
    _entity_packet,
    _entity_type,
    _graph_gaps,
    _optional_int,
    _shadow_sources_from_snapshot,
)


GRAPH_VERSION = "brand_research_evidence_graph_v0_1"

ALLOWED_CLAIM_TYPES = {
    "hero_claim",
    "product_offer",
    "audience",
    "outcome",
    "mission",
    "vision",
    "values",
    "personality",
    "proof",
    "founder_press",
    "feature_evidence",
    "noise",
    "unknown",
}

_GROUP_TO_CLAIM_TYPE = {
    "hero_claims": "hero_claim",
    "product_offer": "product_offer",
    "audience": "audience",
    "outcome": "outcome",
    "mission_language": "mission",
    "vision_language": "vision",
    "values_language": "values",
    "personality_tone": "personality",
    "proof_points": "proof",
    "third_party_context": "founder_press",
}

_GROUP_TO_BLOCKS = {
    "hero_claims": ["magnetism", "brand_idea"],
    "product_offer": ["value_proposition", "brand_idea"],
    "audience": ["value_proposition"],
    "outcome": ["core_purpose", "value_proposition"],
    "mission_language": ["core_purpose", "mission"],
    "vision_language": ["vision"],
    "values_language": ["values", "attributes"],
    "personality_tone": ["personality", "attributes"],
    "proof_points": ["value_proposition", "magnetism"],
    "third_party_context": ["brand_idea", "mission", "vision"],
}


@dataclass(slots=True)
class EvidenceClaim:
    """One traceable claim extracted from research evidence."""

    claim_id: str
    text: str
    claim_type: str
    quote: str = ""
    source_id: str = ""
    source_url: str = ""
    source_type: str = "unknown"
    surface_role: str = ""
    entity_scope: str = ""
    confidence: str = ""
    freshness_days: int | None = None
    supports_blocks: list[str] = field(default_factory=list)
    contradicts: list[str] = field(default_factory=list)
    secondary_source_ids: list[str] = field(default_factory=list)
    secondary_source_urls: list[str] = field(default_factory=list)
    secondary_origins: list[str] = field(default_factory=list)
    noise_reason: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate(self.claim_type, ALLOWED_CLAIM_TYPES, "claim_type")
        _validate(self.source_type, ALLOWED_SOURCE_TYPES, "source_type")

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "claim_type": self.claim_type,
            "quote": self.quote,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
            "confidence": self.confidence,
            "freshness_days": self.freshness_days,
            "supports_blocks": list(self.supports_blocks),
            "contradicts": list(self.contradicts),
            "secondary_source_ids": list(self.secondary_source_ids),
            "secondary_source_urls": list(self.secondary_source_urls),
            "secondary_origins": list(self.secondary_origins),
            "noise_reason": self.noise_reason,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceClaim":
        freshness = data.get("freshness_days")
        return cls(
            claim_id=str(data.get("claim_id") or ""),
            text=str(data.get("text") or ""),
            claim_type=str(data.get("claim_type") or "unknown"),
            quote=str(data.get("quote") or ""),
            source_id=str(data.get("source_id") or ""),
            source_url=str(data.get("source_url") or ""),
            source_type=str(data.get("source_type") or "unknown"),
            surface_role=str(data.get("surface_role") or ""),
            entity_scope=str(data.get("entity_scope") or ""),
            confidence=str(data.get("confidence") or ""),
            freshness_days=int(freshness) if freshness is not None else None,
            supports_blocks=_str_list(data.get("supports_blocks")),
            contradicts=_str_list(data.get("contradicts")),
            secondary_source_ids=_str_list(data.get("secondary_source_ids")),
            secondary_source_urls=_str_list(data.get("secondary_source_urls")),
            secondary_origins=_str_list(data.get("secondary_origins")),
            noise_reason=str(data.get("noise_reason") or ""),
            notes=_str_list(data.get("notes")),
        )


@dataclass(slots=True)
class BrandResearchRun:
    """Run-level identity and provenance."""

    run_id: int | None
    brand_name: str
    input_url: str
    resolved_entity: str = ""
    entity_type: str = "unknown"
    parent_brand: str = ""
    confidence: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "brand_name": self.brand_name,
            "input_url": self.input_url,
            "resolved_entity": self.resolved_entity,
            "entity_type": self.entity_type,
            "parent_brand": self.parent_brand,
            "confidence": self.confidence,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrandResearchRun":
        run_id = data.get("run_id")
        return cls(
            run_id=int(run_id) if run_id is not None else None,
            brand_name=str(data.get("brand_name") or ""),
            input_url=str(data.get("input_url") or ""),
            resolved_entity=str(data.get("resolved_entity") or ""),
            entity_type=str(data.get("entity_type") or "unknown"),
            parent_brand=str(data.get("parent_brand") or ""),
            confidence=str(data.get("confidence") or ""),
            notes=_str_list(data.get("notes")),
        )


@dataclass(slots=True)
class EvidenceGraph:
    """Structured evidence base that downstream Brand3 products can consume."""

    version: str
    run: BrandResearchRun
    sources: dict[str, ResearchSource] = field(default_factory=dict)
    claims: list[EvidenceClaim] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    shadow_sources: list[dict[str, Any]] = field(default_factory=list)
    dedupe_stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "run": self.run.to_dict(),
            "sources": {key: value.to_dict() for key, value in self.sources.items()},
            "claims": [claim.to_dict() for claim in self.claims],
            "gaps": list(self.gaps),
            "warnings": list(self.warnings),
            "shadow_sources": [dict(item) for item in self.shadow_sources if isinstance(item, dict)],
            "dedupe_stats": dict(self.dedupe_stats),
            "summary": self.summary(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceGraph":
        sources_raw = data.get("sources") if isinstance(data.get("sources"), dict) else {}
        claims_raw = data.get("claims") if isinstance(data.get("claims"), list) else []
        return cls(
            version=str(data.get("version") or GRAPH_VERSION),
            run=BrandResearchRun.from_dict(_dict(data.get("run"))),
            sources={
                str(key): ResearchSource.from_dict(value)
                for key, value in sources_raw.items()
                if isinstance(value, dict)
            },
            claims=[EvidenceClaim.from_dict(item) for item in claims_raw if isinstance(item, dict)],
            gaps=_str_list(data.get("gaps")),
            warnings=_str_list(data.get("warnings")),
            shadow_sources=_dict_list(data.get("shadow_sources")),
            dedupe_stats=_dict(data.get("dedupe_stats")),
        )

    def summary(self) -> dict[str, Any]:
        source_counts: dict[str, int] = {}
        claim_counts: dict[str, int] = {}
        block_counts: dict[str, int] = {}
        for source in self.sources.values():
            source_counts[source.source_type] = source_counts.get(source.source_type, 0) + 1
        for claim in self.claims:
            claim_counts[claim.claim_type] = claim_counts.get(claim.claim_type, 0) + 1
            for block in claim.supports_blocks:
                block_counts[block] = block_counts.get(block, 0) + 1
        return {
            "source_count": len(self.sources),
            "claim_count": len(self.claims),
            "shadow_source_count": len(self.shadow_sources),
            "dedupe_stats": dict(self.dedupe_stats),
            "source_counts": dict(sorted(source_counts.items())),
            "claim_counts": dict(sorted(claim_counts.items())),
            "supported_block_counts": dict(sorted(block_counts.items())),
            "noise_claim_count": claim_counts.get("noise", 0),
        }
from src.research.evidence_graph_claims import build_claims_from_snapshot


def build_evidence_graph_from_snapshot(snapshot: dict[str, Any]) -> EvidenceGraph:
    """Build an evidence graph from an existing Brand Audit snapshot."""

    run_payload = _dict(snapshot.get("run"))
    input_url = _normalize_url(str(run_payload.get("url") or ""))
    entity_packet = _entity_packet(snapshot)
    strategic_packet = build_strategic_evidence_packet(snapshot)
    run = BrandResearchRun(
        run_id=_optional_int(run_payload.get("id")),
        brand_name=str(run_payload.get("brand_name") or ""),
        input_url=input_url,
        resolved_entity=str((entity_packet or {}).get("entity_name") or run_payload.get("brand_name") or ""),
        entity_type=_entity_type(entity_packet, input_url),
        parent_brand=str((entity_packet or {}).get("parent_brand") or ""),
        confidence=str((entity_packet or {}).get("confidence") or ""),
        notes=_str_list((entity_packet or {}).get("limitations")),
    )

    sources = build_sources(snapshot, entity_packet=entity_packet)
    claims, dedupe_stats = build_claims_from_snapshot(snapshot, sources=sources, strategic_packet=strategic_packet)
    gaps = _graph_gaps(sources, claims)
    warnings = _unique(_str_list(strategic_packet.warnings) + _entity_boundary_warnings(sources))
    return EvidenceGraph(
        version=GRAPH_VERSION,
        run=run,
        sources=sources,
        claims=claims,
        gaps=gaps,
        warnings=warnings,
        shadow_sources=_shadow_sources_from_snapshot(snapshot),
        dedupe_stats=dedupe_stats,
    )


def _dedupe_claims(
    claims: list[EvidenceClaim],
    *,
    sources: dict[str, ResearchSource],
) -> tuple[list[EvidenceClaim], dict[str, Any]]:
    from src.research.evidence_graph_claims import _dedupe_claims as _claims_dedupe_claims

    return _claims_dedupe_claims(claims, sources=sources)
