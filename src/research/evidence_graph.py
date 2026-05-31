"""Evidence graph primitives for Brand Research.

The first implementation is intentionally deterministic and network-free. It
adapts an existing Brand Audit snapshot into a traceable graph of sources and
claims so the research contract can stabilize before adding new acquisition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
import hashlib
import re

from src.reports.derivation import collect_evidences
from src.reports.entity_research_packet import entity_scope_for_url, surface_role_for_url
from src.reports.strategic_evidence_packet import StrategicEvidenceLine, build_strategic_evidence_packet


GRAPH_VERSION = "brand_research_evidence_graph_v0_1"

ALLOWED_SOURCE_TYPES = {
    "owned_home",
    "owned_about",
    "owned_product",
    "owned_pricing",
    "owned_security",
    "owned_docs",
    "owned_proof",
    "press_founder",
    "third_party_review",
    "third_party_context",
    "social",
    "competitor_context",
    "noise",
    "unknown",
}

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

_SUBPAGE_RE = re.compile(r"(?:^|\n)## Subpage:\s*(?P<url>\S+)\s*\n", re.IGNORECASE)

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
class ResearchSource:
    """One discovered or analyzed surface."""

    source_id: str
    url: str
    source_type: str
    label: str = ""
    surface_role: str = ""
    entity_scope: str = ""
    title: str = ""
    origin: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate(self.source_type, ALLOWED_SOURCE_TYPES, "source_type")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "source_type": self.source_type,
            "label": self.label,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
            "title": self.title,
            "origin": self.origin,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchSource":
        return cls(
            source_id=str(data.get("source_id") or ""),
            url=str(data.get("url") or ""),
            source_type=str(data.get("source_type") or "unknown"),
            label=str(data.get("label") or ""),
            surface_role=str(data.get("surface_role") or ""),
            entity_scope=str(data.get("entity_scope") or ""),
            title=str(data.get("title") or ""),
            origin=str(data.get("origin") or ""),
            notes=_str_list(data.get("notes")),
        )


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "run": self.run.to_dict(),
            "sources": {key: value.to_dict() for key, value in self.sources.items()},
            "claims": [claim.to_dict() for claim in self.claims],
            "gaps": list(self.gaps),
            "warnings": list(self.warnings),
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
            "source_counts": dict(sorted(source_counts.items())),
            "claim_counts": dict(sorted(claim_counts.items())),
            "supported_block_counts": dict(sorted(block_counts.items())),
            "noise_claim_count": claim_counts.get("noise", 0),
        }


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

    sources = _build_sources(snapshot, entity_packet=entity_packet)
    claims = _build_claims(snapshot, sources=sources, strategic_packet=strategic_packet)
    gaps = _graph_gaps(sources, claims)
    warnings = _str_list(strategic_packet.warnings)
    return EvidenceGraph(
        version=GRAPH_VERSION,
        run=run,
        sources=sources,
        claims=claims,
        gaps=gaps,
        warnings=warnings,
    )


def _build_sources(snapshot: dict[str, Any], *, entity_packet: dict[str, Any] | None) -> dict[str, ResearchSource]:
    run = _dict(snapshot.get("run"))
    input_url = _normalize_url(str(run.get("url") or ""))
    brand_domain = _root_domain(_host(input_url))
    sources: dict[str, ResearchSource] = {}

    def add(
        url: str,
        *,
        source_type: str,
        label: str = "",
        title: str = "",
        origin: str = "",
        surface_role: str = "",
        entity_scope: str = "",
        notes: list[str] | None = None,
    ) -> None:
        normalized = _normalize_url(url)
        if not normalized:
            return
        source_type = source_type if source_type in ALLOWED_SOURCE_TYPES else "unknown"
        source_id = _source_id(normalized)
        if source_id in sources:
            existing = sources[source_id]
            sources[source_id] = ResearchSource(
                source_id=source_id,
                url=existing.url,
                source_type=_prefer_source_type(existing.source_type, source_type),
                label=existing.label or label,
                surface_role=_prefer_annotation(existing.surface_role, surface_role),
                entity_scope=_prefer_annotation(existing.entity_scope, entity_scope),
                title=existing.title or title,
                origin=existing.origin or origin,
                notes=_unique(existing.notes + (notes or [])),
            )
            return
        sources[source_id] = ResearchSource(
            source_id=source_id,
            url=normalized,
            source_type=source_type,
            label=label,
            surface_role=surface_role,
            entity_scope=entity_scope,
            title=title,
            origin=origin,
            notes=_unique(notes or []),
        )

    if input_url:
        add(
            input_url,
            source_type="owned_home",
            label="input_url",
            title=str(run.get("brand_name") or ""),
            origin="run",
            surface_role="audited_surface",
            entity_scope="audited_surface",
            notes=["Initial URL supplied to Brand Audit."],
        )

    for raw_input in snapshot.get("raw_inputs") or []:
        source = str(raw_input.get("source") or "")
        payload = _dict(raw_input.get("payload"))
        if source == "web":
            text = str(payload.get("markdown_content") or payload.get("content") or "")
            for url in _web_urls(payload, fallback=input_url):
                add(
                    url,
                    source_type=_classify_source_url(url, brand_domain=brand_domain, text=text),
                    label=str(payload.get("title") or "web"),
                    title=str(payload.get("title") or ""),
                    origin="raw_inputs.web",
                    surface_role=surface_role_for_url(url, entity_packet),
                    entity_scope=entity_scope_for_url(url, entity_packet),
                    notes=["Owned web content collected by Brand Audit."],
                )
        elif source == "exa":
            for collection in ("mentions", "news", "ai_visibility_results", "competitors"):
                for item in payload.get(collection) or []:
                    if not isinstance(item, dict):
                        continue
                    url = str(item.get("url") or "")
                    text = " ".join(
                        part
                        for part in [
                            str(item.get("title") or ""),
                            str(item.get("summary") or ""),
                            str(item.get("text") or ""),
                            " ".join(str(h) for h in item.get("highlights") or []),
                        ]
                        if part.strip()
                    )
                    source_type = "competitor_context" if collection == "competitors" else _classify_source_url(
                        url,
                        brand_domain=brand_domain,
                        text=text,
                        external=True,
                    )
                    add(
                        url,
                        source_type=source_type,
                        label=str(item.get("title") or collection),
                        title=str(item.get("title") or ""),
                        origin=f"raw_inputs.exa.{collection}",
                        surface_role="external_context",
                        entity_scope="external_context",
                        notes=["External discovery evidence collected by Brand Audit."],
                    )
        elif source == "social":
            for url in _social_urls(payload):
                add(
                    url,
                    source_type="social",
                    label=str(payload.get("brand_name") or "social"),
                    origin="raw_inputs.social",
                    surface_role="social",
                    entity_scope="external_context",
                )
        elif source == "competitors":
            for url in _competitor_urls(payload):
                add(
                    url,
                    source_type="competitor_context",
                    label="competitor",
                    origin="raw_inputs.competitors",
                    surface_role="external_context",
                    entity_scope="external_context",
                )

    if entity_packet:
        for surface in list(entity_packet.get("owned_surfaces") or []) + list(entity_packet.get("product_surfaces") or []):
            if not isinstance(surface, dict):
                continue
            url = str(surface.get("url") or "")
            role = str(surface.get("role") or "")
            add(
                url,
                source_type=_source_type_from_entity_role(role, url),
                label=role or "owned_surface",
                origin="entity_research_packet",
                surface_role=role,
                entity_scope=str(surface.get("entity_scope") or ""),
                notes=[str(surface.get("reason") or "Owned surface from entity research packet.")],
            )

    for evidence in collect_evidences(snapshot):
        if not evidence.url:
            continue
        add(
            str(evidence.url),
            source_type=_classify_source_url(str(evidence.url), brand_domain=brand_domain, text=str(evidence.quote or "")),
            label=str(evidence.feature_name or "feature_evidence"),
            origin="feature_or_evidence_item",
            surface_role="evidence",
            entity_scope="evidence",
            notes=[f"Feature evidence from {evidence.dimension}."],
        )

    return dict(sorted(sources.items()))


def _build_claims(snapshot: dict[str, Any], *, sources: dict[str, ResearchSource], strategic_packet) -> list[EvidenceClaim]:
    claims: list[EvidenceClaim] = []
    seen: set[tuple[str, str, str]] = set()

    def add(
        text: str,
        *,
        claim_type: str,
        source_url: str = "",
        quote: str = "",
        confidence: str = "",
        supports_blocks: list[str] | None = None,
        noise_reason: str = "",
        notes: list[str] | None = None,
        surface_role: str = "",
        entity_scope: str = "",
    ) -> None:
        cleaned = _clean(text)
        source_url_norm = _normalize_url(source_url)
        if not cleaned and not source_url_norm:
            return
        source_id = _source_id(source_url_norm) if source_url_norm else ""
        source = sources.get(source_id)
        source_type = source.source_type if source else ("noise" if claim_type == "noise" else "unknown")
        key = (cleaned.lower(), source_id, claim_type)
        if key in seen:
            return
        seen.add(key)
        claims.append(
            EvidenceClaim(
                claim_id=_claim_id(claim_type, cleaned, source_id),
                text=cleaned,
                claim_type=claim_type if claim_type in ALLOWED_CLAIM_TYPES else "unknown",
                quote=quote or cleaned,
                source_id=source_id,
                source_url=source_url_norm,
                source_type=source_type,
                surface_role=surface_role or (source.surface_role if source else ""),
                entity_scope=entity_scope or (source.entity_scope if source else ""),
                confidence=confidence or ("high" if source_url_norm and claim_type != "noise" else "low"),
                supports_blocks=_unique(supports_blocks or []),
                noise_reason=noise_reason,
                notes=_unique(notes or []),
            )
        )

    for group, lines in strategic_packet.groups.items():
        claim_type = _GROUP_TO_CLAIM_TYPE.get(group, "unknown")
        supports_blocks = _GROUP_TO_BLOCKS.get(group, [])
        for line in lines:
            if not isinstance(line, StrategicEvidenceLine):
                continue
            add(
                line.text,
                claim_type=claim_type,
                source_url=str(line.url or ""),
                confidence="high" if line.url else "medium",
                supports_blocks=supports_blocks,
                notes=[f"Strategic evidence group: {group}."],
                surface_role=str(line.surface_role or ""),
                entity_scope=str(line.entity_scope or ""),
            )

    for evidence in collect_evidences(snapshot):
        add(
            str(evidence.quote or evidence.url or ""),
            claim_type="feature_evidence",
            source_url=str(evidence.url or ""),
            confidence="medium",
            notes=[f"Feature evidence: {evidence.dimension}/{evidence.feature_name}."],
        )

    for raw_input in snapshot.get("raw_inputs") or []:
        if raw_input.get("source") != "exa":
            continue
        payload = _dict(raw_input.get("payload"))
        for collection in ("news", "mentions", "ai_visibility_results"):
            for item in payload.get(collection) or []:
                if not isinstance(item, dict):
                    continue
                text = _clean(
                    " ".join(
                        part
                        for part in [
                            str(item.get("title") or ""),
                            str(item.get("summary") or ""),
                            str(item.get("text") or ""),
                        ]
                        if part.strip()
                    )
                )
                url = str(item.get("url") or "")
                if not text or not url:
                    continue
                source = sources.get(_source_id(_normalize_url(url)))
                claim_type = _claim_type_for_external_source(source.source_type if source else "unknown", text)
                add(
                    text,
                    claim_type=claim_type,
                    source_url=url,
                    confidence="medium",
                    supports_blocks=_blocks_for_external_claim_type(claim_type),
                    notes=[f"Supplemental external evidence from raw_inputs.exa.{collection}."],
                )

    web_url = _snapshot_web_url(snapshot)
    for item in strategic_packet.rejected:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "")
        recovered_type = _recovered_claim_type(text, str(item.get("reason") or ""))
        if recovered_type:
            add(
                text,
                claim_type=recovered_type,
                source_url=web_url,
                confidence="medium",
                supports_blocks=_blocks_for_recovered_claim_type(recovered_type),
                notes=["Recovered from low-signal strategic packet rejection for EvidenceGraph review."],
            )
        add(
            text,
            claim_type="noise",
            source_url=web_url,
            confidence="low",
            noise_reason=str(item.get("reason") or "rejected_by_strategic_packet"),
            notes=["Rejected while grouping strategic evidence."],
        )

    return sorted(claims, key=lambda claim: (claim.claim_type, claim.source_url, claim.text))


def _claim_type_for_external_source(source_type: str, text: str) -> str:
    low = text.lower()
    if source_type == "press_founder" or any(marker in low for marker in ("founder", "interview", "launch", "raises", "funding", "acquired")):
        return "founder_press"
    if source_type == "third_party_review" or any(marker in low for marker in ("review", "customer", "testimonial", "case study")):
        return "proof"
    if source_type == "competitor_context":
        return "unknown"
    return "unknown"


def _blocks_for_external_claim_type(claim_type: str) -> list[str]:
    if claim_type == "founder_press":
        return ["brand_idea", "mission", "vision"]
    if claim_type == "proof":
        return ["value_proposition", "magnetism"]
    return []


def _recovered_claim_type(text: str, reason: str) -> str:
    if reason not in {"low_strategic_signal", "duplicate"}:
        return ""
    low = text.lower()
    if not low.strip() or _looks_like_form_or_chrome(low):
        return ""
    if any(marker in low for marker in ("smarter way", "new home for your internet", "fresh take")):
        return "hero_claim"
    if any(
        marker in low
        for marker in (
            "browser",
            "tabs",
            "workspaces",
            "split screen",
            "search your internet",
            "ask anything",
            "answers in context",
            "airis",
        )
    ):
        return "product_offer"
    if any(marker in low for marker in ("organize", "flow through", "work smarter", "multitasking", "easier", "faster")):
        return "outcome"
    return ""


def _blocks_for_recovered_claim_type(claim_type: str) -> list[str]:
    return {
        "hero_claim": ["magnetism", "brand_idea"],
        "product_offer": ["value_proposition", "brand_idea"],
        "outcome": ["core_purpose", "value_proposition"],
    }.get(claim_type, [])


def _looks_like_form_or_chrome(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "download free",
            "download started",
            "click here",
            "email below",
            "submit",
            "continue without accepting",
            "privacy policy",
            "terms",
            "copyright",
            "©",
            "in 2022",
            "recap",
            "year in review",
            "blog",
            "what should we call you",
            "how can we reach you",
            "slack",
            "wrong answers",
            "sitemap.xml",
            "robots.txt",
            "key pages found",
            "local image analysis",
            "whitespace ratio",
        )
    )


def _graph_gaps(sources: dict[str, ResearchSource], claims: list[EvidenceClaim]) -> list[str]:
    source_types = {source.source_type for source in sources.values()}
    claim_types = {claim.claim_type for claim in claims if claim.claim_type != "noise"}
    gaps: list[str] = []
    if not source_types.intersection({"owned_about", "owned_product", "owned_security", "owned_docs", "owned_proof"}):
        gaps.append("No strategic owned subpage evidence is present in the current graph.")
    if not source_types.intersection({"press_founder", "third_party_review", "third_party_context"}):
        gaps.append("No third-party contextual evidence is present in the current graph.")
    if "proof" not in claim_types:
        gaps.append("No explicit proof claims were extracted.")
    if not any(claim.supports_blocks for claim in claims):
        gaps.append("No claims are mapped to Brand3 TLDR blocks.")
    return gaps


def _entity_packet(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") == "entity_research_packet" and isinstance(raw_input.get("payload"), dict):
            return raw_input["payload"]
    audit = (_dict(snapshot.get("run")).get("audit") or {})
    packet = audit.get("entity_research_packet") if isinstance(audit, dict) else None
    return packet if isinstance(packet, dict) else None


def _entity_type(entity_packet: dict[str, Any] | None, input_url: str) -> str:
    if entity_packet:
        architecture = str(entity_packet.get("brand_architecture") or "")
        audited_type = str(entity_packet.get("audited_surface_type") or "")
        if architecture == "single_brand_surface":
            return "company"
        if audited_type in {"product_surface", "product_lab"}:
            return "product"
        if audited_type == "secondary_surface":
            return "sub_brand"
    path = (urlparse(input_url).path or "").lower()
    if any(marker in path for marker in ("/blog", "/news", "/article", "/post")):
        return "content"
    host = _host(input_url)
    root = _root_domain(host)
    if host and root and host != root and not host.startswith("www."):
        return "product"
    return "company" if input_url else "unknown"


def _web_urls(payload: dict[str, Any], *, fallback: str = "") -> list[str]:
    urls: list[str] = []
    for key in ("canonical_url", "url", "page_url", "input_url"):
        value = str(payload.get(key) or "").strip()
        if value:
            urls.append(value)
    urls.extend(str(url) for url in payload.get("owned_fallback_urls") or [] if str(url).strip())
    markdown = str(payload.get("markdown_content") or payload.get("content") or "")
    urls.extend(match.group("url") for match in _SUBPAGE_RE.finditer(markdown))
    if fallback:
        urls.append(fallback)
    return _unique(_normalize_url(url) for url in urls)


def _social_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for key in ("profiles", "platforms", "profile_urls"):
        value = payload.get(key)
        if isinstance(value, dict):
            for item in value.values():
                if isinstance(item, dict):
                    urls.append(str(item.get("url") or item.get("profile_url") or ""))
                else:
                    urls.append(str(item))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    urls.append(str(item.get("url") or item.get("profile_url") or ""))
    return _unique(_normalize_url(url) for url in urls)


def _competitor_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in payload.get("competitors") or []:
        if isinstance(item, dict):
            urls.append(str(item.get("url") or item.get("website") or ""))
    return _unique(_normalize_url(url) for url in urls)


def _snapshot_web_url(snapshot: dict[str, Any]) -> str:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") == "web" and isinstance(raw_input.get("payload"), dict):
            return _normalize_url(str(raw_input["payload"].get("canonical_url") or raw_input["payload"].get("url") or ""))
    return _normalize_url(str(_dict(snapshot.get("run")).get("url") or ""))


def _classify_source_url(url: str, *, brand_domain: str, text: str = "", external: bool = False) -> str:
    normalized = _normalize_url(url)
    host = _host(normalized)
    path = (urlparse(normalized).path or "/").lower()
    text_low = text.lower()
    if not normalized:
        return "unknown"
    if _is_social(host):
        return "social"
    if brand_domain and (host == brand_domain or host.endswith("." + brand_domain)):
        if path in {"", "/"}:
            return "owned_home"
        if any(marker in path for marker in ("/about", "/company", "/mission", "/manifesto", "/team", "/story", "/principles")):
            return "owned_about"
        if any(marker in path for marker in ("/security", "/privacy", "/trust", "/legal", "/terms", "/compliance")):
            return "owned_security"
        if any(marker in path for marker in ("/docs", "/documentation", "/developers", "/api", "/help", "/support")):
            return "owned_docs"
        if any(marker in path for marker in ("/pricing", "/plans")):
            return "owned_pricing"
        if any(marker in path for marker in ("/customers", "/case", "/stories", "/testimonials", "/reviews")):
            return "owned_proof"
        if any(marker in path for marker in ("/product", "/products", "/platform", "/solution", "/solutions", "/app", "/demo", "/lab", "/natureos")):
            return "owned_product"
        if any(marker in path for marker in ("/blog", "/news", "/feed", "/article", "/post", "/resources")):
            return "noise"
        return "owned_home"
    if external and any(marker in text_low for marker in ("founder", "interview", "launch", "raises", "raised", "funding", "acquired", "press")):
        return "press_founder"
    if external and any(marker in text_low for marker in ("review", "customer", "testimonial", "case study", "trusted by", "used by")):
        return "third_party_review"
    if external:
        return "third_party_context"
    return "unknown"


def _source_type_from_entity_role(role: str, url: str) -> str:
    if role.startswith("product:"):
        return "owned_product"
    if role in {"audited_surface", "parent_home"}:
        return "owned_home"
    if role == "mission_about":
        return "owned_about"
    if role == "product_system":
        return "owned_product"
    if role == "policy_security":
        return "owned_security"
    if role == "pricing":
        return "owned_pricing"
    if role == "proof_customer":
        return "owned_proof"
    return _classify_source_url(url, brand_domain=_root_domain(_host(url)))


def _prefer_source_type(existing: str, candidate: str) -> str:
    priority = {
        "unknown": 0,
        "noise": 1,
        "owned_home": 2,
        "third_party_context": 2,
        "social": 2,
        "competitor_context": 2,
        "press_founder": 3,
        "third_party_review": 3,
        "owned_about": 4,
        "owned_pricing": 4,
        "owned_security": 4,
        "owned_docs": 4,
        "owned_proof": 4,
        "owned_product": 5,
    }
    if priority.get(candidate, 0) > priority.get(existing, 0):
        return candidate
    if existing in {"unknown", "noise"} and candidate not in {"unknown", "noise"}:
        return candidate
    return existing


def _prefer_annotation(existing: str, candidate: str) -> str:
    if not candidate:
        return existing
    if not existing:
        return candidate
    if candidate.startswith("product:") or existing in {"unknown", "external_context", "evidence", "owned_surface"}:
        return candidate
    return existing


def _source_id(url: str) -> str:
    normalized = _normalize_url(url)
    if not normalized:
        return ""
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:10]
    return f"src_{digest}"


def _claim_id(claim_type: str, text: str, source_id: str) -> str:
    raw = "|".join([claim_type, source_id, text])
    return f"claim_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def _normalize_url(value: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    path = parsed.path if parsed.netloc else ""
    if path == "/":
        path = ""
    return f"{parsed.scheme or 'https'}://{host}{path}".rstrip("/")


def _host(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _is_social(host: str) -> bool:
    return host.endswith((
        "linkedin.com",
        "x.com",
        "twitter.com",
        "instagram.com",
        "youtube.com",
        "tiktok.com",
        "facebook.com",
        "github.com",
    ))


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _unique(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _validate(value: str, allowed: set[str], field_name: str) -> None:
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")
