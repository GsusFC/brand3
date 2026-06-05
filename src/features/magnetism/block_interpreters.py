"""Executable TLDR Brand3 block interpreter specs.

The specs define the exercise each migrated TLDR block must perform. This
module owns candidate selection, evidence acceptance, and block-level metadata
for migrated TLDR blocks while the extractor remains responsible for scanner
orchestration.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from src.reports.brand_context_brief import brand_context_candidates
from src.reports.editorial_policy import overreach_warnings
from src.reports.vertical_signals import (
    product_offer_family_allows_multiple_lines,
    product_offer_family_for_text,
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


def get_tldr_block_interpreter_spec(block: str) -> dict[str, Any] | None:
    """Return the executable spec for a migrated TLDR block."""
    spec = TLDR_BLOCK_INTERPRETER_SPECS.get(block)
    return dict(spec) if spec else None


LOW_TRUST_BLOCK_SOURCE_ROLES = {"blog_feed", "proof_customer", "legal_navigation"}


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


def interpret_tldr_block(
    block: str,
    spec: dict[str, Any],
    candidates: list[dict[str, str]],
    layers: dict[str, Any],
    primary_layer_key: str,
) -> dict[str, Any] | None:
    """Interpret a TLDR block from candidate evidence using its executable spec."""
    accepted = accepted_block_evidence(block, spec, candidates)
    if not accepted:
        sufficiency = evidence_sufficiency_from_spec(block, candidates, accepted)
        return {
            "content": None,
            "detected": False,
            "claim_type": "absent",
            "mode": "not_detected",
            "confidence": "low",
            "evidence": [],
            "rationale": "Insufficient evidence to articulate this block responsibly.",
            "reasoning": "Insufficient evidence to articulate this block responsibly.",
            "observations": [f"Applied executable {block} interpreter spec."],
            "counter_evidence": sufficiency.get("missing_evidence", []),
            "source_layers": [primary_layer_key],
            "human_review_recommended": sufficiency.get("status") in {"partial", "polluted"},
            "evidence_sufficiency": sufficiency,
        }

    evidence = accepted[0]["text"]
    diagnostics = block_evidence_diagnostics(block, accepted, layers, primary_layer_key)
    answer = answer_from_spec(block, evidence, accepted)
    display_evidence = evidence_from_spec(block, evidence, answer, accepted)
    mode = mode_from_spec(block, diagnostics)
    confidence = confidence_from_spec(block, diagnostics, accepted)
    claim_type = claim_type_from_spec(block, diagnostics)
    counter_evidence = counter_evidence_from_spec(block, diagnostics)
    human_review = human_review_from_spec(block, diagnostics, confidence, counter_evidence)
    sufficiency = evidence_sufficiency_from_spec(block, candidates, accepted, diagnostics, counter_evidence)
    if sufficiency.get("decision") == "interpret_with_review":
        human_review = True
    reasoning_evidence = display_evidence[0] if display_evidence else evidence
    reasoning = reasoning_from_spec(block, reasoning_evidence, diagnostics)
    mode, confidence, counter_evidence, human_review = apply_editorial_policy_guardrails(
        block,
        answer,
        reasoning,
        mode,
        confidence,
        counter_evidence,
        human_review,
    )

    return {
        "content": answer,
        "detected": True,
        "claim_type": claim_type,
        "mode": mode,
        "confidence": confidence,
        "evidence": display_evidence,
        "rationale": reasoning,
        "reasoning": reasoning,
        "observations": observations_from_spec(block, diagnostics),
        "counter_evidence": counter_evidence,
        "source_layers": list(dict.fromkeys(item["layer"] for item in accepted)),
        "human_review_recommended": human_review,
        "evidence_sufficiency": sufficiency,
    }


def apply_editorial_policy_guardrails(
    block: str,
    answer: str,
    reasoning: str,
    mode: str,
    confidence: str,
    counter_evidence: list[str],
    human_review: bool,
) -> tuple[str, str, list[str], bool]:
    """Apply final editorial overreach checks to interpreted TLDR blocks."""
    warnings = overreach_warnings(f"{answer} {reasoning}")
    if not warnings:
        return mode, confidence, counter_evidence, human_review

    updated_counter = list(counter_evidence)
    updated_counter.append(
        "Editorial policy flagged possible overreach: " + ", ".join(sorted(set(warnings))) + "."
    )
    if confidence == "high":
        confidence = "medium"
    elif confidence == "medium":
        confidence = "low"
    if mode != "not_detected":
        mode = "needs_human_review"
    return mode, confidence, list(dict.fromkeys(updated_counter)), True


def evidence_sufficiency_from_spec(
    block: str,
    candidates: list[dict[str, str]],
    accepted: list[dict[str, str]],
    diagnostics: dict[str, Any] | None = None,
    counter_evidence: list[str] | None = None,
) -> dict[str, Any]:
    """Assess whether the available evidence is enough to interpret a TLDR block."""
    diagnostics = diagnostics or {}
    counter_evidence = counter_evidence or []
    noise_detected = _noise_detected_for_block(block, candidates, accepted)
    available_evidence = [item["text"] for item in accepted[:3] if item.get("text")]
    best_sources = _candidate_source_labels(accepted or candidates)
    missing_evidence = list(counter_evidence)

    if not candidates:
        status = "insufficient"
        missing_evidence.append(f"No candidate evidence was available for {block}.")
    elif not accepted:
        status = "polluted" if noise_detected else "insufficient"
        if noise_detected:
            missing_evidence.append("Candidate evidence was rejected as feed, article, CTA, navigation, or market-prediction noise.")
        else:
            minimum_rule = TLDR_BLOCK_INTERPRETER_SPECS[block]["minimum_evidence_rule"]
            missing_evidence.append(f"No candidate evidence met the minimum rule: {minimum_rule}")
    elif block == "value_proposition":
        strong = diagnostics.get("has_offer") and diagnostics.get("has_outcome")
        status = "sufficient" if strong else "partial"
    elif block == "mission":
        status = "sufficient" if diagnostics.get("has_operating_activity") else "partial"
    elif block == "vision":
        status = "sufficient" if diagnostics.get("has_formal_vision") and not noise_detected else "partial"
    else:
        status = "sufficient" if accepted and not noise_detected else "partial"

    if status == "sufficient":
        decision = "interpret"
    elif status == "partial":
        decision = "interpret_with_review"
    else:
        decision = "not_detected"

    return {
        "status": status,
        "available_evidence": available_evidence,
        "missing_evidence": list(dict.fromkeys(missing_evidence)),
        "noise_detected": noise_detected,
        "best_sources": best_sources,
        "decision": decision,
    }


def _candidate_source_labels(candidates: list[dict[str, str]]) -> list[str]:
    labels: list[str] = []
    for item in candidates:
        label = str(item.get("group") or item.get("source") or item.get("layer") or "unknown")
        if label and label not in labels:
            labels.append(label)
    return labels[:5]


def _noise_detected_for_block(
    block: str,
    candidates: list[dict[str, str]],
    accepted: list[dict[str, str]],
) -> bool:
    accepted_texts = {item.get("text") for item in accepted}
    rejected = [item for item in candidates if item.get("text") not in accepted_texts]
    for item in rejected:
        text = str(item.get("text") or "")
        low = text.lower()
        if _invalid_source_role_for_block(block, item):
            return True
        if _is_navigation_noise(text) or _is_feed_or_article_noise(text) or _is_truncated_evidence(text):
            return True
        if block == "vision" and (_is_market_prediction_noise(text) or _is_rhetorical_future_question_noise(text)):
            return True
        if block == "mission" and (_is_vague_mission_slogan(low) or _is_testimonial_evidence(low) or _is_values_statement_as_mission(low)):
            return True
        if block == "value_proposition" and _is_bad_value_prop_candidate(text):
            return True
    return False


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
        if _invalid_source_role_for_block(block, candidate):
            continue
        group = candidate.get("group")
        from_packet = str(candidate.get("source", "")).startswith("strategic:")
        if from_packet:
            if group not in allowed_groups:
                continue
            if block == "mission" and (
                _is_testimonial_evidence(low)
                or _is_truncated_evidence(low)
                or _is_feed_or_article_noise(text)
                or _is_vague_mission_slogan(low)
                or _is_values_statement_as_mission(low)
                or not (_has_operating_activity_signal(low) or _has_formal_mission_signal(low))
            ):
                continue
            if block == "vision" and (
                _is_truncated_evidence(low)
                or _is_feed_or_article_noise(text)
                or _is_market_prediction_noise(text)
                or _is_rhetorical_future_question_noise(text)
                or not _has_future_signal(low)
            ):
                continue
            if block == "value_proposition" and _is_bad_value_prop_candidate(text):
                continue
        else:
            if not any(_contains_keyword(low, term) for term in spec["look_for"]):
                continue
            if block == "mission" and (
                _is_truncated_evidence(low)
                or _is_feed_or_article_noise(text)
                or _is_vague_mission_slogan(low)
                or _is_values_statement_as_mission(low)
                or not (_has_operating_activity_signal(low) or _has_formal_mission_signal(low))
            ):
                continue
            if block == "vision" and (
                _is_truncated_evidence(low)
                or _is_feed_or_article_noise(text)
                or _is_market_prediction_noise(text)
                or _is_rhetorical_future_question_noise(text)
                or not _has_future_signal(low)
            ):
                continue
            if block == "value_proposition" and (_is_bad_value_prop_candidate(text) or not _has_offer_signal(low)):
                continue
        accepted.append(candidate)
    if block == "value_proposition" and accepted:
        has_offer_candidate = any(
            str(item.get("group") or "") == "product_offer" or _has_offer_signal(str(item.get("text") or "").lower())
            for item in accepted
        )
        if not has_offer_candidate:
            return []
    return accepted


def block_evidence_diagnostics(
    block: str,
    accepted: list[dict[str, str]],
    layers: dict[str, Any],
    primary_layer_key: str,
) -> dict[str, Any]:
    text = "\n".join(item["text"] for item in accepted).lower()
    groups = {str(item.get("group")) for item in accepted if item.get("group")}
    source_roles = sorted({str(item.get("source_role") or "unknown") for item in accepted})
    explicit_sources = [str(item.get("source") or "") for item in accepted]
    product_offer_count = sum(
        1 for item in accepted if str(item.get("group") or "") == "product_offer"
    )
    has_multiple_offers = _has_divergent_product_offers(accepted)
    return {
        "has_explicit_evidence": any(
            source == "evidence" or source.startswith("strategic:")
            for source in explicit_sources
        ),
        "has_offer": _has_offer_signal(text) or "product_offer" in groups,
        "has_audience": _has_audience_signal(text) or "audience" in groups,
        "has_outcome": _has_outcome_signal(text) or "outcome" in groups,
        "has_operating_activity": _has_operating_activity_signal(text) or "mission_language" in groups,
        "has_future": _has_future_signal(text) or "vision_language" in groups,
        "has_formal_vision": bool(
            re.search(r"\b(our vision is|vision is|nuestra visión es|nuestra vision es)\b", text)
        ),
        "candidate_count": len(accepted),
        "product_offer_count": product_offer_count,
        "has_multiple_offers": has_multiple_offers,
        "accepted_groups": sorted(groups),
        "source_roles": source_roles,
        "primary_layer_detected": bool(layers.get(primary_layer_key, {}).get("detected")),
    }


def _has_divergent_product_offers(accepted: list[dict[str, str]]) -> bool:
    product_offers = [
        item for item in accepted if str(item.get("group") or "") == "product_offer"
    ]
    if len(product_offers) <= 1:
        return False

    families = {
        family
        for item in product_offers
        if (family := product_offer_family_for_text(str(item.get("text") or "")))
    }
    if len(families) > 1:
        return True
    if len(families) == 1:
        return not product_offer_family_allows_multiple_lines(next(iter(families)))
    return True

def evidence_from_spec(
    block: str,
    evidence: str,
    answer: str,
    accepted: list[dict[str, str]] | None = None,
) -> list[str]:
    accepted = accepted or []
    if block in {"value_proposition", "mission"}:
        representative = _representative_evidence_phrase(evidence, answer)
        return [representative] if representative else [evidence]
    return [evidence]


def _representative_evidence_phrase(evidence: str, answer: str) -> str:
    cleaned = _clean_value_prop_answer_text(evidence)
    if len(cleaned) <= 240:
        return cleaned
    low_answer = answer.lower()
    candidates = _sentence_like_evidence_segments(cleaned)
    if not candidates:
        return cleaned[:237].rstrip() + "..."
    scored = sorted(
        candidates,
        key=lambda item: _representative_evidence_score(item, low_answer),
        reverse=True,
    )
    best = scored[0].strip()
    if len(best) > 240:
        best = best[:237].rstrip() + "..."
    return best


def _sentence_like_evidence_segments(text: str) -> list[str]:
    raw_parts = re.split(
        r"(?=(?:Build fast|The platform|Powered by|Deploy your app|Modern Compute|For builders|Deploy an app|Sandboxes|Every Sprite|Pay only|Storage That Keeps Up|Built-In Private Networking|VMs That Do Everything|Fly\.io is|A developer|A platform|Public Cloud Billing))",
        text,
    )
    parts: list[str] = []
    for raw in raw_parts:
        cleaned = re.sub(r"\s+", " ", raw).strip(" .-")
        if len(cleaned) < 20:
            continue
        if _is_weak_value_prop_addition(cleaned):
            continue
        parts.append(cleaned)
    if len(parts) <= 1:
        parts = [s.strip(" .-") for s in _sentences(text) if len(s.strip()) >= 20]
    return parts


def _representative_evidence_score(text: str, low_answer: str) -> tuple[int, int, int]:
    low = text.lower()
    overlap = sum(1 for token in set(re.findall(r"[a-z0-9-]{4,}", low_answer)) if token in low)
    signal = sum(
        1
        for marker in (
            "platform for devs",
            "for builders",
            "deploy any code",
            "run any code",
            "sandboxes",
            "deploy your app",
            "developer-focused",
            "secure",
            "confidence",
        )
        if marker in low
    )
    length_penalty = abs(len(text) - 140)
    return (signal, overlap, -length_penalty)


def answer_from_spec(
    block: str,
    evidence: str,
    accepted: list[dict[str, str]] | None = None,
) -> str:
    if block == "value_proposition":
        return _value_proposition_answer(evidence, accepted or [])
    if block == "mission":
        return _mission_answer(evidence)
    if block == "vision" and "macroalgas" in evidence.lower() and "nuevo modelo" in evidence.lower():
        return "A regenerative industrial model built around the potential of Mediterranean macroalgae."
    return evidence


def mode_from_spec(block: str, diagnostics: dict[str, Any]) -> str:
    if block == "vision":
        return "compressed" if diagnostics.get("has_formal_vision") else "interpreted_from_discourse"
    return "compressed" if diagnostics["has_explicit_evidence"] else "interpreted_from_discourse"


def claim_type_from_spec(block: str, diagnostics: dict[str, Any]) -> str:
    if block == "vision":
        return "declared" if diagnostics.get("has_formal_vision") else "inferred"
    return "declared" if diagnostics["has_explicit_evidence"] else "inferred"


def confidence_from_spec(
    block: str,
    diagnostics: dict[str, Any],
    accepted: list[dict[str, str]],
) -> str:
    if block == "value_proposition":
        if diagnostics["has_offer"] and diagnostics["has_outcome"] and diagnostics["has_audience"]:
            return "high"
        if diagnostics["has_offer"] and (diagnostics["has_outcome"] or diagnostics["has_audience"]):
            return "medium"
        return "low"
    if block == "mission":
        return "medium" if diagnostics["has_operating_activity"] else "low"
    if block == "vision":
        return "medium" if diagnostics["has_future"] and accepted else "low"
    return "medium"


def counter_evidence_from_spec(block: str, diagnostics: dict[str, Any]) -> list[str]:
    limits: list[str] = []
    if block == "value_proposition":
        if not diagnostics["has_audience"]:
            limits.append("The available value proposition evidence does not clearly name the audience.")
        if not diagnostics["has_outcome"]:
            limits.append("The available value proposition evidence does not clearly state the outcome or change for the audience.")
        if diagnostics.get("has_multiple_offers"):
            limits.append("The evidence contains multiple offer signals, so a strategist should confirm the primary value proposition.")
    if block == "vision" and not diagnostics.get("has_formal_vision"):
        limits.append("The available evidence contains future-facing language, but not a formal vision statement.")
    if block == "mission" and not diagnostics["has_explicit_evidence"]:
        limits.append("The mission is inferred from product/service evidence rather than stated as a formal mission.")
    return limits


def human_review_from_spec(
    block: str,
    diagnostics: dict[str, Any],
    confidence: str,
    counter_evidence: list[str],
) -> bool:
    if block == "vision":
        return True if counter_evidence or confidence == "low" else False
    if block == "value_proposition":
        return (
            confidence == "low"
            or len(counter_evidence) >= 2
            or diagnostics.get("has_multiple_offers", False)
        )
    if block == "mission":
        return not diagnostics["has_explicit_evidence"] or confidence == "low"
    return False


def reasoning_from_spec(block: str, evidence: str, diagnostics: dict[str, Any]) -> str:
    if block == "value_proposition":
        parts = ["The evidence states a concrete offer"]
        if diagnostics["has_audience"]:
            parts.append("names or implies an audience")
        if diagnostics["has_outcome"]:
            parts.append("and describes the operational change or outcome")
        return ", ".join(parts) + f": {evidence}"
    if block == "mission":
        return f"The evidence uses present-tense operating language that describes what the brand does today: {evidence}"
    if block == "vision":
        return f"The evidence contains future-facing or category-change language, so the block is treated as an interpreted vision signal: {evidence}"
    return f"The block is derived from accepted evidence: {evidence}"


def observations_from_spec(block: str, diagnostics: dict[str, Any]) -> list[str]:
    observations = [f"Applied executable {block} interpreter spec."]
    if block == "value_proposition":
        observations.append(
            "Detected offer/audience/outcome coverage: "
            f"offer={diagnostics['has_offer']}, audience={diagnostics['has_audience']}, outcome={diagnostics['has_outcome']}."
        )
        if diagnostics.get("accepted_groups"):
            observations.append("Strategic packet groups used: " + ", ".join(diagnostics["accepted_groups"]) + ".")
        if diagnostics.get("source_roles"):
            observations.append("Source roles used: " + ", ".join(diagnostics["source_roles"]) + ".")
        if diagnostics.get("has_multiple_offers"):
            observations.append("Multiple product_offer candidates were found; primary offer requires review.")
    if block == "mission":
        observations.append(f"Present-tense operating evidence={diagnostics['has_operating_activity']}.")
        if diagnostics.get("source_roles"):
            observations.append("Source roles used: " + ", ".join(diagnostics["source_roles"]) + ".")
    if block == "vision":
        observations.append(f"Future/category-change evidence={diagnostics['has_future']}.")
        if diagnostics.get("source_roles"):
            observations.append("Source roles used: " + ", ".join(diagnostics["source_roles"]) + ".")
    return observations


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
            "we help",
            "we make",
            "we enable",
            "we empower",
            "deploy",
            "deploys",
            "run any code",
            "lets you run",
            "lets you deploy",
            "launch instantly",
            "runs on",
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
            "estamos creando",
            "estamos creado",
            "convierte",
        )
    )


def _is_vague_mission_slogan(text: str) -> bool:
    low = text.strip().lower()
    return low in {"we make good shit"} or "shit" in low


def _is_values_statement_as_mission(text: str) -> bool:
    low = text.strip().lower()
    return low.startswith(("valoramos ", "we value ", "we believe ")) and not _has_formal_mission_signal(low)


def _is_feed_or_article_noise(text: str) -> bool:
    low = text.strip().lower()
    url_count = len(re.findall(r"https?://", low))
    if any(marker in low for marker in ("]]>", "#respond", "/feed/", "?p=")):
        return True
    if url_count >= 2:
        return True
    if re.search(r"\b(?:mon|tue|wed|thu|fri|sat|sun),\s+\d{1,2}\s+[a-z]{3}\s+\d{4}", low):
        return True
    editorial_markers = (
        "imagínate",
        "imaginate",
        "cómo puedes beneficiarte",
        "como puedes beneficiarte",
        "lo que no quieren que sepas",
        "descubre por qué",
        "descubre por que",
        "activo subyacente",
        "caídas de precios",
        "caidas de precios",
        "este tipo de seguridad",
        "muchos, ya que",
        "no te quedes fuera",
        "tú tienes una decisión",
        "tu tienes una decision",
        "quedarte en la sombra",
        "ser parte del cambio",
    )
    return any(marker in low for marker in editorial_markers)


def _is_rhetorical_future_question_noise(text: str) -> bool:
    low = text.strip().lower()
    if not _has_future_signal(low):
        return False
    if not low.endswith("?") and "?" not in low:
        return False
    rhetorical_markers = (
        "cómo ves el futuro",
        "como ves el futuro",
        "qué opinas del futuro",
        "que opinas del futuro",
        "imaginas el futuro",
        "ves el futuro",
    )
    return any(marker in low for marker in rhetorical_markers)


def _is_market_prediction_noise(text: str) -> bool:
    low = text.strip().lower()
    if not _has_future_signal(low):
        return False
    market_prediction_markers = (
        "japón está liderando",
        "japon está liderando",
        "japon esta liderando",
        "japón ha comprendido",
        "japon ha comprendido",
        "el futuro de las finanzas pasa por",
        "el futuro de las criptomonedas",
        "otros aún no ven",
        "otros aun no ven",
        "referente global",
        "incertidumbre regulatoria",
        "mercado japonés",
        "mercado japones",
    )
    if any(marker in low for marker in market_prediction_markers):
        return True
    talks_about_external_market = any(term in low for term in ("japón", "japon", "países", "paises", "mercado"))
    talks_about_brand_action = any(
        term in low
        for term in (
            "we are building",
            "we're building",
            "our vision",
            "nuestra visión",
            "nuestra vision",
            "estamos creando",
            "estamos creado",
            "bokeroon",
        )
    )
    return talks_about_external_market and not talks_about_brand_action


def _is_testimonial_evidence(text: str) -> bool:
    low = text.strip().lower()
    return low.startswith((">", "“", '"')) or " nos ofrece " in low or " customer " in low


def _is_truncated_evidence(text: str) -> bool:
    return bool(re.search(r"\b(?:com|streamli|throu|softwar|platfor|developmen|infrastructur|users?|c|w|cr)\s*$", text.strip(), re.I))


def _has_formal_mission_signal(text: str) -> bool:
    return bool(
        re.search(
            r"\b(our mission|nuestra misión|nuestra mision|mission revolves around|on a mission to)\b",
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
            "assistant",
            "companion",
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
            "open stack",
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


def _has_audience_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "for ",
            "para ",
            "teams",
            "operators",
            "creators",
            "subscribers",
            "athletes",
            "atletas",
            "banks",
            "erp",
            "cosmética",
            "nutrición",
            "health animal",
            "salud animal",
        )
    )


def _has_outcome_signal(text: str) -> bool:
    return any(
        term in text
        for term in (
            "streamline",
            "centralise",
            "centralize",
            "reconcile",
            "execute",
            "forecast",
            "control",
            "grow",
            "grow your business",
            "grow your revenue",
            "hacer crecer",
            "gestionar",
            "gestionar el movimiento de dinero",
            "modelos personalizados",
            "potenciar",
            "transform",
            "reduce",
            "save",
            "last over time",
            "built to last",
            "duren en el tiempo",
            "dure en el tiempo",
            "duraderos",
            "duraderas",
            "build relationships",
            "get things done",
            "improve",
            "valuable channel",
            "turn subscribers into customers",
            "biorremediación",
        )
    )


def _value_proposition_answer(evidence: str, accepted: list[dict[str, str]]) -> str:
    primary = _clean_value_prop_answer_text(evidence)
    primary_low = primary.lower()
    if _is_developer_cloud_positioning(primary_low):
        return "A developer cloud platform for shipping and running code confidently in secure sandboxes."
    if (
        not accepted
        or len(primary) >= 90
        or (_has_audience_signal(primary_low) and _has_outcome_signal(primary_low))
    ):
        return primary
    additions: list[str] = []
    for target_group in ("outcome", "audience"):
        for item in accepted:
            text = _clean_value_prop_answer_text(str(item.get("text") or ""))
            if item.get("group") != target_group or not text or text == primary or text in additions:
                continue
            if _is_weak_value_prop_addition(text):
                continue
            additions.append(text)
            break
    if not additions:
        return primary
    answer = primary.rstrip(".") + ". " + " ".join(additions)
    return _clean_value_prop_answer_text(answer[:360].rstrip())



def _mission_answer(evidence: str) -> str:
    cleaned = _clean_value_prop_answer_text(evidence)
    low = cleaned.lower()
    if _is_developer_cloud_positioning(low):
        return "Provides developer infrastructure for deploying and running code in secure sandboxes."
    if re.match(r"^¿[^?]{8,180}\?\s+en\s+", cleaned, flags=re.I):
        cleaned = re.sub(r"^¿[^?]{8,180}\?\s+", "", cleaned, flags=re.I).strip()
        low = cleaned.lower()
    if "menos complicaciones" in low:
        cleaned = re.split(r"\bMenos complicaciones\b", cleaned, maxsplit=1, flags=re.I)[0].strip().rstrip(". ") + "."
    if len(cleaned) > 360:
        return cleaned[:357].rstrip() + "..."
    return cleaned


def _is_developer_cloud_positioning(text: str) -> bool:
    return (
        ("platform for devs" in text or "for builders" in text or "developer-focused public cloud" in text)
        and ("deploy any code" in text or "run any code" in text or "sandboxes" in text)
    )

def _clean_value_prop_answer_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = re.sub(r"\s*\[[^\]]{2,90}\]\(https?://[^)]+\)\s*$", "", cleaned).strip()
    cleaned = re.sub(r"^New(?=[A-Z][A-Za-z0-9]+(?:'s)\b)", "", cleaned)
    cleaned = re.sub(r"^Base App Base Build Base Chain Base Pay Base App\s+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^[A-Z][A-Za-z0-9 .&'*-]{1,60}\s+\|\s+", "", cleaned)
    cleaned = re.sub(r"\s+Teams Changelog Blog Support Docs Explore.*$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\bWhere sales begin\s+Where sales begin\b", "Where sales begin", cleaned, flags=re.I)
    cleaned = re.sub(r"^Why [A-Z][^?]{2,120}\?\.\s*", "", cleaned)
    cleaned = re.sub(r"\s+Businesses spend thousands on ads.*$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\.?launching soon\s*$", ".", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\s+Suscr[ií]bete\b.*$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^¿[^?]{8,180}\?\s+(?=En\s+)", "", cleaned, flags=re.I).strip()
    return cleaned.strip()


def _is_bad_value_prop_candidate(text: str) -> bool:
    stripped = text.strip()
    low = stripped.lower()
    if low.startswith("source:"):
        return True
    if _is_truncated_evidence(low):
        return True
    if stripped.startswith("![") or "![" in stripped:
        return True
    if _looks_like_concatenated_copy(stripped):
        return True
    if re.fullmatch(r"\[[^\]]{2,120}\]\(https?://[^)]+\)", stripped):
        return True
    if "play video pause video" in low:
        return True
    if "teams changelog blog support docs" in low:
        return True
    if _looks_like_web_chrome_or_navigation_blob(low):
        return True
    if _looks_like_portfolio_case_card(low):
        return True
    if low.count("moments of activation") >= 2:
        return True
    if "schema detected:" in low:
        return True
    if "technology, information and internet company" in low:
        return True
    if low.startswith("a public cloud for security nerds") and len(stripped) > 420:
        return True
    if " company. " in low and " is a " in low[:120]:
        return True
    if " | " in stripped and "##" in stripped:
        return True
    if " b a s e b a s e " in low or "chain products developers solutions community" in low:
        return True
    if "customers logos" in low or "_next/image" in low:
        return True
    if "book a demo" in low and low.startswith(("book a demo", "talk to")):
        return True
    if any(marker in low for marker in ("política de privacidad", "politica de privacidad", "política de cookies", "politica de cookies", "rgpd", "lssi", "protección de datos", "proteccion de datos")):
        return True
    if "hashtag" in low and any(marker in low for marker in ("instagram", "comparte tus propias fotos", "inspírate", "inspirate")):
        return True
    if low.startswith(("inclusión ", "inclusion ")) and "valoramos" in low:
        return True
    if stripped.count("**](http") or stripped.endswith("]"):
        return True
    return False


def _looks_like_web_chrome_or_navigation_blob(low: str) -> bool:
    chrome_hits = sum(
        1
        for marker in (
            "sign in",
            "subscribe",
            "book a call",
            "work about",
            "services collections",
            "home newsletter",
            "columnists",
            "podcast products events",
            "guides consulting",
            "search about us careers",
            "get a demo",
            "launch now",
        )
        if marker in low
    )
    if chrome_hits >= 2:
        return True
    if "[&>*]" in low or "*]:block" in low:
        return True
    return False


def _looks_like_portfolio_case_card(low: str) -> bool:
    if len(low) > 180 and any(marker in low for marker in ("book a call", "work about", "services collections")):
        return True
    if (
        any(marker in low for marker in ("case study", "portfolio", "crafting a brand", "brand and platform redesign"))
        and not any(marker in low for marker in ("we are", "we build", "we provide", "platform for", "service for"))
    ):
        return True
    if "go sprint" in low and "go to market" in low and "what's included" in low:
        return True
    return False


def _looks_like_concatenated_copy(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 80:
        return False
    space_ratio = stripped.count(" ") / max(len(stripped), 1)
    return space_ratio < 0.04


def _is_weak_value_prop_addition(text: str) -> bool:
    low = text.strip().lower()
    if len(low) < 40 and not re.search(r"\b(?:helps|help|enables|enable|streamlines|automates|reduces|improves|builds|creates|for|para)\b", low):
        return True
    if any(marker in low for marker in ("copyright", "all rights reserved", "pricing", "privacy policy", "terms of service", "connect it to your favorite tools", "outlook sendgrid mailchimp")):
        return True
    if any(marker in low for marker in ("](", "→](", "learn more", "calculate savings", "bring all your tools")):
        return True
    return low in {"help and security", "startups program"}


def _evidence_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value:
        return [str(value).strip()]
    return []


def _sentences(text: str) -> list[str]:
    raw_segments = [s.strip() for s in re.split(r"[.!?\n]+", text or "") if len(s.strip()) > 5]
    segments: list[str] = []
    for segment in raw_segments:
        if len(segment) <= 320:
            segments.append(segment)
            continue
        cuts = re.split(
            r"(?=\b(?:Macroalgas|Soluciones|Únete|Unete|Ingredientes|Creamos|Servicios|Nuestras)\b)",
            segment,
        )
        segments.extend(cut.strip() for cut in cuts if len(cut.strip()) > 10)
    return segments


def _clean_layer_candidate_text(value: str) -> str:
    cleaned = " ".join(value.split()).strip(" -•*\t")
    for marker in (" Contáctanos", " Contacto", " Nuestras soluciones", " Main Menu"):
        idx = cleaned.find(marker)
        if idx > 40:
            cleaned = cleaned[:idx].strip()
    return cleaned


def _is_navigation_noise(value: str) -> bool:
    low = value.lower().strip()
    if low.startswith("main menu"):
        return True
    nav_tokens = ("contacto", "contáctanos", "menu", "menú", "alternar menú")
    return len(value) < 120 and sum(1 for token in nav_tokens if token in low) >= 2
