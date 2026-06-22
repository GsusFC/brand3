"""Text and metadata heuristics for BrandResearchPack building."""

from __future__ import annotations

from collections.abc import Iterable

from src.reports.brand_research_pack import ResearchEvidence
from src.reports.brand_research_pack_building_helpers import _looks_like_crypto_product
from src.research.evidence_graph import EvidenceClaim, EvidenceGraph
from src.research.research_pack_builder_text_preprocessing import (
    _audience_text,
    _clean_offer_sentence,
    _compact_offer_text,
    _infer_audience_from_texts,
    _join_offer_sentences,
    _looks_like_audience_noise,
    _looks_like_extraction_artifact,
    _looks_like_integration_title_audience,
    _looks_like_language_selector_fragment,
    _looks_like_product_summary_noise,
    _looks_like_url_only,
    _normalize_research_pack_text,
    _offer_sentence_score,
    _strip_offer_cta_tail,
)


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


def _first_clean_claim_text(claims: Iterable[EvidenceClaim], claim_types: tuple[str, ...]) -> str:
    for claim_type in claim_types:
        for claim in claims:
            if (
                claim.claim_type == claim_type
                and claim.text
                and not _looks_like_extraction_artifact(claim.text)
                and not _looks_like_product_summary_noise(claim.text)
                and not _looks_like_audience_noise(claim.text)
            ):
                return claim.text
    return ""


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
    if _looks_like_crypto_product(text):
        return "crypto product"
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
        "competitor_context": "competitive_context",
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


__all__ = [name for name in globals() if name.startswith("_")]
