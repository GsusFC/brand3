"""Source normalization and classification helpers for EvidenceGraph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.reports.entity_research_packet import entity_scope_for_url, surface_role_for_url
from src.research.evidence_graph_sources_support import (
    ALLOWED_SOURCE_TYPES,
    _classify_source_url,
    _competitor_urls,
    _dict,
    _external_entity_boundary_collision,
    _host,
    _is_social,
    _normalize_url,
    _prefer_annotation,
    _prefer_source_type,
    _root_domain,
    _source_id,
    _source_type_from_entity_role,
    _social_urls,
    _str_list,
    _unique,
    _validate,
    _web_urls,
)


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
    notes: list[str] | None = None

    def __post_init__(self) -> None:
        _validate(self.source_type, ALLOWED_SOURCE_TYPES, "source_type")
        if self.notes is None:
            self.notes = []

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
            "notes": list(self.notes or []),
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


def build_sources(snapshot: dict[str, Any], *, entity_packet: dict[str, Any] | None) -> dict[str, ResearchSource]:
    run = _dict(snapshot.get("run"))
    input_url = _normalize_url(str(run.get("url") or ""))
    brand_name = str((entity_packet or {}).get("entity_name") or run.get("brand_name") or "")
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
            merged_notes = list(existing.notes or [])
            if origin and origin != existing.origin:
                merged_notes.append(f"Also observed via {origin}.")
            sources[source_id] = ResearchSource(
                source_id=source_id,
                url=existing.url,
                source_type=_prefer_source_type(existing.source_type, source_type),
                label=existing.label or label,
                surface_role=_prefer_annotation(existing.surface_role, surface_role),
                entity_scope=_prefer_annotation(existing.entity_scope, entity_scope),
                title=existing.title or title,
                origin=existing.origin or origin,
                notes=_unique(merged_notes + (notes or [])),
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
        if source in {"web", "hyperbrowser"}:
            text = str(payload.get("markdown_content") or payload.get("content") or "")
            for url in _web_urls(payload, fallback=input_url) or [str(payload.get("source_url") or payload.get("url") or input_url)]:
                add(
                    url,
                    source_type=_classify_source_url(url, brand_domain=brand_domain, text=text),
                    label=str(payload.get("title") or source),
                    title=str(payload.get("title") or ""),
                    origin=f"raw_inputs.{source}",
                    surface_role=surface_role_for_url(url, entity_packet),
                    entity_scope=entity_scope_for_url(url, entity_packet),
                    notes=[
                        "Owned web content collected by Brand Audit."
                        if source == "web"
                        else "Owned web shadow content collected by Hyperbrowser."
                    ],
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
                    notes = ["External discovery evidence collected by Brand Audit."]
                    if collection != "competitors" and _external_entity_boundary_collision(
                        url,
                        text,
                        brand_name=brand_name,
                        brand_domain=brand_domain,
                    ):
                        source_type = "noise"
                        notes.append(
                            "entity_boundary_collision: external evidence appears to reference a near-name entity, not the audited entity."
                        )
                    add(
                        url,
                        source_type=source_type,
                        label=str(item.get("title") or collection),
                        title=str(item.get("title") or ""),
                        origin=f"raw_inputs.exa.{collection}",
                        surface_role="external_context",
                        entity_scope="external_context",
                        notes=notes,
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

    return dict(sorted(sources.items()))
