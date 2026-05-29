"""Brand Research Pack v0.1.

This module defines the canonical evidence container that should exist before
TLDR Brand3 writes block-level interpretations. It keeps entity resolution,
evidence classification, source metadata, and analyst notes in one structured
object so the TLDR layer can consume organized evidence instead of raw scraper
fragments.

Field guide:
- input_url: the original URL being analyzed.
- resolved_entity: canonical entity resolution for the input surface.
- entity_type: the coarse entity class for the analysis target.
- parent_brand: parent brand name when the input is a product or sub-brand.
- official_urls: URLs considered official/owned for this entity.
- analyzed_urls: URLs that were actually inspected.
- source_map: source metadata keyed by a stable source key, usually a URL.
- company_summary: short summary of the company-level reading.
- product_summary: short summary of the product-level reading.
- audience: who the offer appears to be for.
- offer: what is being offered.
- outcome: what changes for the audience.
- category: the market/category framing.
- declared_purpose: explicit purpose language from the brand.
- declared_mission: explicit mission language from the brand.
- future_direction: future/category-change language.
- tone_of_voice: the observed tone of voice.
- personality_signals: short signals describing personality.
- visual_or_conceptual_signals: visual/metaphorical concept signals.
- values_signals: repeated value or belief signals.
- attributes_signals: repeated attribute signals.
- proof_points: supporting proof, credibility, or validation evidence.
- founder_or_press_context: founder, press, or other contextual evidence.
- noise_rejected: rejected evidence kept for auditability.
- evidence_gaps: missing evidence that still blocks a stronger reading.
- confidence_notes: short notes about confidence or limitations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any
from urllib.parse import urlparse

from src.reports.derivation import collect_evidences
from src.reports.entity_research_packet import (
    entity_scope_for_url,
    surface_role_for_url,
)
from src.reports.strategic_evidence_packet import (
    StrategicEvidenceLine,
    build_strategic_evidence_packet,
)


ALLOWED_ENTITY_TYPES = {
    "company",
    "brand",
    "product",
    "sub_brand",
    "campaign",
    "content",
    "unknown",
}
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
    "noise_rejected": "Noise or fragments explicitly rejected during analysis.",
    "evidence_gaps": "Important gaps still blocking a stronger reading.",
    "confidence_notes": "Short notes explaining confidence or uncertainty.",
}


@dataclass(slots=True)
class ResearchSource:
    """Metadata for one analyzed source or owned surface."""

    url: str
    source_type: str
    label: str = ""
    surface_role: str = ""
    entity_scope: str = ""
    title: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "source_type": self.source_type,
            "label": self.label,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
            "title": self.title,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchSource:
        return cls(
            url=str(data.get("url") or ""),
            source_type=str(data.get("source_type") or ""),
            label=str(data.get("label") or ""),
            surface_role=str(data.get("surface_role") or ""),
            entity_scope=str(data.get("entity_scope") or ""),
            title=str(data.get("title") or ""),
            notes=_str_list(data.get("notes")),
        )


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
    def from_dict(cls, data: dict[str, Any]) -> ResearchEvidence:
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
class EntityResolution:
    """Canonical entity interpretation for the input surface."""

    resolved_entity: str
    entity_type: str
    canonical_url: str = ""
    parent_brand: str = ""
    surface_role: str = ""
    entity_scope: str = ""
    confidence: str = ""
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_entity_type(self.entity_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolved_entity": self.resolved_entity,
            "entity_type": self.entity_type,
            "canonical_url": self.canonical_url,
            "parent_brand": self.parent_brand,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
            "confidence": self.confidence,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityResolution:
        return cls(
            resolved_entity=str(data.get("resolved_entity") or ""),
            entity_type=str(data.get("entity_type") or "unknown"),
            canonical_url=str(data.get("canonical_url") or ""),
            parent_brand=str(data.get("parent_brand") or ""),
            surface_role=str(data.get("surface_role") or ""),
            entity_scope=str(data.get("entity_scope") or ""),
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
    noise_rejected: list[ResearchEvidence] = field(default_factory=list)
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
            "noise_rejected": [item.to_dict() for item in self.noise_rejected],
            "evidence_gaps": list(self.evidence_gaps),
            "confidence_notes": list(self.confidence_notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrandResearchPack:
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
            noise_rejected=_evidence_list(data.get("noise_rejected")),
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


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dict")
    return value


def _validate_entity_type(value: str) -> None:
    if value not in ALLOWED_ENTITY_TYPES:
        raise ValueError(f"entity_type must be one of {sorted(ALLOWED_ENTITY_TYPES)}")


def _validate_evidence_kind(value: str) -> None:
    if value not in ALLOWED_EVIDENCE_KINDS:
        raise ValueError(f"evidence kind must be one of {sorted(ALLOWED_EVIDENCE_KINDS)}")


def build_brand_research_pack_from_snapshot(snapshot: dict[str, Any]) -> BrandResearchPack:
    """Adapt a persisted Brand Audit snapshot into a canonical research pack.

    The builder does not scrape, search, or enrich. It only reorganizes already
    collected snapshot data into a structure that a downstream analyst LLM can
    read without re-deriving the evidence graph.
    """

    run = snapshot.get("run") or {}
    raw_inputs = snapshot.get("raw_inputs") or []
    strategic_packet = build_strategic_evidence_packet(snapshot)
    entity_packet = _entity_packet(snapshot)
    web_payload = _payload_for_source(raw_inputs, "web")
    exa_payload = _payload_for_source(raw_inputs, "exa")
    context_payload = _payload_for_source(raw_inputs, "context")
    social_payload = _payload_for_source(raw_inputs, "social")

    input_url = _normalize_url(
        str(
            run.get("url")
            or (entity_packet or {}).get("input_url")
            or _payload_url(web_payload)
            or ""
        )
    )
    brand_name = str(run.get("brand_name") or "").strip()
    resolved = _resolve_entity_resolution(
        input_url=input_url,
        brand_name=brand_name,
        run=run,
        entity_packet=entity_packet,
        web_payload=web_payload,
        exa_payload=exa_payload,
        context_payload=context_payload,
        social_payload=social_payload,
        strategic_packet=strategic_packet,
    )

    source_map = _build_source_map(
        snapshot=snapshot,
        strategic_packet=strategic_packet,
        entity_packet=entity_packet,
    )
    official_urls = _collect_official_urls(source_map, input_url=input_url, entity_packet=entity_packet)
    analyzed_urls = _collect_analyzed_urls(snapshot, source_map=source_map)

    offer_lines = strategic_packet.groups.get("product_offer", [])
    audience_lines = strategic_packet.groups.get("audience", [])
    outcome_lines = strategic_packet.groups.get("outcome", [])
    mission_lines = strategic_packet.groups.get("mission_language", [])
    vision_lines = strategic_packet.groups.get("vision_language", [])
    values_lines = strategic_packet.groups.get("values_language", [])
    personality_lines = strategic_packet.groups.get("personality_tone", [])
    hero_lines = strategic_packet.groups.get("hero_claims", [])
    proof_lines = strategic_packet.groups.get("proof_points", [])
    third_party_lines = strategic_packet.groups.get("third_party_context", [])
    press_like_personality_lines = [line for line in personality_lines if _looks_like_press_or_founder_text(str(line.text or ""))]
    clean_personality_lines = [line for line in personality_lines if line not in press_like_personality_lines]

    company_summary = _first_meaningful_text(
        _primary_web_text(web_payload),
        _lines_text(hero_lines),
        _lines_text(offer_lines),
        _lines_text(mission_lines),
    )
    product_summary = _first_meaningful_text(
        _primary_web_text(web_payload),
        _lines_text(offer_lines),
        _lines_text(hero_lines),
        _lines_text(outcome_lines),
    )
    offer = _first_meaningful_text(
        _primary_web_text(web_payload),
        _lines_text(offer_lines),
        company_summary,
        _lines_text(hero_lines),
    )
    audience = _infer_audience(audience_lines, offer, company_summary)
    outcome = _infer_outcome(outcome_lines, offer, product_summary)
    category = _infer_category(
        offer,
        product_summary,
        company_summary,
        exa_payload,
        context_payload,
        resolved,
    )
    declared_purpose = _first_meaningful_text(_lines_text(mission_lines), _lines_text(hero_lines))
    declared_mission = _first_meaningful_text(_lines_text(mission_lines))
    future_direction = _first_meaningful_text(_lines_text(vision_lines))
    tone_of_voice = _tone_summary(clean_personality_lines, product_summary)
    personality_signals = _unique_texts(
        _attribute_signals(_line_texts(clean_personality_lines) or [product_summary, offer], snapshot)
    )
    visual_or_conceptual_signals = _unique_texts(
        _concept_signals(
            company_summary,
            product_summary,
            offer,
            declared_mission,
            future_direction,
        )
    )
    values_signals = _unique_texts(_filter_values_signals(values_lines))
    attributes_signals = _unique_texts(
        _attribute_signals(
            [company_summary, product_summary, offer, tone_of_voice, declared_mission],
            snapshot,
        )
    )
    proof_points = _build_evidence_list(
        proof_lines,
        kind="proof",
        default_topic="proof_point",
    )
    founder_or_press_context = _build_evidence_list(
        third_party_lines,
        kind="context",
        default_topic="founder_or_press",
    )
    founder_or_press_context.extend(
        _build_evidence_list(
            press_like_personality_lines,
            kind="context",
            default_topic="founder_or_press",
        )
    )
    founder_or_press_context.extend(
        _build_evidence_from_source_map(source_map, allowed_types={"press_or_founder"}, kind="context")
    )
    founder_or_press_context.extend(
        _build_supplemental_context_evidence(snapshot, proof_points + founder_or_press_context)
    )
    proof_points.extend(
        _build_evidence_from_source_map(source_map, allowed_types={"proof_point"}, kind="proof")
    )
    noise_rejected = _build_noise_list(strategic_packet.rejected, web_payload)
    noise_rejected.extend(_build_evidence_from_source_map(source_map, allowed_types={"noise"}, kind="noise"))

    evidence_gaps = _evidence_gaps(
        company_summary=company_summary,
        product_summary=product_summary,
        offer=offer,
        audience=audience,
        outcome=outcome,
        proof_points=proof_points,
        mission=declared_mission,
        official_urls=official_urls,
    )
    confidence_notes = _confidence_notes(
        resolved=resolved,
        source_map=source_map,
        proof_points=proof_points,
        founder_or_press_context=founder_or_press_context,
        web_payload=web_payload,
        entity_packet=entity_packet,
    )

    pack = BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url=input_url,
        resolved_entity=resolved,
        entity_type=resolved.entity_type,
        parent_brand=resolved.parent_brand,
        official_urls=official_urls,
        analyzed_urls=analyzed_urls,
        source_map=source_map,
        company_summary=company_summary,
        product_summary=product_summary,
        audience=audience,
        offer=offer,
        outcome=outcome,
        category=category,
        declared_purpose=declared_purpose,
        declared_mission=declared_mission,
        future_direction=future_direction,
        tone_of_voice=tone_of_voice,
        personality_signals=personality_signals,
        visual_or_conceptual_signals=visual_or_conceptual_signals,
        values_signals=values_signals,
        attributes_signals=attributes_signals,
        proof_points=proof_points,
        founder_or_press_context=founder_or_press_context,
        noise_rejected=noise_rejected,
        evidence_gaps=evidence_gaps,
        confidence_notes=confidence_notes,
    )
    return pack


def _entity_packet(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") == "entity_research_packet" and isinstance(raw_input.get("payload"), dict):
            return raw_input["payload"]
    run = snapshot.get("run") or {}
    audit = run.get("audit") if isinstance(run.get("audit"), dict) else {}
    packet = audit.get("entity_research_packet") if isinstance(audit, dict) else None
    return packet if isinstance(packet, dict) else None


def _payload_for_source(raw_inputs: list[dict[str, Any]], source: str) -> dict[str, Any]:
    for raw_input in reversed(raw_inputs):
        if raw_input.get("source") == source and isinstance(raw_input.get("payload"), dict):
            return raw_input["payload"]
    return {}


def _payload_url(payload: dict[str, Any]) -> str:
    if not payload:
        return ""
    for key in ("canonical_url", "url", "page_url", "input_url"):
        value = str(payload.get(key) or "").strip()
        if value:
            return _normalize_url(value)
    return ""


def _normalize_url(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).lower()
    path = parsed.path if parsed.netloc else ""
    return f"{parsed.scheme or 'https'}://{host}{path}".rstrip("/")


def _extract_host(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _subdomain(host: str, root: str) -> str:
    if not host or not root or host == root:
        return ""
    suffix = f".{root}"
    if not host.endswith(suffix):
        return ""
    return host[: -len(suffix)].split(".")[-1]


def _parent_name_from_root(root: str) -> str:
    if not root:
        return ""
    label = root.split(".")[0]
    return label.replace("-", " ").title()


def _site_role_from_url(url: str) -> str:
    parsed = urlparse(_normalize_url(url))
    path = (parsed.path or "/").lower().rstrip("/") or "/"
    if path == "/":
        return "owned_official"
    if any(marker in path for marker in ("/about", "/mission", "/manifesto", "/team", "/company", "/story", "/principles")):
        return "owned_about"
    if any(marker in path for marker in ("/privacy", "/security", "/trust", "/legal", "/terms", "/compliance")):
        return "owned_security_trust"
    if any(marker in path for marker in ("/product", "/products", "/platform", "/solution", "/solutions", "/app", "/pricing", "/plans", "/demo", "/beta", "/lab", "/natureos")):
        return "owned_product"
    if any(marker in path for marker in ("/blog", "/news", "/press", "/article", "/post", "/feed", "/resources")):
        return "noise"
    if any(marker in path for marker in ("/customers", "/clients", "/case", "/stories", "/reviews", "/testimonials", "/casos", "/opiniones")):
        return "proof_point"
    return "owned_official"


def _source_type_from_url(url: str, *, brand_domain: str, text: str = "", source: str = "") -> str:
    normalized = _normalize_url(url)
    host = _extract_host(normalized)
    text_low = (text or "").lower()
    path = (urlparse(normalized).path or "").lower()
    if source == "social" or host.endswith(("linkedin.com", "x.com", "twitter.com", "instagram.com", "youtube.com", "tiktok.com", "facebook.com", "github.com")):
        return "social"
    if brand_domain and (host == brand_domain or host.endswith("." + brand_domain)):
        role = _site_role_from_url(normalized)
        if role == "owned_official":
            return "owned_official"
        return role
    if any(marker in text_low for marker in ("founder", "founders", "interview", "press", "announc", "launch", "raises", "raised", "acquired", "acquisition")):
        return "press_or_founder"
    if any(marker in text_low for marker in ("testimonial", "testimonials", "customer", "customers", "client", "clients", "trusted by", "used by", "case study", "case studies", "review", "reviews", "proof")):
        return "proof_point"
    if any(marker in path for marker in ("/customers", "/client", "/case", "/stories", "/reviews", "/testimonials")):
        return "proof_point"
    if any(marker in path for marker in ("/blog", "/news", "/press", "/article", "/post", "/feed", "/resources")):
        return "noise"
    return "noise"


def _classify_entity_type(
    *,
    input_url: str,
    brand_name: str,
    entity_packet: dict[str, Any] | None,
    web_payload: dict[str, Any],
) -> str:
    if entity_packet:
        architecture = str(entity_packet.get("brand_architecture") or "")
        audited_type = str(entity_packet.get("audited_surface_type") or "")
        if architecture == "single_brand_surface":
            return "company"
        if audited_type in {"product_surface", "product_lab"}:
            return "product"
        if audited_type == "secondary_surface":
            return "sub_brand"
        if str(entity_packet.get("parent_brand") or ""):
            return "product"

    host = _extract_host(input_url)
    root = _root_domain(host)
    subdomain = _subdomain(host, root)
    path = (urlparse(input_url).path or "").lower()
    if any(marker in path for marker in ("/blog", "/news", "/press", "/article", "/post", "/resources")):
        return "content"
    if any(marker in path for marker in ("/campaign", "/promo", "/launch", "/event", "/sale")):
        return "campaign"
    if subdomain and subdomain not in {"www", "m"}:
        return "product"
    if root and (brand_name or root):
        return "company"
    return "unknown"


def _resolve_entity_resolution(
    *,
    input_url: str,
    brand_name: str,
    run: dict[str, Any],
    entity_packet: dict[str, Any] | None,
    web_payload: dict[str, Any],
    exa_payload: dict[str, Any],
    context_payload: dict[str, Any],
    social_payload: dict[str, Any],
    strategic_packet,
) -> EntityResolution:
    host = _extract_host(input_url)
    root = _root_domain(host)
    subdomain = _subdomain(host, root)
    parent_brand = ""
    notes: list[str] = []
    if entity_packet:
        parent_brand = str(entity_packet.get("parent_brand") or "").strip()
        if parent_brand:
            notes.append("Parent brand reused from entity research packet.")
        if entity_packet.get("limitations"):
            notes.extend(str(item) for item in entity_packet.get("limitations") if str(item).strip())
    if not parent_brand and root and subdomain and subdomain not in {"www", "m"}:
        parent_brand = _parent_name_from_root(root)
        notes.append("Parent brand inferred from subdomain/root domain relationship.")

    resolved_name = (
        str((entity_packet or {}).get("entity_name") or "").strip()
        or str((entity_packet or {}).get("product_name") or "").strip()
        or str((entity_packet or {}).get("canonical_brand_name") or "").strip()
        or str(run.get("brand_name") or "").strip()
        or _parent_name_from_root(root)
        or input_url
    )
    entity_type = _classify_entity_type(
        input_url=input_url,
        brand_name=brand_name,
        entity_packet=entity_packet,
        web_payload=web_payload,
    )

    surface_role = "audited_surface"
    entity_scope = "audited_surface"
    if parent_brand and entity_type in {"product", "sub_brand"}:
        entity_scope = "product_surface"
        surface_role = "product_surface"
    if entity_type == "content":
        entity_scope = "content_surface"
        surface_role = "content_surface"
    if entity_type == "campaign":
        entity_scope = "campaign_surface"
        surface_role = "campaign_surface"

    confidence = "medium"
    if entity_packet and str(entity_packet.get("confidence") or "").strip():
        confidence = str(entity_packet.get("confidence") or "medium")
    elif parent_brand and entity_type in {"product", "sub_brand"}:
        confidence = "medium"
    elif entity_type == "company":
        confidence = "medium"
    else:
        confidence = "low"

    canonical_url = (
        _payload_url(web_payload)
        or _normalize_url(str(run.get("url") or ""))
        or input_url
    )
    if exa_payload.get("news"):
        notes.append("External news evidence available; keep it in founder_or_press_context, not tone.")
    if context_payload.get("homepage_status"):
        notes.append(f"Context scan status={context_payload.get('homepage_status')}.")
    if social_payload and social_payload.get("profiles_found"):
        notes.append("Social profiles were collected in the audit snapshot.")
    if strategic_packet.warnings:
        notes.extend(str(item) for item in strategic_packet.warnings if str(item).strip())

    return EntityResolution(
        resolved_entity=resolved_name,
        entity_type=entity_type,
        canonical_url=canonical_url,
        parent_brand=parent_brand,
        surface_role=surface_role,
        entity_scope=entity_scope,
        confidence=confidence,
        notes=_unique_texts(notes),
    )


def _build_source_map(
    *,
    snapshot: dict[str, Any],
    strategic_packet,
    entity_packet: dict[str, Any] | None,
) -> dict[str, ResearchSource]:
    run = snapshot.get("run") or {}
    brand_url = _normalize_url(str(run.get("url") or ""))
    brand_domain = _extract_host(brand_url)
    sources: dict[str, ResearchSource] = {}

    def add(
        *,
        url: str,
        source_type: str,
        label: str = "",
        title: str = "",
        surface_role: str = "",
        entity_scope: str = "",
        notes: list[str] | None = None,
    ) -> None:
        normalized = _normalize_url(url)
        if not normalized:
            return
        key = normalized
        if key in sources:
            existing = sources[key]
            merged_notes = _unique_texts(existing.notes + (notes or []))
            sources[key] = ResearchSource(
                url=existing.url,
                source_type=existing.source_type or source_type,
                label=existing.label or label,
                surface_role=existing.surface_role or surface_role,
                entity_scope=existing.entity_scope or entity_scope,
                title=existing.title or title,
                notes=merged_notes,
            )
            return
        sources[key] = ResearchSource(
            url=normalized,
            source_type=source_type,
            label=label,
            surface_role=surface_role,
            entity_scope=entity_scope,
            title=title,
            notes=_unique_texts(notes or []),
        )

    if brand_url:
        add(
            url=brand_url,
            source_type="owned_official",
            label="audited surface",
            title=str(run.get("brand_name") or ""),
            surface_role="audited_surface",
            entity_scope="audited_surface",
            notes=["Run input URL."],
        )

    for raw_input in snapshot.get("raw_inputs") or []:
        source = str(raw_input.get("source") or "")
        payload = raw_input.get("payload") or {}
        if not isinstance(payload, dict):
            continue

        if source == "web":
            for candidate_url in _web_urls(payload, fallback=brand_url):
                source_type = _source_type_from_url(
                    candidate_url,
                    brand_domain=brand_domain,
                    text=str(payload.get("markdown_content") or payload.get("content") or ""),
                    source=source,
                )
                add(
                    url=candidate_url,
                    source_type=source_type,
                    label=str(payload.get("title") or source),
                    title=str(payload.get("title") or ""),
                    surface_role=surface_role_for_url(candidate_url, entity_packet),
                    entity_scope=entity_scope_for_url(candidate_url, entity_packet),
                    notes=["Derived from raw_inputs.web."],
                )
        elif source == "exa":
            for collection_name in ("mentions", "news", "competitors", "ai_visibility_results"):
                for item in payload.get(collection_name) or []:
                    if not isinstance(item, dict):
                        continue
                    candidate_url = str(item.get("url") or "").strip()
                    if not candidate_url:
                        continue
                    text = " ".join(
                        str(part)
                        for part in (
                            item.get("title"),
                            item.get("summary"),
                            item.get("text"),
                            " ".join(item.get("highlights") or []),
                        )
                        if str(part or "").strip()
                    )
                    source_type = _source_type_from_url(
                        candidate_url,
                        brand_domain=brand_domain,
                        text=text,
                        source=source,
                    )
                    add(
                        url=candidate_url,
                        source_type=source_type,
                        label=str(item.get("title") or collection_name),
                        title=str(item.get("title") or ""),
                        surface_role="external_context" if source_type in {"press_or_founder", "proof_point"} else "noise",
                        entity_scope="external_context" if source_type in {"press_or_founder", "proof_point"} else "noise",
                        notes=[f"Derived from raw_inputs.exa.{collection_name}."],
                    )
        elif source == "social":
            for candidate_url in _social_urls(payload):
                add(
                    url=candidate_url,
                    source_type="social",
                    label=str(payload.get("brand_name") or "social"),
                    title=str(payload.get("brand_name") or ""),
                    surface_role="social",
                    entity_scope="external_context",
                    notes=["Derived from raw_inputs.social."],
                )
        elif source == "competitor":
            for candidate_url in _competitor_urls(payload):
                add(
                    url=candidate_url,
                    source_type="noise",
                    label=str(payload.get("brand_name") or "competitor"),
                    title=str(payload.get("brand_name") or ""),
                    surface_role="external_context",
                    entity_scope="external_context",
                    notes=["Competitor context only."],
                )
        elif source == "context":
            candidate_url = _payload_url(payload) or brand_url
            if candidate_url:
                add(
                    url=candidate_url,
                    source_type=_source_type_from_url(candidate_url, brand_domain=brand_domain, source=source),
                    label="context scan",
                    title=str(run.get("brand_name") or ""),
                    surface_role="audited_surface",
                    entity_scope="audited_surface",
                    notes=["Derived from raw_inputs.context."],
                )

    for item in collect_evidences(snapshot):
        candidate_url = _normalize_url(str(item.url or ""))
        if not candidate_url:
            continue
        source_type = _source_type_from_url(
            candidate_url,
            brand_domain=brand_domain,
            text=str(item.quote or ""),
            source=str(item.source_type or ""),
        )
        add(
            url=candidate_url,
            source_type=source_type,
            label=str(item.feature_name or "evidence"),
            title=str(item.extra.get("title") or ""),
            surface_role="evidence",
            entity_scope="evidence",
            notes=[f"Derived from feature/evidence item ({item.dimension})."],
        )

    if entity_packet:
        for surface in entity_packet.get("owned_surfaces") or []:
            if not isinstance(surface, dict):
                continue
            candidate_url = str(surface.get("url") or "").strip()
            if not candidate_url:
                continue
            role = str(surface.get("role") or "")
            source_type = {
                "audited_surface": "owned_official",
                "parent_home": "owned_official",
                "mission_about": "owned_about",
                "product_system": "owned_product",
                "policy_security": "owned_security_trust",
                "proof_customer": "proof_point",
            }.get(role, _site_role_from_url(candidate_url))
            add(
                url=candidate_url,
                source_type=source_type,
                label=role or "owned surface",
                title="",
                surface_role=role or surface_role_for_url(candidate_url, entity_packet),
                entity_scope=str(surface.get("entity_scope") or entity_scope_for_url(candidate_url, entity_packet) or ""),
                notes=[str(surface.get("reason") or "Owned surface from entity research packet.")],
            )

    return dict(sorted(sources.items(), key=lambda item: item[0]))


def _build_evidence_list(
    lines: list[StrategicEvidenceLine],
    *,
    kind: str,
    default_topic: str,
) -> list[ResearchEvidence]:
    evidences: list[ResearchEvidence] = []
    seen: set[tuple[str, str, str]] = set()
    for line in lines:
        source_url = _normalize_url(str(line.url or ""))
        text = str(line.text or "").strip()
        if not text and not source_url:
            continue
        source_type = _evidence_source_type(line, text=text, url=source_url)
        key = (text.lower(), source_url, source_type)
        if key in seen:
            continue
        seen.add(key)
        evidences.append(
            ResearchEvidence(
                text=text,
                kind=kind,
                source_url=source_url,
                source_type=source_type,
                source_label=str(line.feature_name or default_topic or ""),
                surface_role=str(line.surface_role or ""),
                entity_scope=str(line.entity_scope or ""),
                topic=str(line.dimension or default_topic or ""),
                confidence="high" if source_url else "medium",
            )
        )
    return evidences


def _build_supplemental_context_evidence(
    snapshot: dict[str, Any],
    existing: list[ResearchEvidence],
) -> list[ResearchEvidence]:
    seen = {(item.text.lower(), item.source_url, item.source_type) for item in existing}
    items: list[ResearchEvidence] = []
    for evidence in collect_evidences(snapshot):
        if not evidence.url:
            continue
        source_type = _source_type_from_url(
            evidence.url,
            brand_domain=_extract_host(str((snapshot.get("run") or {}).get("url") or "")),
            text=str(evidence.quote or ""),
            source=str(evidence.source_type or ""),
        )
        kind = "proof" if source_type == "proof_point" else "context" if source_type == "press_or_founder" else "noise"
        text = str(evidence.quote or evidence.url or "").strip()
        key = (text.lower(), _normalize_url(str(evidence.url or "")), source_type)
        if key in seen or not text:
            continue
        seen.add(key)
        items.append(
            ResearchEvidence(
                text=text,
                kind=kind,
                source_url=_normalize_url(str(evidence.url or "")),
                source_type=source_type,
                source_label=str(evidence.feature_name or ""),
                surface_role="evidence",
                entity_scope="evidence",
                topic=str(evidence.dimension or ""),
                confidence="medium",
            )
        )
    return items


def _build_noise_list(rejected: list[dict[str, Any]], web_payload: dict[str, Any]) -> list[ResearchEvidence]:
    noise: list[ResearchEvidence] = []
    seen: set[str] = set()
    for item in rejected:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        noise.append(
            ResearchEvidence(
                text=text,
                kind="noise",
                source_url=_payload_url(web_payload),
                source_type="noise",
                source_label="rejected line",
                surface_role="page_chrome" if _looks_like_page_chrome(text) else "noise",
                entity_scope="audited_surface",
                topic=str(item.get("reason") or "noise"),
                confidence="low",
            )
        )
    markdown = str(web_payload.get("markdown_content") or web_payload.get("content") or "")
    source_url = _payload_url(web_payload)
    for raw_line in markdown.splitlines():
        line = _clean_text(raw_line)
        if not line or not _looks_like_page_chrome(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        noise.append(
            ResearchEvidence(
                text=line,
                kind="noise",
                source_url=source_url,
                source_type="noise",
                source_label="web page chrome",
                surface_role="page_chrome",
                entity_scope="audited_surface",
                topic="page chrome",
                confidence="low",
            )
        )
    return noise


def _evidence_source_type(line: StrategicEvidenceLine, *, text: str, url: str) -> str:
    source_type = str(line.source_type or "")
    if source_type in {"owned", "owned_raw"}:
        return _source_type_from_url(url, brand_domain=_extract_host(url), text=text, source=source_type)
    if source_type == "social":
        return "social"
    if source_type in {"news", "review", "encyclopedic", "other", "changelog"}:
        if "press" in (line.surface_role or "") or "founder" in text.lower():
            return "press_or_founder"
        if any(marker in text.lower() for marker in ("testimonial", "customer", "client", "trusted by", "used by", "case study", "review")):
            return "proof_point"
        return "noise" if source_type == "other" else "press_or_founder"
    return _source_type_from_url(url, brand_domain=_extract_host(url), text=text, source=source_type)


def _collect_official_urls(
    source_map: dict[str, ResearchSource],
    *,
    input_url: str,
    entity_packet: dict[str, Any] | None,
) -> list[str]:
    urls = []
    for source in source_map.values():
        if source.source_type in {"owned_official", "owned_product", "owned_about", "owned_security_trust"}:
            urls.append(source.url)
    if entity_packet:
        for surface in entity_packet.get("owned_surfaces") or []:
            if not isinstance(surface, dict):
                continue
            url = str(surface.get("url") or "").strip()
            role = str(surface.get("role") or "")
            if url and role in {"audited_surface", "parent_home", "mission_about", "product_system", "policy_security"}:
                urls.append(_normalize_url(url))
    if input_url:
        urls.append(_normalize_url(input_url))
    return _unique_texts(urls)


def _collect_analyzed_urls(snapshot: dict[str, Any], *, source_map: dict[str, ResearchSource] | None = None) -> list[str]:
    urls: list[str] = []
    if source_map:
        urls.extend(source.url for source in source_map.values())
    for evidence in collect_evidences(snapshot):
        if evidence.url:
            urls.append(_normalize_url(str(evidence.url)))
    return _unique_texts(urls)


def _web_urls(payload: dict[str, Any], *, fallback: str = "") -> list[str]:
    urls = []
    for key in ("canonical_url", "url", "page_url", "input_url"):
        value = str(payload.get(key) or "").strip()
        if value:
            urls.append(_normalize_url(value))
    for value in payload.get("owned_fallback_urls") or []:
        if isinstance(value, str) and value.strip():
            urls.append(_normalize_url(value))
    if not urls and fallback:
        urls.append(_normalize_url(fallback))
    return _unique_texts(urls)


def _social_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for value in payload.get("profiles_found") or []:
        if isinstance(value, str) and value.strip():
            urls.append(_normalize_url(value))
    return _unique_texts(urls)


def _competitor_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in payload.get("competitors") or []:
        if isinstance(item, dict):
            value = str(item.get("url") or "").strip()
            if value:
                urls.append(_normalize_url(value))
    return _unique_texts(urls)


def _first_meaningful_text(*candidates: str) -> str:
    for candidate in candidates:
        text = _clean_text(candidate)
        if text:
            return text
    return ""


def _summarize_texts(lines: list[StrategicEvidenceLine]) -> str:
    texts = _line_texts(lines)
    if not texts:
        return ""
    if len(texts) == 1:
        return texts[0]
    return "; ".join(texts[:2])


def _lines_text(lines: list[StrategicEvidenceLine]) -> str:
    return _clean_text(" ".join(_line_texts(lines)))


def _line_texts(lines: list[StrategicEvidenceLine]) -> list[str]:
    return [_clean_text(str(line.text or "")) for line in lines if str(line.text or "").strip()]


def _tone_summary(lines: list[StrategicEvidenceLine], fallback: str) -> str:
    texts = _line_texts(lines)
    if texts:
        signals = _attribute_signals(texts, {})
        if signals:
            return ", ".join(_unique_texts(signals[:3]))
        return ", ".join(_unique_texts(texts[:1]))
    fallback_terms = _attribute_signals([fallback], {})
    return ", ".join(_unique_texts(fallback_terms[:3]))


def _infer_audience(lines: list[StrategicEvidenceLine], offer: str, summary: str) -> str:
    texts = _line_texts(lines)
    text = " ".join(texts + [offer, summary]).lower()
    phrases: list[str] = []
    for marker in (
        "non-technical founders",
        "founders",
        "teams",
        "developers",
        "businesses",
        "creators",
        "customers",
        "clients",
        "operators",
        "startups",
        "enterprises",
        "students",
        "makers",
    ):
        if marker in text:
            phrases.append(marker)
    if phrases:
        return "; ".join(_unique_texts(phrases))
    if texts:
        return texts[0]
    return ""


def _infer_outcome(lines: list[StrategicEvidenceLine], offer: str, summary: str) -> str:
    texts = _line_texts(lines)
    text = " ".join(texts + [offer, summary]).lower()
    phrases: list[str] = []
    for marker in (
        "build and ship",
        "ship software",
        "ship apps",
        "make app creation simple",
        "life orchestration",
        "help teams",
        "save time",
        "simplify",
        "streamline",
        "secure",
        "transparent",
        "instant",
    ):
        if marker in text:
            phrases.append(marker)
    if phrases:
        return "; ".join(_unique_texts(phrases))
    if texts:
        return texts[0]
    return ""


def _concept_signals(*texts: str) -> list[str]:
    candidates = []
    for text in texts:
        low = text.lower()
        for term in ("lab", "command center", "nature", "builder", "platform", "assistant", "studio", "system", "playbook", "engine", "operating system"):
            if term in low:
                candidates.append(term)
    return candidates


def _attribute_signals(texts: list[str], snapshot: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for text in texts:
        low = text.lower()
        for term in ("clear", "practical", "direct", "simple", "fast", "secure", "transparent", "private", "technical", "minimal", "dense", "human", "playful", "premium", "focused", "structured", "organized"):
            if term in low:
                candidates.append(term)
    for feat in snapshot.get("features") or []:
        raw_value = feat.get("raw_value")
        if isinstance(raw_value, str):
            low = raw_value.lower()
            for term in ("clear", "practical", "direct", "simple", "fast", "secure", "transparent", "private", "technical", "minimal", "dense", "human", "playful", "premium", "focused", "structured", "organized"):
                if term in low:
                    candidates.append(term)
    return candidates


def _infer_category(
    offer: str,
    product_summary: str,
    company_summary: str,
    exa_payload: dict[str, Any],
    context_payload: dict[str, Any],
    resolved: EntityResolution,
) -> str:
    text = " ".join(part for part in (offer, product_summary, company_summary, resolved.resolved_entity) if part).lower()
    if "ai app builder" in text or "app builder" in text:
        return "AI app builder"
    if "ai assistant" in text or "assistant" in text:
        return "AI assistant"
    if "crypto" in text or "wallet" in text:
        return "crypto product"
    if "platform" in text:
        return "platform"
    if "software" in text:
        return "software"
    if context_payload.get("schema_types"):
        return ", ".join(_unique_texts(str(item) for item in context_payload.get("schema_types") or [])[:3])
    if exa_payload.get("competitors"):
        return "market category"
    return "unknown"


def _confidence_notes(
    *,
    resolved: EntityResolution,
    source_map: dict[str, ResearchSource],
    proof_points: list[ResearchEvidence],
    founder_or_press_context: list[ResearchEvidence],
    web_payload: dict[str, Any],
    entity_packet: dict[str, Any] | None,
) -> list[str]:
    notes = list(resolved.notes)
    if resolved.parent_brand:
        notes.append(f"Parent brand detected: {resolved.parent_brand}.")
    if resolved.entity_type in {"product", "sub_brand"} and resolved.surface_role == "product_surface":
        notes.append("Treat the input as a product surface, not as the whole company brand.")
    if not proof_points:
        notes.append("No direct proof-point evidence surfaced in the snapshot.")
    if not founder_or_press_context:
        notes.append("No founder or press context surfaced in the snapshot.")
    if web_payload and not _primary_web_text(web_payload):
        notes.append("Web payload did not provide a clean primary page text block.")
    owned_count = sum(1 for source in source_map.values() if source.source_type.startswith("owned"))
    if owned_count:
        notes.append(f"{owned_count} owned source(s) were retained in the pack.")
    if entity_packet and entity_packet.get("limitations"):
        notes.extend(str(item) for item in entity_packet.get("limitations") if str(item).strip())
    return _unique_texts(notes)


def _evidence_gaps(
    *,
    company_summary: str,
    product_summary: str,
    offer: str,
    audience: str,
    outcome: str,
    proof_points: list[ResearchEvidence],
    mission: str,
    official_urls: list[str],
) -> list[str]:
    gaps = []
    if not offer:
        gaps.append("No clear offer sentence was extracted.")
    if not audience:
        gaps.append("Audience remains thin or absent.")
    if not outcome:
        gaps.append("Outcome language remains thin or absent.")
    if not mission:
        gaps.append("Mission/purpose language remains thin or absent.")
    if not proof_points:
        gaps.append("No proof-point evidence was retained.")
    if not company_summary and not product_summary:
        gaps.append("No usable homepage or summary sentence was extracted.")
    if len(official_urls) <= 1:
        gaps.append("Only one official URL was retained; parent context may still be incomplete.")
    return gaps


def _primary_web_text(payload: dict[str, Any]) -> str:
    markdown = str(payload.get("markdown_content") or payload.get("content") or "").strip()
    if not markdown:
        return ""
    primary = markdown.split("\n---\n", 1)[0]
    lines = [_clean_text(line) for line in primary.splitlines()]
    for index, line in enumerate(lines):
        if not line or _looks_like_page_chrome(line):
            continue
        if len(line) >= 24 or any(mark in line for mark in (".", ",", ":", "?", "!", " is ", " are ")):
            return _clean_text(" ".join(lines[index:]))
    return _clean_text(primary)


def _looks_like_page_chrome(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in ("navigation", "menu", "footer", "header", "feed", "article prediction", "page chrome", "breadcrumbs", "sign in", "log in", "top of page"))


def _looks_like_press_or_founder_text(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in (
            "founder",
            "founders",
            "press",
            "interview",
            "announc",
            "launch",
            "raised",
            "raises",
            "exit",
            "acquisition",
            "acquired",
        )
    )


def _filter_values_signals(lines: list[StrategicEvidenceLine]) -> list[str]:
    texts: list[str] = []
    for line in lines:
        text = _clean_text(str(line.text or ""))
        low = text.lower()
        if not text:
            continue
        if _looks_like_press_or_founder_text(text):
            continue
        if any(marker in low for marker in ("trusted by", "customers", "clients", "proof", "case study", "testimonial")):
            continue
        texts.append(text)
    return texts


def _clean_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    text = text.strip(" -|•*")
    return text


def _unique_texts(values: list[str] | tuple[str, ...] | Any) -> list[str]:
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _clean_text(str(value or ""))
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _build_evidence_from_source_map(
    source_map: dict[str, ResearchSource],
    *,
    allowed_types: set[str],
    kind: str,
) -> list[ResearchEvidence]:
    items: list[ResearchEvidence] = []
    seen: set[tuple[str, str, str]] = set()
    for source in source_map.values():
        if source.source_type not in allowed_types:
            continue
        text = source.title or source.label or source.url
        source_url = source.url
        key = (text.lower(), source_url, source.source_type)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            ResearchEvidence(
                text=text,
                kind=kind,
                source_url=source_url,
                source_type=source.source_type,
                source_label=source.label,
                surface_role=source.surface_role,
                entity_scope=source.entity_scope,
                topic=kind,
                confidence="medium",
            )
        )
    return items
