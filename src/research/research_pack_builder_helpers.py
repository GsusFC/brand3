"""Helper functions for building BrandResearchPack objects from graphs."""

from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from src.reports.brand_research_pack import ResearchEvidence
from src.reports.brand_research_pack_building_helpers import _looks_like_crypto_product
from src.research.evidence_graph import EvidenceClaim, EvidenceGraph
from src.research.research_pack_builder_text_preprocessing import _looks_like_url_only
from src.research.research_pack_builder_text_helpers import *  # noqa: F401,F403

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


def _competitive_context_evidence(graph: EvidenceGraph) -> list[ResearchEvidence]:
    items: list[ResearchEvidence] = []
    seen: set[str] = set()
    for source in graph.sources.values():
        if source.source_type != "competitor_context" or not source.url:
            continue
        key = source.url.lower()
        if key in seen:
            continue
        seen.add(key)
        label = source.title or source.label or source.url
        items.append(
            ResearchEvidence(
                text=f"Competitive context source: {label}",
                kind="context",
                source_url=source.url,
                source_type=_pack_source_type(source.source_type),
                source_label="competitive_context",
                surface_role=source.surface_role,
                entity_scope=source.entity_scope,
                topic="competitive_context",
                confidence="medium",
                notes=[
                    "Competitor context only; do not use as evidence of the audited brand's identity, offer, proof, or TLDR claims."
                ],
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
        and not _looks_like_url_only(claim.text)
        and _eligible_for_offer_candidate(claim)
        and _looks_like_offer(claim.text)
        and not _looks_like_extraction_artifact(claim.text)
        and not _looks_like_product_summary_noise(claim.text)
    ]
    if graph and _is_company_brand_graph(graph):
        candidates = _company_level_offer_candidates(candidates, graph)
    if not candidates:
        candidates = _owned_proof_offer_candidates(claim_list, graph=graph)
    if candidates:
        return _compact_offer_text(max(candidates, key=lambda claim: _offer_score(claim, graph=graph)).text)
    fallback = _first_clean_claim_text(claim_list, ("product_offer", "hero_claim", "outcome", "audience"))
    return _compact_offer_text(fallback)


def _looks_like_offer(text: str) -> bool:
    if _looks_like_url_only(text):
        return False
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
            "recommendation",
            "recommendations",
            "plan",
            "integration",
            "integrates",
            "dashboard",
            "shopping list",
        )
    )


def _eligible_for_offer_candidate(claim: EvidenceClaim) -> bool:
    if claim.claim_type != "feature_evidence":
        return True
    return bool(claim.source_url) and claim.source_type.startswith("owned_")


def _offer_score(claim: EvidenceClaim, *, graph: EvidenceGraph | None = None) -> int:
    low = claim.text.lower()
    score = {
        "mission": 26,
        "product_offer": 30,
        "hero_claim": 25,
        "audience": 20,
        "outcome": 10,
        "feature_evidence": 12,
        "proof": 14,
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
            ("recommendation", 14),
            ("recommendations", 14),
            ("plan", 12),
            ("integration", 12),
            ("integrates", 12),
            ("dashboard", 10),
            ("shopping list", 10),
        )
        if marker in low
    )
    if "mission" in low:
        score -= 25
    if "founder" in low or "founders" in low:
        score -= 5
    if _looks_like_extraction_artifact(claim.text):
        score -= 80
    if _looks_like_product_summary_noise(claim.text):
        score -= 45
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


def _looks_like_extraction_artifact(text: str) -> bool:
    cleaned = " ".join(str(text or "").split()).strip()
    low = cleaned.lower()
    if not cleaned:
        return True
    if low.startswith(("<loc>", "</loc>", "<lastmod>", "</url>", "urlset ")):
        return True
    return any(
        marker in low
        for marker in (
            "skip to main content",
            "search... ",
            "search...\u2318",
            "api playground",
            "ask assistant",
            "\u2318 k",
            "ctrl k",
            "main content parallel home page",
            "privacy policy terms",
        )
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


def _owned_proof_offer_candidates(
    claims: Iterable[EvidenceClaim],
    *,
    graph: EvidenceGraph | None = None,
) -> list[EvidenceClaim]:
    candidates = [
        claim
        for claim in claims
        if claim.claim_type == "proof"
        and claim.text
        and claim.source_type in {"owned_home", "owned_about", "owned_product", "owned_proof"}
        and claim.surface_role
        in {"audited_surface", "owned_surface", "parent_home", "product_surface", "product_system"}
        and {"value_proposition", "magnetism"}.intersection(set(claim.supports_blocks or []))
        and _looks_like_offer(claim.text)
        and not _looks_like_extraction_artifact(claim.text)
        and not _looks_like_product_summary_noise(claim.text)
    ]
    if graph and _is_company_brand_graph(graph):
        return _company_level_offer_candidates(candidates, graph) or candidates
    return candidates


def _company_summary_text(claims: Iterable[EvidenceClaim], *, graph: EvidenceGraph) -> str:
    claim_list = list(claims)
    preferred = [
        claim
        for claim in claim_list
        if claim.claim_type in {"mission", "hero_claim", "product_offer", "outcome"}
        and claim.text
        and _is_company_scoped_claim(claim)
        and not _product_specific_without_parent(claim, graph)
        and not _looks_like_extraction_artifact(claim.text)
        and not _looks_like_product_summary_noise(claim.text)
    ]
    if preferred:
        return _normalize_research_pack_text(max(preferred, key=lambda claim: _offer_score(claim, graph=graph)).text)
    return _normalize_research_pack_text(_first_clean_claim_text(claim_list, ("mission", "hero_claim", "product_offer")))


def _product_summary_text(claims: Iterable[EvidenceClaim]) -> str:
    claim_list = list(claims)
    for claim in claim_list:
        if (
            claim.claim_type in {"product_offer", "feature_evidence", "outcome", "audience", "hero_claim"}
            and claim.text
            and not _looks_like_url_only(claim.text)
            and _is_product_scoped_claim(claim)
            and not _looks_like_extraction_artifact(claim.text)
            and not _looks_like_product_summary_noise(claim.text)
            and not _looks_like_audience_noise(claim.text)
        ):
            return _normalize_research_pack_text(claim.text)
    owned_proof = _owned_proof_offer_candidates(claim_list)
    if owned_proof:
        return _normalize_research_pack_text(max(owned_proof, key=lambda claim: _offer_score(claim)).text)
    return ""


__all__ = [name for name in globals() if name.startswith("_")]
