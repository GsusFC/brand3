"""Entity resolution and source-map helpers for Brand Research Pack."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from src.reports.derivation import collect_evidences
from src.reports.brand_research_pack_sources_support import (
    _clean_text,
    _confidence_notes,
    _evidence_gaps,
    _entity_packet,
    _payload_for_source,
    _payload_url,
    _normalize_url,
    _extract_host,
    _root_domain,
    _subdomain,
    _parent_name_from_root,
    _looks_like_page_chrome,
    _looks_like_press_or_founder_text,
    _primary_web_text,
    _site_role_from_url,
    _source_type_from_url,
    _classify_entity_type,
    _web_urls,
    _social_urls,
    _competitor_urls,
    _str_list,
    _unique_texts,
    _validate_entity_type,
)
from src.reports.entity_research_packet import entity_scope_for_url, surface_role_for_url


ALLOWED_ENTITY_TYPES = {
    "company",
    "brand",
    "product",
    "sub_brand",
    "campaign",
    "content",
    "unknown",
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
    def from_dict(cls, data: dict[str, Any]) -> "ResearchSource":
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
    def from_dict(cls, data: dict[str, Any]) -> "EntityResolution":
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
