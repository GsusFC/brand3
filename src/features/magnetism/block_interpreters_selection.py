"""Executable TLDR Brand3 block interpreter specs and candidate selection."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from src.reports.brand_context_brief import brand_context_candidates
from src.features.magnetism.block_interpreters_helpers import (
    _clean_candidate_text,
    _clean_layer_candidate_text,
    _contains_keyword,
    _evidence_list,
    _has_audience_signal,
    _has_future_signal,
    _has_formal_mission_signal,
    _has_operating_activity_signal,
    _has_offer_signal,
    _has_outcome_signal,
    _is_bad_value_prop_candidate,
    _is_feed_or_article_noise,
    _is_market_prediction_noise,
    _is_navigation_noise,
    _is_rhetorical_future_question_noise,
    _is_testimonial_evidence,
    _is_truncated_evidence,
    _is_vague_mission_slogan,
    _is_values_statement_as_mission,
    _looks_like_concatenated_copy,
    _looks_like_portfolio_case_card,
    _looks_like_web_chrome_or_navigation_blob,
    _sentence_like_evidence_segments,
    _sentences,
)


TLDR_BLOCK_INTERPRETER_SPECS = {
    "value_proposition": {
        "block": "value_proposition",
        "task": "Identify the concrete value exchange: offer, audience, and change.",
        "primary_question": "What does the brand offer, to whom, and what changes for that audience?",
        "source_layers": ["netspace", "tactispace", "ambientspace"],
        "strategic_groups": ["product_offer", "audience", "outcome", "hero_claims"],
        "look_for": [
            "offer", "offers", "solution", "solutions", "platform", "product", "service", "services",
            "api", "system", "assistant", "companion", "management", "streamline", "centralise", "centralize", "reconcile",
            "execute", "forecast", "payments", "pagos", "billing", "facturación", "financial services",
            "servicios financieros", "revenue", "ingresos", "product development", "planning and building",
            "teams and agents", "human intelligence", "business analyst", "research people",
            "research people and companies", "soluciones", "materias primas", "ingredientes", "biorremediación",
            "cosmética", "nutrición",
        ],
        "reject": ["main menu", "contacto", "subscribe now", "buy now", "book a demo"],
        "minimum_evidence_rule": "At least one concrete offer or service description.",
        "claim_type_rules": "declared when the offer is directly stated; inferred only when features imply the offer.",
        "mode_rules": "compressed for direct offer evidence; needs_human_review when audience or outcome is unclear.",
        "confidence_rules": "high requires offer plus outcome; medium requires clear offer; low is inferred from sparse features.",
        "human_review_triggers": ["missing_audience", "missing_outcome", "multiple_offers"],
        "output_style": "Concrete functional offer; avoid category slogans.",
    },
    "mission": {
        "block": "mission",
        "task": "Identify the brand's current operating activity.",
        "primary_question": "What does the brand concretely do today?",
        "source_layers": ["tactispace", "netspace", "aetherspace"],
        "strategic_groups": ["mission_language", "product_offer", "hero_claims"],
        "look_for": [
            "we build", "we create", "we provide", "we offer", "we operate", "we deliver",
            "builds", "creates", "provides", "offers", "operates", "delivers", "help", "helps",
            "creamos", "construimos", "ofrecemos", "proporcionamos", "desarrollamos",
        ],
        "reject": [
            "contact us", "book a demo", "subscribe", "buy now", "pricing", "future", "futuro",
            "vision", "visión", "new model", "nuevo modelo",
        ],
        "minimum_evidence_rule": "At least one concrete present-tense operating claim.",
        "claim_type_rules": "declared when copied/compressed from an operating claim; inferred only from clear product/service evidence.",
        "mode_rules": "compressed for direct operating evidence; not_detected for CTAs, slogans, or future language.",
        "confidence_rules": "high requires explicit mission/current activity; medium requires clear operating claim; low is inferred from product evidence only.",
        "human_review_triggers": ["inferred_from_product_only", "mission_vision_mixed"],
        "output_style": "Concrete, present-tense, operational. No aspiration.",
    },
    "vision": {
        "block": "vision",
        "task": "Identify the future state, category shift, or long-term change.",
        "primary_question": "What future, category shift, or change does the brand appear to be building toward?",
        "source_layers": ["tactispace", "aetherspace", "mindspace"],
        "strategic_groups": ["vision_language"],
        "look_for": [
            "future", "future of", "vision", "new model", "new paradigm", "transform", "towards",
            "toward", "redefine", "next generation", "futuro", "visión", "nuevo modelo",
            "nuevo paradigma", "transformar",
        ],
        "reject": ["we build", "we create", "we provide", "creamos", "ofrecemos", "book a demo", "pricing"],
        "minimum_evidence_rule": "At least one future-facing or category-change signal.",
        "claim_type_rules": "declared when the brand states a vision; inferred when Brand3 articulates a future hypothesis from future-facing evidence.",
        "mode_rules": "interpreted_from_discourse for future signals that need articulation; not_detected without future/category-change evidence.",
        "confidence_rules": "high requires explicit vision plus support; medium requires clear future/category-change signal; low is weak future language.",
        "human_review_triggers": ["future_from_current_offer_only", "generic_transform_language", "mission_vision_overlap"],
        "output_style": "Future-oriented but bounded. Avoid grandiose category claims unless explicit.",
    },
}

LOW_TRUST_BLOCK_SOURCE_ROLES = {"blog_feed", "proof_customer", "legal_navigation"}


def get_tldr_block_interpreter_spec(block: str) -> dict[str, Any] | None:
    """Return the executable spec for a migrated TLDR block."""
    spec = TLDR_BLOCK_INTERPRETER_SPECS.get(block)
    return dict(spec) if spec else None


def source_role_for_candidate(item: dict[str, Any]) -> str:
    surface_role = str(item.get("surface_role") or "")
    if surface_role:
        mapped_role = {
            "audited_surface": "homepage",
            "parent_home": "homepage",
            "mission_about": "about",
            "product_system": "product",
            "policy_security": "legal_navigation",
            "blog_feed": "blog_feed",
            "proof_customer": "proof_customer",
        }.get(surface_role)
        if mapped_role:
            return mapped_role
    return source_role_for_url(str(item.get("url") or ""))


def source_role_for_url(url: str) -> str:
    """Classify a source URL by strategic role for TLDR evidence weighting."""
    if not url:
        return "unknown"
    try:
        parsed = urlparse(url)
    except ValueError:
        return "unknown"
    path = (parsed.path or "/").lower().rstrip("/") or "/"
    if path == "/":
        return "homepage"
    if any(marker in path for marker in ("/blog", "/news", "/feed", "/article", "/post", "/resources")):
        return "blog_feed"
    if any(marker in path for marker in ("/customers", "/customer", "/clients", "/client", "/case-stud", "/stories", "/reviews", "/testimonials", "/casos", "/opiniones")):
        return "proof_customer"
    if any(marker in path for marker in ("privacy", "privacidad", "terms", "legal", "aviso-legal", "cookies", "security", "proteccion-de-datos", "protección-de-datos")):
        return "legal_navigation"
    if any(marker in path for marker in ("about", "company", "mission", "manifesto", "principles", "conocenos", "conócenos")):
        return "about"
    if any(marker in path for marker in ("/product", "/products", "/platform", "/solution", "/solutions", "/services", "/features")):
        return "product"
    if "/pricing" in path or "/plans" in path:
        return "pricing"
    if any(marker in path for marker in ("/docs", "/developers", "/api")):
        return "docs"
    return "unknown"


def _source_role_rank(source_role: str) -> int:
    return {
        "homepage": 0,
        "about": 1,
        "product": 1,
        "pricing": 2,
        "docs": 2,
        "layer_evidence": 3,
        "unknown": 4,
        "proof_customer": 6,
        "blog_feed": 7,
        "legal_navigation": 8,
    }.get(source_role, 5)


def _invalid_source_role_for_block(block: str, candidate: dict[str, str]) -> bool:
    if block not in {"value_proposition", "mission", "vision"}:
        return False
    source_role = str(candidate.get("source_role") or "unknown")
    return source_role in LOW_TRUST_BLOCK_SOURCE_ROLES


def block_evidence_candidates(
    block: str,
    spec: dict[str, Any],
    layers: dict[str, Any],
    strategic_packet: dict[str, Any] | None,
    primary_layer_key: str,
    brand_context_brief: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Select block evidence candidates from context brief, strategic packet, or Magenta layers."""
    context_candidates = brand_context_candidates(block, brand_context_brief, primary_layer_key)
    if strategic_packet:
        return context_candidates + strategic_packet_candidates(block, spec, strategic_packet, primary_layer_key)

    candidates: list[dict[str, str]] = context_candidates
    seen: set[str] = set()
    for layer_key in spec["source_layers"]:
        layer = layers.get(layer_key) or {}
        for source in ("evidence", "finding"):
            value = layer.get(source)
            for sentence in _sentences("\n".join(_evidence_list(value))):
                cleaned = _clean_layer_candidate_text(sentence)
                if not cleaned or cleaned in seen or _is_navigation_noise(cleaned):
                    continue
                seen.add(cleaned)
                candidates.append({"text": cleaned, "layer": layer_key, "source": source, "source_role": "layer_evidence"})
    return candidates


def strategic_packet_candidates(
    block: str,
    spec: dict[str, Any],
    strategic_packet: dict[str, Any],
    source_layer: str,
) -> list[dict[str, str]]:
    """Select ordered evidence candidates from a StrategicEvidencePacket."""
    groups = strategic_packet.get("groups") if isinstance(strategic_packet, dict) else {}
    if not isinstance(groups, dict):
        return []
    candidates: list[dict[str, str]] = []
    for group in spec.get("strategic_groups") or []:
        for item in groups.get(group) or []:
            if not isinstance(item, dict):
                continue
            text = _clean_candidate_text(str(item.get("text") or ""))
            if not text:
                continue
            candidates.append(
                {
                    "text": text,
                    "layer": source_layer,
                    "source": f"strategic:{group}",
                    "group": group,
                    "source_type": str(item.get("source_type") or ""),
                    "feature_name": str(item.get("feature_name") or ""),
                    "url": str(item.get("url") or ""),
                    "surface_role": str(item.get("surface_role") or ""),
                    "entity_scope": str(item.get("entity_scope") or ""),
                    "source_role": source_role_for_candidate(item),
                    "block": block,
                }
            )
    return sorted(candidates, key=strategic_packet_candidate_priority)


def strategic_packet_candidate_priority(
    candidate: dict[str, str],
) -> tuple[int, int, int, int, int, int, int, int, int]:
    """Rank candidates so concrete owned offer evidence wins over snippets/noise."""
    source_type = str(candidate.get("source_type") or "")
    source_role = str(candidate.get("source_role") or "unknown")
    feature_name = str(candidate.get("feature_name") or "")
    group = str(candidate.get("group") or "")
    text = str(candidate.get("text") or "")
    low = text.lower()
    group_rank = {"product_offer": 0, "hero_claims": 1, "outcome": 2, "audience": 3}.get(
        group, 4
    )
    source_rank = {"owned_raw": 0, "owned": 1, "social": 2}.get(source_type, 3)
    source_role_rank = _source_role_rank(source_role)
    feature_rank = 3 if feature_name == "search_visibility" else 0
    truncated_rank = (
        2 if re.search(r"\b(?:com|streamli|throu|c|users?)\s*$", text, re.I) else 0
    )
    generic_rank = 2 if low in {"todo en una plataforma", "all in one platform"} else 0
    title_rank = (
        1 if (" | " in text or " – " in text or " # " in text) and len(text) < 120 else 0
    )
    richness = sum(
        1
        for marker in (
            "platform",
            "plataforma",
            "teams",
            "creators",
            "developers",
            "enterprises",
            "helps",
            "helping",
            "ayuda",
            "enables",
            "streamline",
            "streamlines",
            "for ",
            "para ",
            "gestionar",
            "hacer crecer",
            "servicios financieros",
            "payments",
            "pagos",
            "reduce",
            "reduce costes",
            "secure",
            "competitive advantage",
            "web search",
            "search engine",
            "crawler",
            "real-world data",
            "video generation",
            "operating system",
            "open stack",
            "transport",
            "transporte",
            "planning",
            "roadmap",
            "human intelligence",
            "business analyst",
            "research people",
            "creative entity",
            "wield power",
            "world stage",
        )
        if marker in low
    )
    useful_length = min(len(text), 220)
    return (
        group_rank,
        generic_rank,
        truncated_rank,
        -richness,
        title_rank,
        source_role_rank,
        source_rank,
        feature_rank,
        -useful_length,
    )
