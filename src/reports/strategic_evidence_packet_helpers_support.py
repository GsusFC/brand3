"""Heuristics and candidate-building helpers for strategic evidence packets."""

from __future__ import annotations

import re
from typing import Any

from src.reports.evidence_noise import looks_like_article_or_product_card_feed
from src.reports.entity_research_packet import entity_scope_for_url, surface_role_for_url
from src.reports.vertical_signals import vertical_group_keywords
from src.reports.strategic_evidence_packet_helpers_noise_support import (
    _clean_quote,
    _looks_like_bare_page_label,
    _looks_like_customer_story_fragment,
    _looks_like_directory_profile_noise,
    _looks_like_ecommerce_grid_noise,
    _looks_like_image_or_logo_noise,
    _looks_like_legal_or_footer_noise,
    _looks_like_promotion_or_event,
    _looks_like_short_label,
    _looks_like_testimonial_quote,
    _looks_like_title_or_directory,
    _looks_truncated,
    _reject_reason,
)
from src.reports.strategic_evidence_packet_sources_support import (
    _add_owned_raw_page_candidates,
    _add_owned_raw_web_candidates,
    _candidate_dedupe_key,
    _embedded_web_subpage_texts,
    _is_proof_page_url,
    _groups_for,
    _looks_like_about_mission_or_values_line,
    _primary_web_page_text,
    _raw_candidate_lines,
)


GROUP_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hero_claims": (
        "introducing",
        "meet ",
        "built for",
        "designed for",
        "purpose-built",
        "just do it",
        "earn every",
        "system for",
        "platform for",
    ),
    "product_offer": (
        "platform",
        "plataforma",
        "infrastructure",
        "infraestructura",
        "api",
        "payments",
        "pagos",
        "billing",
        "facturacion",
        "facturación",
        "services",
        "servicios",
        "products",
        "productos",
        "software",
        "model",
        "ai assistant",
        "chatbot",
        "banking",
        "wealth management",
        "private banking",
        "business analyst",
        "human intelligence",
        "research people",
        "research people and companies",
        "brand identities",
        "ai-powered search",
        "product discovery",
        "merchandising",
        "conversions",
        "shopper intent",
        "ecommerce",
        "e-commerce",
        "branding solution",
        "brand execution",
        "brand and website",
        "deliverables",
        "calendar app",
        "productivity tools",
        "extendable launcher",
        "application launcher",
        "observability service",
        "monitoring",
        "portfolio platform",
        "jobs and recruiting site",
    )
    + vertical_group_keywords("product_offer"),
    "audience": (
        "teams",
        "agents",
        "developers",
        "businesses",
        "founders",
        "startups",
        "finance teams",
        "sales teams",
        "wealth managers",
        "creators",
        "customers",
        "clients",
        "shopper",
        "shoppers",
        "manufacturer",
        "manufacturers",
        "people and companies",
        "enterprise",
        "fortune 100",
        "asesores",
        "empresas",
        "clientes",
        "fabricante",
        "fabricantes",
        "distribuidor",
        "distribuidores",
        "atletas",
        "athletes",
    ),
    "outcome": (
        "helps",
        "help ",
        "eliminate risks",
        "secure your competitive advantage",
        "grow",
        "increase",
        "reduce",
        "automate",
        "productive",
        "productivity",
        "efficient",
        "efficiency",
        "drive success",
        "build relationships",
        "get things done",
        "make people talk",
        "solve problems",
        "learn faster",
        "faster",
        "deploy instantly",
        "build and ship",
        "develop and ship",
        "ship digital products",
        "scale",
        "improve product discovery",
        "increasing conversions",
        "boosts conversions",
        "reduce no-result searches",
        "streamline",
        "centralise",
        "centralize",
        "gestionar",
        "hacer crecer",
        "automatizar",
        "reducir costes",
        "reduce costes",
        "facilitar",
        "optimiza",
        "asegura",
        "empowering",
        "impulsando",
    )
    + vertical_group_keywords("outcome"),
    "mission_language": (
        "we build",
        "we create",
        "we provide",
        "we help",
        "we make",
        "we enable",
        "we develop",
        "we empower",
        "our mission",
        "on a mission to",
        "make developers",
        "make teams",
        "help companies",
        "ayuda a",
        "ofrece",
        "creamos",
        "proporcionamos",
    ),
    "vision_language": (
        "future of",
        "built for the future",
        "new model",
        "new paradigm",
        "transform the future",
        "transforming the future",
        "shape the future",
        "creative entity",
        "creative work",
        "wield power",
        "world stage",
        "futuro de",
        "nuevo modelo",
        "nueva generación",
        "transformar la categoría",
        "transformar el futuro",
    ),
    "values_language": (
        "trusted",
        "trust",
        "secure",
        "security",
        "privacy",
        "transparent",
        "sustainable",
        "regenerative",
        "confianza",
        "seguro",
        "seguridad",
        "sostenible",
    )
    + vertical_group_keywords("values_language"),
    "personality_tone": (
        "bold",
        "fast",
        "simple",
        "powerful",
        "precise",
        "creative",
        "ambition",
        "culture",
        "inspire",
        "inspirar",
        "innovative",
        "innovadores",
    ),
    "proof_points": (
        "customers",
        "customer",
        "clients",
        "client",
        "clientes",
        "cliente",
        "trusted by",
        "con la confianza",
        "case study",
        "case studies",
        "customer story",
        "success story",
        "caso de éxito",
        "casos de éxito",
        "testimonial",
        "testimonials",
        "testimonio",
        "testimonios",
        "reviews",
        "review",
        "reseñas",
        "resenas",
        "opiniones",
        "millions",
        "global",
        "leader",
        "used by",
        "raises",
        "funding",
    ),
    "third_party_context": (
        "raises",
        "funding",
        "report",
        "market",
        "competitor",
        "news",
    ),
}

OWNED_SOURCE_TYPES = {"owned", "social", "owned_raw"}
CONTEXT_SOURCE_TYPES = {"encyclopedic", "news", "review", "other", "changelog"}
_EMBEDDED_SUBPAGE_RE = re.compile(r"(?:^|\n)## Subpage:\s*(?P<url>\S+)\s*\n", re.IGNORECASE)


NOISE_MARKERS = (
    "; evidence=",
    "source_type=",
    "dimension=",
    "feature=",
    "__next_data__",
    "graphql api",
    "product roadmap",
    "rg --files",
    "/bin/bash",
)


def _rejected_reason_counts(rejected: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in rejected:
        reason = str(item.get("reason") or "unknown")
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _entity_research_packet(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") == "entity_research_packet" and isinstance(item.get("payload"), dict):
            return item["payload"]
    audit = ((snapshot.get("run") or {}).get("audit") or {})
    packet = audit.get("entity_research_packet") if isinstance(audit, dict) else None
    return packet if isinstance(packet, dict) else None


def _rank_packet_groups(packet: Any) -> None:
    for group, lines in list(packet.groups.items()):
        packet.groups[group] = sorted(lines, key=lambda line: _line_priority(line, group))


def _line_priority(line: Any, group: str) -> tuple[int, int, int, int, int, int]:
    low = line.text.lower()
    source_rank = {"owned_raw": 0, "owned": 1, "social": 2}.get(line.source_type, 3)
    feature_rank = 2 if line.feature_name == "search_visibility" else 0
    context_rank = 1 if group == "third_party_context" else 0
    noise_rank = 0
    if _looks_like_promotion_or_event(low):
        noise_rank += 3
    if _looks_like_short_label(low):
        noise_rank += 3
    if _looks_like_title_or_directory(low):
        noise_rank += 2
    proof_page_rank = 0
    if group == "proof_points":
        proof_page_rank = 0 if _is_proof_page_url(line.url) else 1
    useful_length = min(len(line.text), 260)
    return (source_rank, proof_page_rank, noise_rank, feature_rank, context_rank, -useful_length)


def _add_candidate_line(
    packet: Any,
    seen: set[tuple[str, str, str]],
    *,
    text: str,
    source_type: str,
    source_domain: str | None = None,
    url: str | None = None,
    feature_name: str | None = None,
    dimension: str | None = None,
    entity_research_packet: dict[str, Any] | None = None,
) -> None:
    cleaned = _clean_quote(text)
    reject_reason = _reject_reason(cleaned)
    if reject_reason:
        packet.rejected.append({"text": cleaned[:220], "reason": reject_reason})
        return
    groups = _groups_for(cleaned, source_type, url=url)
    if not groups:
        packet.rejected.append({"text": cleaned[:220], "reason": "low_strategic_signal"})
        return
    line = _make_line(
        cleaned,
        source_type=source_type,
        source_domain=source_domain,
        url=url,
        feature_name=feature_name,
        dimension=dimension,
        entity_research_packet=entity_research_packet,
    )
    for group in groups:
        key = _candidate_dedupe_key(cleaned, url=url, group=group)
        if key in seen:
            packet.rejected.append({"text": cleaned[:220], "reason": "duplicate"})
            continue
        seen.add(key)
        if len(packet.groups.setdefault(group, [])) < 8:
            packet.groups[group].append(line)


def _make_line(
    text: str,
    *,
    source_type: str,
    source_domain: str | None = None,
    url: str | None = None,
    feature_name: str | None = None,
    dimension: str | None = None,
    entity_research_packet: dict[str, Any] | None = None,
) -> Any:
    from src.reports.strategic_evidence_packet import StrategicEvidenceLine

    return StrategicEvidenceLine(
        text=text,
        source_type=source_type,
        source_domain=source_domain,
        url=url,
        feature_name=feature_name,
        dimension=dimension,
        surface_role=surface_role_for_url(url or "", entity_research_packet),
        entity_scope=entity_scope_for_url(url or "", entity_research_packet),
    )
