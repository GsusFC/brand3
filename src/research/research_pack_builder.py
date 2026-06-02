"""Build BrandResearchPack objects from the Brand Research evidence graph."""

from __future__ import annotations

from typing import Iterable

from src.reports.brand_research_pack import (
    BrandResearchPack,
    EntityResolution,
    ResearchEvidence,
    ResearchSource,
)
from src.research.evidence_graph import EvidenceClaim, EvidenceGraph


def build_brand_research_pack_from_graph(graph: EvidenceGraph) -> BrandResearchPack:
    """Adapt the BrandResearch EvidenceGraph into the existing pack contract.

    This bridge lets downstream TLDR code consume the new research substrate
    without forcing a rewrite of the current Magnetism integration.
    """

    resolved = EntityResolution(
        resolved_entity=graph.run.resolved_entity or graph.run.brand_name,
        entity_type=_pack_entity_type(graph.run.entity_type),
        canonical_url=graph.run.input_url,
        parent_brand=graph.run.parent_brand,
        surface_role=_primary_surface_role(graph),
        entity_scope=_primary_entity_scope(graph),
        confidence=graph.run.confidence,
        notes=list(graph.run.notes),
    )
    source_map = {
        source.url: ResearchSource(
            url=source.url,
            source_type=_pack_source_type(source.source_type),
            label=source.label,
            surface_role=source.surface_role,
            entity_scope=source.entity_scope,
            title=source.title,
            notes=list(source.notes),
        )
        for source in graph.sources.values()
        if source.url
    }
    claims = [claim for claim in graph.claims if claim.claim_type != "noise"]
    proof_points = _research_evidence(
        [claim for claim in graph.claims if claim.claim_type in {"proof", "feature_evidence"}],
        kind="proof",
    )
    founder_or_press_context = _research_evidence(
        [claim for claim in graph.claims if claim.claim_type == "founder_press"],
        kind="context",
    )
    noise_rejected = _research_evidence(
        [claim for claim in graph.claims if claim.claim_type == "noise"],
        kind="noise",
    )
    offer = _offer_text(claims, graph=graph)
    product_summary = _product_summary_text(claims) or offer or _first_claim_text(claims, ("hero_claim", "outcome"))
    company_summary = _company_summary_text(claims, graph=graph) or offer
    outcome = _first_claim_text(claims, ("outcome",)) or _infer_outcome([offer, product_summary, company_summary])
    audience = _audience_text(claims, [offer, product_summary, company_summary, outcome])
    declared_mission = _first_claim_text(claims, ("mission",))
    future_direction = _first_claim_text(claims, ("vision",))
    signal_texts = _signal_texts(claims)
    personality_signals = _unique(
        _claim_texts(claims, ("personality",), limit=6)
        + _attribute_signals([product_summary, offer, company_summary] + signal_texts)
    )[:6]
    visual_or_conceptual_signals = _unique(
        _claim_texts(claims, ("hero_claim",), limit=6)
        + _concept_signals([company_summary, product_summary, offer, declared_mission, future_direction])
    )[:6]
    values_signals = _claim_texts(claims, ("values",), limit=6, reject_form_noise=True)
    attributes_signals = _unique(
        values_signals
        + _claim_texts(claims, ("personality",), limit=6, reject_form_noise=True)
        + _attribute_signals([company_summary, product_summary, offer, outcome, declared_mission] + signal_texts)
    )[:8]
    category = _category_from_graph(graph, offer=offer, product_summary=product_summary, company_summary=company_summary)
    evidence_gaps = _evidence_gaps(
        graph=graph,
        offer=offer,
        audience=audience,
        outcome=outcome,
        mission=declared_mission,
        proof_points=proof_points,
        official_urls=_official_urls(graph),
        company_summary=company_summary,
        product_summary=product_summary,
    )

    return BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url=graph.run.input_url,
        resolved_entity=resolved,
        entity_type=resolved.entity_type,
        parent_brand=graph.run.parent_brand,
        official_urls=_official_urls(graph),
        analyzed_urls=[source.url for source in graph.sources.values() if source.url],
        source_map=source_map,
        company_summary=company_summary,
        product_summary=product_summary,
        audience=audience,
        offer=offer,
        outcome=outcome,
        category=category,
        declared_purpose=_first_claim_text(claims, ("mission", "hero_claim")),
        declared_mission=declared_mission,
        future_direction=future_direction,
        tone_of_voice=_tone_summary(personality_signals, [product_summary, offer, company_summary]),
        personality_signals=personality_signals,
        visual_or_conceptual_signals=visual_or_conceptual_signals,
        values_signals=values_signals,
        attributes_signals=attributes_signals,
        proof_points=proof_points,
        founder_or_press_context=founder_or_press_context,
        noise_rejected=noise_rejected,
        evidence_gaps=evidence_gaps,
        confidence_notes=_confidence_notes(graph),
    )


def _research_evidence(claims: Iterable[EvidenceClaim], *, kind: str) -> list[ResearchEvidence]:
    items: list[ResearchEvidence] = []
    seen: set[tuple[str, str, str]] = set()
    for claim in claims:
        text = claim.quote or claim.text
        key = (text.lower(), claim.source_url, claim.claim_type)
        if not text or key in seen:
            continue
        seen.add(key)
        items.append(
            ResearchEvidence(
                text=text,
                kind=kind,
                source_url=claim.source_url,
                source_type=_pack_source_type(claim.source_type),
                source_label=claim.claim_type,
                surface_role=claim.surface_role,
                entity_scope=claim.entity_scope,
                topic=claim.noise_reason or claim.claim_type,
                confidence=claim.confidence,
                notes=list(claim.notes),
            )
        )
    return items


def _first_claim_text(claims: Iterable[EvidenceClaim], claim_types: tuple[str, ...]) -> str:
    for claim_type in claim_types:
        for claim in claims:
            if claim.claim_type == claim_type and claim.text:
                return claim.text
    return ""


def _offer_text(claims: Iterable[EvidenceClaim], *, graph: EvidenceGraph | None = None) -> str:
    claim_list = list(claims)
    claim_types = {"product_offer", "hero_claim", "audience", "outcome", "feature_evidence"}
    if graph and _is_company_brand_graph(graph):
        claim_types.add("mission")
    candidates = [
        claim
        for claim in claim_list
        if claim.claim_type in claim_types
        and claim.text
        and _looks_like_offer(claim.text)
    ]
    if graph and _is_company_brand_graph(graph):
        candidates = _company_level_offer_candidates(candidates, graph) or candidates
    if candidates:
        return _compact_offer_text(max(candidates, key=lambda claim: _offer_score(claim, graph=graph)).text)
    return _compact_offer_text(_first_claim_text(claim_list, ("product_offer", "hero_claim", "outcome", "audience")))


def _looks_like_offer(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in (
            "new home for your internet",
            "platform",
            "app builder",
            "browser",
            "tabs",
            "workspaces",
            "assistant",
            "software",
            "infrastructure",
            "product",
            "tool",
            "service",
            "api",
            "solution",
        )
    )


def _offer_score(claim: EvidenceClaim, *, graph: EvidenceGraph | None = None) -> int:
    low = claim.text.lower()
    score = {
        "mission": 26,
        "product_offer": 30,
        "hero_claim": 25,
        "audience": 20,
        "outcome": 10,
        "feature_evidence": 12,
    }.get(claim.claim_type, 0)
    score += sum(
        weight
        for marker, weight in (
            ("app builder", 30),
            ("new home for your internet", 28),
            ("platform", 25),
            ("assistant", 25),
            ("browser", 25),
            ("tabs", 22),
            ("workspaces", 20),
            ("infrastructure", 20),
            ("api", 18),
            ("software", 12),
            ("tool", 10),
            ("service", 8),
            ("solution", 8),
        )
        if marker in low
    )
    if "mission" in low:
        score -= 25
    if "founder" in low or "founders" in low:
        score -= 5
    if graph and _is_company_brand_graph(graph):
        entity = str(graph.run.resolved_entity or graph.run.brand_name or "").lower()
        if entity and entity in low:
            score += 35
        if claim.source_type == "owned_about" or claim.surface_role == "mission_about":
            score += 22
        if claim.entity_scope in {"parent_brand", "audited_surface"}:
            score += 12
        if _product_specific_without_parent(claim, graph):
            score -= 65
        if _looks_like_heading_or_truncated_summary(claim.text):
            score -= 35
    if len(claim.text) > 700:
        score -= 18
    elif len(claim.text) > 420:
        score -= 8
    return score


def _looks_like_heading_or_truncated_summary(text: str) -> bool:
    cleaned = " ".join(str(text or "").split()).strip()
    if not cleaned:
        return False
    low = cleaned.lower()
    last_word = cleaned.rsplit(" ", 1)[-1].strip(" .,:;").lower()
    return (
        low.startswith("about ")
        or " # " in cleaned
        or (0 < len(last_word) <= 2 and len(cleaned) > 80)
    )


def _company_level_offer_candidates(
    candidates: list[EvidenceClaim],
    graph: EvidenceGraph,
) -> list[EvidenceClaim]:
    preferred = [
        claim
        for claim in candidates
        if _is_company_scoped_claim(claim) and not _product_specific_without_parent(claim, graph)
    ]
    if preferred:
        return preferred
    company_scoped = [claim for claim in candidates if not _is_product_scoped_claim(claim)]
    if company_scoped:
        return company_scoped
    return []


def _company_summary_text(claims: Iterable[EvidenceClaim], *, graph: EvidenceGraph) -> str:
    claim_list = list(claims)
    preferred = [
        claim
        for claim in claim_list
        if claim.claim_type in {"mission", "hero_claim", "product_offer", "outcome"}
        and claim.text
        and _is_company_scoped_claim(claim)
        and not _product_specific_without_parent(claim, graph)
    ]
    if preferred:
        return max(preferred, key=lambda claim: _offer_score(claim, graph=graph)).text
    return _first_claim_text(claim_list, ("mission", "hero_claim", "product_offer"))


def _product_summary_text(claims: Iterable[EvidenceClaim]) -> str:
    for claim in claims:
        if (
            claim.claim_type in {"product_offer", "feature_evidence", "outcome", "audience", "hero_claim"}
            and claim.text
            and _is_product_scoped_claim(claim)
            and not _looks_like_product_summary_noise(claim.text)
            and not _looks_like_audience_noise(claim.text)
        ):
            return claim.text
    return ""


def _audience_text(claims: Iterable[EvidenceClaim], fallback_texts: Iterable[str]) -> str:
    for claim in claims:
        if claim.claim_type == "audience" and claim.text and not _looks_like_audience_noise(claim.text):
            return claim.text
    return _infer_audience_from_texts(fallback_texts)


def _looks_like_product_summary_noise(text: str) -> bool:
    low = " ".join(str(text or "").lower().split())
    if not low:
        return True
    pricing_markers = {"free", "basic", "pro", "max", "enterprise", "plan", "plans", "pricing"}
    tokens = set(low.replace("/", " ").split())
    if len(tokens) <= 5 and tokens & pricing_markers:
        return True
    return any(
        marker in low
        for marker in (
            "free pro enterprise",
            "basic pro max",
            "pricing plans",
            "compare plans",
            "pick the plan",
            "plan that fits",
            "fits your stage",
            "billing cycle",
            "credit package",
            "changing your plan",
            "top up",
        )
    )


def _looks_like_audience_noise(text: str) -> bool:
    cleaned = " ".join(str(text or "").split()).strip()
    low = cleaned.lower()
    if not cleaned:
        return True
    if low in {"free", "basic", "pro", "max", "enterprise", "startup", "starter"}:
        return True
    if low.startswith("meet the "):
        return True
    if "|" in cleaned or cleaned.count(" - ") >= 1:
        return True
    if any(
        marker in low
        for marker in (
            "evaluate your",
            "free pro enterprise",
            "pricing",
            "copyright",
            "privacy policy",
            "unit of evaluation",
            "model calls",
            "nodes are running",
            "pick the plan",
            "plan that fits",
            "fits your stage",
            "billing cycle",
            "credit package",
            "changing your plan",
            "top up",
        )
    ):
        return True
    return False


def _infer_audience_from_texts(texts: Iterable[str]) -> str:
    low = " ".join(str(text or "") for text in texts).lower()
    if not low:
        return ""
    if "legal and development teams" in low:
        return "legal and development teams"
    if "development teams" in low:
        return "development teams"
    if "ai teams" in low or "agent" in low and "teams" in low:
        return "AI teams"
    if "companies" in low and ("generative ai" in low or "ai" in low):
        return "companies deploying generative AI"
    if "enterprise" in low or "enterprises" in low:
        return "enterprise teams"
    if "operations teams" in low:
        return "operations teams"
    if "teams" in low:
        return "teams"
    if "founders" in low:
        return "founders"
    if "traders" in low:
        return "traders"
    if "browser" in low or "tabs" in low or "workspaces" in low or "internet" in low:
        return "browser users"
    return ""


def _is_company_brand_graph(graph: EvidenceGraph) -> bool:
    return graph.run.entity_type in {"company", "brand"} and not graph.run.parent_brand


def _is_product_scoped_claim(claim: EvidenceClaim) -> bool:
    return (
        claim.entity_scope.startswith("product:")
        or claim.surface_role.startswith("product:")
        or claim.surface_role == "product_system"
        or claim.source_type in {"owned_product", "owned_docs", "owned_pricing"}
    )


def _is_company_scoped_claim(claim: EvidenceClaim) -> bool:
    return not _is_product_scoped_claim(claim) and claim.entity_scope in {
        "",
        "audited_surface",
        "parent_brand",
        "owned_surface",
        "evidence",
    }


def _product_specific_without_parent(claim: EvidenceClaim, graph: EvidenceGraph) -> bool:
    text = str(claim.text or "").lower()
    entity = str(graph.run.resolved_entity or graph.run.brand_name or "").lower()
    product_names = _product_names(graph)
    if not text or not product_names:
        return False
    mentions_product = any(product and product in text for product in product_names)
    mentions_parent = bool(entity and entity in text)
    return mentions_product and not mentions_parent


def _product_names(graph: EvidenceGraph) -> list[str]:
    names: list[str] = []
    for source in graph.sources.values():
        scope = str(source.entity_scope or "")
        role = str(source.surface_role or "")
        for value in (scope, role):
            if value.startswith("product:"):
                names.append(value.split(":", 1)[1])
    return [name.lower() for name in _unique(names)]


def _compact_offer_text(text: str) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    if len(cleaned) <= 420:
        return cleaned
    sentences = [part.strip() for part in cleaned.replace("?", ".").replace("!", ".").split(".") if part.strip()]
    priority = [
        sentence
        for sentence in sentences
        if any(
            marker in sentence.lower()
            for marker in (
                "agent engineering platform",
                "observe",
                "evaluate",
                "deploy",
                "traces",
                "platform",
                "framework",
                "assistant",
                "browser",
            )
        )
    ]
    selected = priority[:3] or sentences[:3]
    compact = ". ".join(selected).strip()
    compact = compact.replace("Get a demo ", "").strip()
    if " Observability Evaluation " in compact:
        compact = compact.split(" Observability Evaluation ", 1)[0].strip()
    if compact and not compact.endswith("."):
        compact += "."
    return compact[:420].rstrip()


def _claim_texts(
    claims: Iterable[EvidenceClaim],
    claim_types: tuple[str, ...],
    *,
    limit: int,
    reject_form_noise: bool = False,
) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for claim in claims:
        if claim.claim_type not in claim_types or not claim.text:
            continue
        if reject_form_noise and _looks_like_form_noise(claim.text):
            continue
        key = claim.text.lower()
        if key in seen:
            continue
        seen.add(key)
        values.append(claim.text)
        if len(values) >= limit:
            break
    return values


def _signal_texts(claims: Iterable[EvidenceClaim]) -> list[str]:
    texts: list[str] = []
    for claim in claims:
        if not claim.text or _looks_like_form_noise(claim.text):
            continue
        if claim.source_type.startswith("owned_") or claim.claim_type in {
            "hero_claim",
            "product_offer",
            "outcome",
            "personality",
            "values",
        } or (claim.claim_type == "feature_evidence" and not claim.source_url):
            texts.append(claim.text)
    return _unique(texts)


def _looks_like_form_noise(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in ("airtable", "form", "submit", "slack", "email"))


def _official_urls(graph: EvidenceGraph) -> list[str]:
    urls: list[str] = []
    for source in graph.sources.values():
        if source.source_type.startswith("owned_") and source.source_type != "owned_proof":
            urls.append(source.url)
    return _unique(urls)


def _confidence_notes(graph: EvidenceGraph) -> list[str]:
    notes = list(graph.run.notes)
    summary = graph.summary()
    notes.append(
        "EvidenceGraph summary: "
        f"{summary['source_count']} sources, {summary['claim_count']} claims, "
        f"{summary['noise_claim_count']} noise claims."
    )
    for warning in graph.warnings:
        notes.append(warning)
    return _unique(notes)


def _category_from_graph(
    graph: EvidenceGraph,
    *,
    offer: str = "",
    product_summary: str = "",
    company_summary: str = "",
) -> str:
    text = " ".join(part for part in (offer, product_summary, company_summary, graph.run.resolved_entity) if part).lower()
    if "agent engineering platform" in text:
        return "agent engineering platform"
    if "framework" in text and ("agent" in text or "llm" in text):
        return "llm application framework"
    if "platform" in text and ("agent" in text or "agents" in text):
        return "ai agent platform"
    if "platform" in text:
        return "platform"
    if "app builder" in text:
        return "AI app builder"
    if "ai assistant" in text or "assistant" in text:
        return "ai assistant"
    if "browser" in text or "tabs" in text or "workspaces" in text:
        return "browser"
    for claim in graph.claims:
        if claim.claim_type == "product_offer" and claim.text:
            text = claim.text.lower()
            if "platform" in text:
                return "platform"
            if "assistant" in text:
                return "ai assistant"
            if "browser" in text:
                return "browser"
            if "app" in text:
                return "application"
    if any(source.source_type == "competitor_context" for source in graph.sources.values()):
        return "market category"
    return ""


def _infer_outcome(texts: Iterable[str]) -> str:
    text = " ".join(str(item or "") for item in texts).lower()
    phrases: list[str] = []
    for marker in (
        "build and ship",
        "ship software",
        "ship apps",
        "life orchestration",
        "save time",
        "simplify",
        "streamline",
        "organize",
        "organized",
        "faster",
        "fast",
        "secure",
        "instant",
    ):
        if marker in text:
            phrases.append(marker)
    return "; ".join(_unique(phrases))


def _tone_summary(signals: list[str], fallback_texts: Iterable[str]) -> str:
    if signals:
        return ", ".join(signals[:3])
    fallback = _attribute_signals(fallback_texts)
    return ", ".join(_unique(fallback)[:3])


def _concept_signals(texts: Iterable[str]) -> list[str]:
    candidates: list[str] = []
    for text in texts:
        low = str(text or "").lower()
        for term in (
            "lab",
            "command center",
            "nature",
            "builder",
            "platform",
            "assistant",
            "browser",
            "workspace",
            "tabs",
            "studio",
            "system",
            "engine",
            "operating system",
        ):
            if term in low:
                candidates.append(term)
    return candidates


def _attribute_signals(texts: Iterable[str]) -> list[str]:
    candidates: list[str] = []
    for text in texts:
        low = str(text or "").lower()
        for term in (
            "clear",
            "practical",
            "direct",
            "simple",
            "fast",
            "secure",
            "transparent",
            "private",
            "technical",
            "minimal",
            "dense",
            "human",
            "playful",
            "premium",
            "focused",
            "structured",
            "organized",
        ):
            if term in low:
                candidates.append(term)
        if "organize" in low:
            candidates.append("organized")
    return candidates


def _evidence_gaps(
    *,
    graph: EvidenceGraph,
    offer: str,
    audience: str,
    outcome: str,
    mission: str,
    proof_points: list[ResearchEvidence],
    official_urls: list[str],
    company_summary: str,
    product_summary: str,
) -> list[str]:
    gaps = list(graph.gaps)
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
    return _unique(gaps)


def _primary_surface_role(graph: EvidenceGraph) -> str:
    for source in graph.sources.values():
        if source.url == graph.run.input_url and source.surface_role:
            return source.surface_role
    return "audited_surface"


def _primary_entity_scope(graph: EvidenceGraph) -> str:
    for source in graph.sources.values():
        if source.url == graph.run.input_url and source.entity_scope:
            return source.entity_scope
    return "audited_surface"


def _pack_entity_type(value: str) -> str:
    return value if value in {"company", "brand", "product", "sub_brand", "campaign", "content", "unknown"} else "unknown"


def _pack_source_type(value: str) -> str:
    return {
        "owned_home": "owned_official",
        "owned_about": "owned_about",
        "owned_product": "owned_product",
        "owned_pricing": "owned_product",
        "owned_security": "owned_security_trust",
        "owned_docs": "owned_product",
        "owned_proof": "proof_point",
        "press_founder": "press_or_founder",
        "third_party_review": "proof_point",
        "third_party_context": "press_or_founder",
        "social": "social",
        "competitor_context": "noise",
        "noise": "noise",
    }.get(value, "unknown")


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
