"""Executable TLDR Brand3 block interpreter specs.

The specs define the exercise each migrated TLDR block must perform. Runtime
logic still lives in ``extractor.py`` for now; this module keeps the method
contract separate from scanner orchestration so specs can evolve independently.
"""

from __future__ import annotations

import re
from typing import Any


TLDR_BLOCK_INTERPRETER_SPECS = {
    "value_proposition": {
        "block": "value_proposition",
        "task": "Identify the concrete value exchange: offer, audience, and change.",
        "primary_question": "What does the brand offer, to whom, and what changes for that audience?",
        "source_layers": ["netspace", "tactispace", "ambientspace"],
        "strategic_groups": ["product_offer", "audience", "outcome", "hero_claims"],
        "look_for": [
            "offer", "offers", "solution", "solutions", "platform", "product", "service", "services",
            "api", "system", "management", "streamline", "centralise", "centralize", "reconcile",
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
        "strategic_groups": ["mission_language"],
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


def get_tldr_block_interpreter_spec(block: str) -> dict[str, Any] | None:
    """Return the executable spec for a migrated TLDR block."""
    spec = TLDR_BLOCK_INTERPRETER_SPECS.get(block)
    return dict(spec) if spec else None


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
                    "block": block,
                }
            )
    return sorted(candidates, key=strategic_packet_candidate_priority)


def strategic_packet_candidate_priority(
    candidate: dict[str, str],
) -> tuple[int, int, int, int, int, int, int, int]:
    """Rank candidates so concrete owned offer evidence wins over snippets/noise."""
    source_type = str(candidate.get("source_type") or "")
    feature_name = str(candidate.get("feature_name") or "")
    group = str(candidate.get("group") or "")
    text = str(candidate.get("text") or "")
    low = text.lower()
    group_rank = {"product_offer": 0, "hero_claims": 1, "outcome": 2, "audience": 3}.get(
        group, 4
    )
    source_rank = {"owned_raw": 0, "owned": 1, "social": 2}.get(source_type, 3)
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
        source_rank,
        feature_rank,
        -useful_length,
    )


def accepted_block_evidence(
    block: str,
    spec: dict[str, Any],
    candidates: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Filter evidence candidates according to the block's executable spec."""
    accepted: list[dict[str, str]] = []
    allowed_groups = set(spec.get("strategic_groups") or [])
    for candidate in candidates:
        text = candidate["text"]
        low = text.lower()
        if any(term in low for term in spec["reject"]):
            continue
        group = candidate.get("group")
        from_packet = str(candidate.get("source", "")).startswith("strategic:")
        if from_packet:
            if group not in allowed_groups:
                continue
            if block == "mission" and (
                _is_testimonial_evidence(low)
                or _is_truncated_evidence(low)
                or not (_has_operating_activity_signal(low) or _has_formal_mission_signal(low))
            ):
                continue
            if block == "vision" and (
                _is_truncated_evidence(low) or not _has_future_signal(low)
            ):
                continue
        else:
            if not any(_contains_keyword(low, term) for term in spec["look_for"]):
                continue
            if block == "mission" and (
                _is_truncated_evidence(low)
                or not (_has_operating_activity_signal(low) or _has_formal_mission_signal(low))
            ):
                continue
            if block == "vision" and (
                _is_truncated_evidence(low) or not _has_future_signal(low)
            ):
                continue
            if block == "value_proposition" and not _has_offer_signal(low):
                continue
        accepted.append(candidate)
    return accepted


def _clean_candidate_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" -|•*\t")


def _contains_keyword(text: str, keyword: str) -> bool:
    escaped = re.escape(keyword.lower())
    if " " in keyword:
        return re.search(escaped, text, flags=re.IGNORECASE) is not None
    return (
        re.search(
            rf"(?<![A-Za-zÀ-ÿ0-9]){escaped}(?![A-Za-zÀ-ÿ0-9])",
            text,
            flags=re.IGNORECASE,
        )
        is not None
    )


def _has_operating_activity_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "we build",
            "we create",
            "we provide",
            "we offer",
            "we operate",
            "we deliver",
            "builds",
            "creates",
            "provides",
            "offers",
            "operates",
            "delivers",
            "offers",
            "accepts",
            "implements",
            "creamos",
            "construimos",
            "ofrecemos",
            "ofrece",
            "acepta",
            "implementa",
            "proporcionamos",
            "desarrollamos",
        )
    )


def _is_testimonial_evidence(text: str) -> bool:
    low = text.strip().lower()
    return low.startswith((">", "“", '"')) or " nos ofrece " in low or " customer " in low


def _is_truncated_evidence(text: str) -> bool:
    return bool(re.search(r"\b(?:com|streamli|throu|users?|c)\s*$", text.strip(), re.I))


def _has_formal_mission_signal(text: str) -> bool:
    return bool(
        re.search(
            r"\b(our mission|nuestra misión|nuestra mision|mission revolves around)\b",
            text,
            re.I,
        )
    )


def _has_future_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "future",
            "future of",
            "vision",
            "new model",
            "new paradigm",
            "towards",
            "toward",
            "redefine",
            "next generation",
            "futuro",
            "visión",
            "nuevo modelo",
            "nuevo paradigma",
            "nueva generación",
            "creative entity",
            "creative work",
            "wield power",
            "world stage",
        )
    )


def _has_offer_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "solution",
            "solutions",
            "platform",
            "product",
            "service",
            "services",
            "api",
            "system",
            "payments",
            "pagos",
            "billing",
            "facturación",
            "financial services",
            "servicios financieros",
            "revenue",
            "ingresos",
            "streamline",
            "centralise",
            "centralize",
            "soluciones",
            "human intelligence",
            "business analyst",
            "research people",
            "research people and companies",
            "materias primas",
            "ingredientes",
            "biorremediación",
            "cosmética",
            "nutrición",
        )
    )
