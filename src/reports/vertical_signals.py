"""Configurable vertical signal vocabulary for evidence interpretation.

This module keeps domain-specific vocabulary out of the core evidence and
Magnetism interpreters. Profiles should only encode observable language
patterns, not strategic conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VerticalSignalProfile:
    key: str
    group_keywords: dict[str, tuple[str, ...]] = field(default_factory=dict)
    layer_keywords: dict[str, tuple[str, ...]] = field(default_factory=dict)
    term_markers: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)
    offer_family_markers: tuple[str, ...] = ()


HOME_RETAIL_PROFILE = VerticalSignalProfile(
    key="home_retail",
    group_keywords={
        "product_offer": (
            "tienda online",
            "muebles",
            "decoración",
            "decoracion",
            "diseños exclusivos",
            "disenos exclusivos",
        ),
        "outcome": (
            "transformar tu hogar",
            "transforma tu hogar",
            "con estilo",
            "funcionales",
            "inspiradores",
        ),
        "values_language": (
            "inspiradores",
            "inspiración",
            "inspiracion",
        ),
    },
    layer_keywords={
        "netspace": (
            "tienda online",
            "muebles",
            "decoración",
            "decoracion",
            "diseños exclusivos",
            "disenos exclusivos",
        ),
        "ambientspace": (
            "decoración",
            "decoracion",
            "funcionales",
            "inspiradores",
        ),
    },
    term_markers={
        "attributes": {
            "design-led": ("diseño", "diseno", "design", "decoración", "decoracion"),
            "functional": ("funcional", "funcionales", "functional"),
            "inspiring": ("inspirador", "inspiradores", "inspirar", "inspírate", "inspirate"),
        },
        "values": {
            "inspiration": (
                "inspirar",
                "inspire",
                "inspiration",
                "inspiración",
                "inspiracion",
                "inspiradores",
                "inspírate",
                "inspirate",
            ),
            "creativity": ("creatividad", "creativity"),
            "beauty": ("belleza", "beauty"),
            "inclusivity": ("inclusión", "inclusion", "diversidad", "diversity"),
        },
    },
    offer_family_markers=(
        "tienda online",
        "muebles",
        "decoración",
        "decoracion",
        "hogar",
        "diseño",
        "diseno",
        "interiorismo",
    ),
)


VERTICAL_SIGNAL_PROFILES: tuple[VerticalSignalProfile, ...] = (HOME_RETAIL_PROFILE,)

OFFER_FAMILY_MARKERS: dict[str, tuple[str, ...]] = {
    HOME_RETAIL_PROFILE.key: HOME_RETAIL_PROFILE.offer_family_markers,
    "financial_workflows": (
        "payments",
        "pagos",
        "billing",
        "facturación",
        "facturacion",
        "financial services",
        "servicios financieros",
        "revenue",
        "ingresos",
        "treasury",
    ),
    "developer_platform": (
        "developer",
        "deploy",
        "cloud",
        "infrastructure",
        "platform for devs",
        "sandboxes",
        "api",
        "sdk",
    ),
    "ai_research": (
        "human intelligence",
        "business analyst",
        "research people",
        "ai agents",
        "custom agents",
    ),
    "bioingredients": (
        "materias primas",
        "ingredientes",
        "biorremediación",
        "biorremediacion",
        "cosmética",
        "cosmetica",
        "nutrición",
        "nutricion",
        "salud animal",
    ),
}

COHERENT_MULTI_OFFER_FAMILIES: frozenset[str] = frozenset({HOME_RETAIL_PROFILE.key})


def vertical_group_keywords(group: str) -> tuple[str, ...]:
    return _collect_profile_values("group_keywords", group)


def vertical_layer_keywords(layer: str) -> tuple[str, ...]:
    return _collect_profile_values("layer_keywords", layer)


def vertical_preferred_terms(key: str) -> tuple[str, ...]:
    terms: list[str] = []
    for profile in VERTICAL_SIGNAL_PROFILES:
        for term in profile.term_markers.get(key, {}):
            if term not in terms:
                terms.append(term)
    return tuple(terms)


def vertical_terms_for_text(text: str, key: str) -> list[str]:
    low = text.lower()
    terms: list[str] = []
    for profile in VERTICAL_SIGNAL_PROFILES:
        if not _profile_anchor_in_text(low, profile):
            continue
        for term, markers in profile.term_markers.get(key, {}).items():
            if term not in terms and any(marker in low for marker in markers):
                terms.append(term)
    return terms


def product_offer_family_for_text(text: str) -> str | None:
    low = text.lower()
    for family, markers in OFFER_FAMILY_MARKERS.items():
        if any(marker in low for marker in markers):
            return family
    return None


def product_offer_family_allows_multiple_lines(family: str) -> bool:
    return family in COHERENT_MULTI_OFFER_FAMILIES


def _collect_profile_values(attribute: str, key: str) -> tuple[str, ...]:
    values: list[str] = []
    for profile in VERTICAL_SIGNAL_PROFILES:
        mapping = getattr(profile, attribute)
        for value in mapping.get(key, ()):
            if value not in values:
                values.append(value)
    return tuple(values)


def _profile_anchor_in_text(low: str, profile: VerticalSignalProfile) -> bool:
    anchors: list[str] = list(profile.offer_family_markers)
    for group in ("product_offer", "outcome"):
        anchors.extend(profile.group_keywords.get(group, ()))
    return any(anchor in low for anchor in anchors)
