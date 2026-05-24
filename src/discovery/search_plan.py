"""Deterministic search planning for entity discovery metadata.

This module is intentionally read-only. It performs no network calls and does
not influence collectors, scoring, calibration, prompts, cache keys, or reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass(frozen=True)
class DiscoverySearchPlan:
    primary_entity: str
    requested_entity: str
    analysis_mode: str
    queries: list[str] = field(default_factory=list)
    owned_urls: list[str] = field(default_factory=list)


def build_discovery_search_plan(entity_discovery, brand_name: str, url: str) -> DiscoverySearchPlan:
    """Build deterministic search metadata from an entity discovery result."""
    analysis_scope = _get(entity_discovery, "analysis_scope")
    entity_type = _get(entity_discovery, "entity_type")
    canonical_brand_name = _get(entity_discovery, "canonical_brand_name") or _fallback_entity(brand_name, url)
    canonical_url = _get(entity_discovery, "canonical_url")
    input_url = _get(entity_discovery, "input_url") or url

    if analysis_scope == "product_with_parent":
        parent = _get(entity_discovery, "parent_brand_name") or canonical_brand_name
        product = _get(entity_discovery, "product_name") or canonical_brand_name
        return DiscoverySearchPlan(
            primary_entity=parent,
            requested_entity=product,
            analysis_mode="product_with_parent",
            queries=[
                f"{parent} {product} brand positioning",
                f"{parent} {product} product updates",
                f"{parent} {product} reviews",
                f"{parent} {product} competitors",
            ],
            owned_urls=_unique_urls(
                [
                    _get(entity_discovery, "parent_url"),
                    canonical_url,
                    input_url,
                ]
            ),
        )

    if analysis_scope == "company_brand" and entity_type == "company":
        brand = canonical_brand_name
        return DiscoverySearchPlan(
            primary_entity=brand,
            requested_entity=brand,
            analysis_mode="company_brand",
            queries=[
                f"{brand} brand positioning",
                f"{brand} latest product updates",
                f"{brand} reviews reputation",
                f"{brand} competitors",
            ],
            owned_urls=_unique_urls([canonical_url, input_url]),
        )

    if analysis_scope == "ecosystem" or entity_type == "protocol":
        brand = canonical_brand_name
        return DiscoverySearchPlan(
            primary_entity=brand,
            requested_entity=brand,
            analysis_mode="ecosystem_or_protocol",
            queries=[
                f"{brand} ecosystem positioning",
                f"{brand} protocol updates",
                f"{brand} developer community",
                f"{brand} competitors alternatives",
            ],
            owned_urls=_unique_urls([canonical_url, input_url]),
        )

    primary_entity = canonical_brand_name or _fallback_entity(brand_name, url)
    return DiscoverySearchPlan(
        primary_entity=primary_entity,
        requested_entity=(brand_name or primary_entity).strip() or primary_entity,
        analysis_mode="url_only",
        queries=[
            f"{primary_entity} brand positioning",
            f"{primary_entity} latest updates",
            f"{primary_entity} reviews reputation",
            f"{primary_entity} competitors",
        ],
        owned_urls=_unique_urls([canonical_url, input_url, url]),
    )


def _get(entity_discovery, field_name: str):
    if isinstance(entity_discovery, dict):
        return entity_discovery.get(field_name)
    return getattr(entity_discovery, field_name, None)


def _fallback_entity(brand_name: str, url: str) -> str:
    name = (brand_name or "").strip()
    if name:
        return name
    parsed = urlparse(url if "://" in (url or "") else f"https://{url or ''}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "Unknown"


def _unique_urls(urls: list[str | None]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in urls:
        normalized = _normalize_url(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _normalize_url(value: str | None) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).lower()
    path = parsed.path if parsed.netloc else ""
    return f"{parsed.scheme or 'https'}://{host}{path}".rstrip("/")
