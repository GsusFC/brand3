"""Brand research acquisition planning.

This layer treats the input URL as a research seed. It composes the existing
deterministic discovery/search/entity-packet helpers into an explicit plan for
what should be fetched or searched before Brand3 interprets the brand.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.discovery.entity_discovery import discover_entity
from src.discovery.search_plan import build_discovery_search_plan
from src.reports.entity_research_packet import build_entity_research_packet


PLAN_VERSION = "brand_research_acquisition_plan_v0_1"


@dataclass(frozen=True)
class AcquisitionSource:
    url: str
    role: str
    entity_scope: str
    reason: str
    priority: int
    fetch_intent: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrandResearchAcquisitionPlan:
    version: str
    seed_url: str
    requested_name: str
    resolved_entity: str
    canonical_url: str
    analysis_mode: str
    entity_type: str
    parent_brand: str | None = None
    product_name: str | None = None
    confidence: float = 0.0
    sources_to_fetch: list[AcquisitionSource] = field(default_factory=list)
    queries_to_run: list[str] = field(default_factory=list)
    sources_to_ignore: list[dict[str, object]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    raw: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "seed_url": self.seed_url,
            "requested_name": self.requested_name,
            "resolved_entity": self.resolved_entity,
            "canonical_url": self.canonical_url,
            "analysis_mode": self.analysis_mode,
            "entity_type": self.entity_type,
            "parent_brand": self.parent_brand,
            "product_name": self.product_name,
            "confidence": self.confidence,
            "sources_to_fetch": [item.to_dict() for item in self.sources_to_fetch],
            "queries_to_run": list(self.queries_to_run),
            "sources_to_ignore": list(self.sources_to_ignore),
            "limitations": list(self.limitations),
            "raw": dict(self.raw),
        }


def build_brand_research_acquisition_plan(
    *,
    seed_url: str,
    brand_name: str = "",
    web_data: Any | None = None,
    exa_data: Any | None = None,
    context_data: Any | None = None,
) -> BrandResearchAcquisitionPlan:
    """Build a deterministic research plan from a URL seed."""
    discovery = discover_entity(
        brand_name,
        seed_url,
        web_data=web_data,
        exa_data=exa_data,
        context_data=context_data,
    )
    search_plan = build_discovery_search_plan(discovery, brand_name, seed_url)
    entity_packet = build_entity_research_packet(
        input_url=seed_url,
        brand_name=brand_name,
        entity_discovery=asdict(discovery),
        discovery_search_plan=asdict(search_plan),
        web_data=web_data,
        exa_data=exa_data,
    )
    entity_packet_dict = entity_packet.to_dict()
    limitations = _limitations(discovery, entity_packet_dict)
    return BrandResearchAcquisitionPlan(
        version=PLAN_VERSION,
        seed_url=entity_packet.input_url,
        requested_name=(brand_name or "").strip(),
        resolved_entity=discovery.entity_name,
        canonical_url=discovery.canonical_url,
        analysis_mode=search_plan.analysis_mode,
        entity_type=discovery.entity_type,
        parent_brand=discovery.parent_brand_name or entity_packet.parent_brand,
        product_name=discovery.product_name or entity_packet.product_name,
        confidence=round(float(discovery.confidence or 0.0), 4),
        sources_to_fetch=_sources_to_fetch(entity_packet_dict),
        queries_to_run=list(search_plan.queries),
        sources_to_ignore=_sources_to_ignore(entity_packet_dict),
        limitations=limitations,
        raw={
            "entity_discovery": asdict(discovery),
            "discovery_search_plan": asdict(search_plan),
            "entity_research_packet": entity_packet_dict,
        },
    )


def _sources_to_fetch(entity_packet: dict[str, Any]) -> list[AcquisitionSource]:
    surfaces = entity_packet.get("owned_surfaces") or []
    sources: list[AcquisitionSource] = []
    seen: set[str] = set()
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        url = str(surface.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        role = str(surface.get("role") or "owned_surface")
        sources.append(
            AcquisitionSource(
                url=url,
                role=role,
                entity_scope=str(surface.get("entity_scope") or "unknown"),
                reason=str(surface.get("reason") or ""),
                priority=_priority_for_role(role),
                fetch_intent=_fetch_intent_for_role(role),
            )
        )
    return sorted(sources, key=lambda item: (item.priority, item.url))


def _sources_to_ignore(entity_packet: dict[str, Any]) -> list[dict[str, object]]:
    ignored = []
    for surface in entity_packet.get("owned_surfaces") or []:
        if not isinstance(surface, dict):
            continue
        role = str(surface.get("role") or "")
        if role != "blog_feed":
            continue
        ignored.append(
            {
                "url": str(surface.get("url") or ""),
                "role": role,
                "reason": "Blog/feed surfaces are not first-pass owned brand evidence unless explicitly requested.",
            }
        )
    return ignored


def _limitations(discovery, entity_packet: dict[str, Any]) -> list[str]:
    limitations = list(discovery.warnings or [])
    limitations.extend(str(item) for item in entity_packet.get("limitations") or [])
    if float(discovery.confidence or 0.0) < 0.5:
        limitations.append("entity_resolution_low_confidence")
    if discovery.analysis_scope == "url_only":
        limitations.append("seed_url_only_no_verified_brand_entity")
    if len(entity_packet.get("owned_surfaces") or []) <= 1:
        limitations.append("owned_surface_expansion_missing")
    return _unique(limitations)


def _priority_for_role(role: str) -> int:
    return {
        "audited_surface": 10,
        "parent_home": 20,
        "product_system": 30,
        "mission_about": 40,
        "proof_customer": 50,
        "pricing": 60,
        "policy_security": 80,
        "owned_surface": 90,
        "blog_feed": 200,
    }.get(role, 100)


def _fetch_intent_for_role(role: str) -> str:
    return {
        "audited_surface": "seed_surface",
        "parent_home": "parent_brand_context",
        "product_system": "product_context",
        "mission_about": "mission_and_origin",
        "proof_customer": "customer_proof",
        "pricing": "commercial_offer",
        "policy_security": "trust_and_values",
        "blog_feed": "defer_by_default",
    }.get(role, "owned_context")


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
