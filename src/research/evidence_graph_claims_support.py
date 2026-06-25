"""Claim heuristics and dedupe helpers for EvidenceGraph."""

from __future__ import annotations

import hashlib

from src.research.evidence_graph import EvidenceClaim
from src.research.evidence_graph_sources import ResearchSource, _normalize_url, _unique


def _claim_family(claim: EvidenceClaim) -> str:
    return claim.claim_type or "unknown"


def _claim_fingerprint(claim: EvidenceClaim) -> str:
    text = " ".join((claim.text or claim.quote or "").lower().split())
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16] if text else ""


def _preferred_claim(left: EvidenceClaim, right: EvidenceClaim) -> tuple[EvidenceClaim, EvidenceClaim]:
    return (left, right) if _claim_priority(left) <= _claim_priority(right) else (right, left)


def _claim_priority(claim: EvidenceClaim) -> tuple[int, int, int]:
    source_rank = {
        "owned_home": 0,
        "owned_about": 1,
        "owned_product": 2,
        "owned_pricing": 3,
        "owned_security": 4,
        "owned_docs": 5,
        "owned_proof": 6,
        "social": 7,
        "press_founder": 8,
        "third_party_review": 9,
        "third_party_context": 10,
        "competitor_context": 11,
        "noise": 12,
        "unknown": 13,
    }.get(claim.source_type, 13)
    confidence_rank = {"high": 0, "medium": 1, "low": 2}.get((claim.confidence or "").lower(), 3)
    return (source_rank, confidence_rank, -len(claim.text or ""))


def _claim_id(claim_type: str, text: str, source_id: str) -> str:
    raw = "|".join([claim_type, source_id, text])
    return f"claim_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def _is_entity_boundary_quarantined_source(source: ResearchSource) -> bool:
    return source.source_type == "noise" and any(
        str(note).startswith("entity_boundary_collision") for note in source.notes
    )


def _merge_duplicate_claim(
    primary: EvidenceClaim,
    duplicate: EvidenceClaim,
    *,
    sources: dict[str, ResearchSource],
) -> EvidenceClaim:
    duplicate_source = sources.get(duplicate.source_id)
    duplicate_origin = duplicate_source.origin if duplicate_source else ""
    return EvidenceClaim(
        claim_id=primary.claim_id,
        text=primary.text,
        claim_type=primary.claim_type,
        quote=primary.quote,
        source_id=primary.source_id,
        source_url=primary.source_url,
        source_type=primary.source_type,
        surface_role=primary.surface_role,
        entity_scope=primary.entity_scope,
        confidence=primary.confidence,
        freshness_days=primary.freshness_days,
        supports_blocks=_unique(primary.supports_blocks + duplicate.supports_blocks),
        contradicts=_unique(primary.contradicts + duplicate.contradicts),
        secondary_source_ids=_unique(
            primary.secondary_source_ids
            + ([duplicate.source_id] if duplicate.source_id and duplicate.source_id != primary.source_id else [])
            + duplicate.secondary_source_ids
        ),
        secondary_source_urls=_unique(
            primary.secondary_source_urls
            + ([duplicate.source_url] if duplicate.source_url and duplicate.source_url != primary.source_url else [])
            + duplicate.secondary_source_urls
        ),
        secondary_origins=_unique(
            primary.secondary_origins
            + ([duplicate_origin] if duplicate_origin else [])
            + duplicate.secondary_origins
        ),
        noise_reason=primary.noise_reason or duplicate.noise_reason,
        notes=_unique(primary.notes + duplicate.notes + ["deduped_multi_source_evidence"]),
    )


def _claim_type_for_external_source(source_type: str, text: str) -> str:
    low = text.lower()
    if source_type == "press_founder" or any(marker in low for marker in ("founder", "interview", "launch", "raises", "funding", "acquired")):
        return "founder_press"
    if source_type == "third_party_review" or any(marker in low for marker in ("review", "customer", "testimonial", "case study")):
        return "proof"
    if source_type == "competitor_context":
        return "unknown"
    return "unknown"


def _blocks_for_external_claim_type(claim_type: str) -> list[str]:
    if claim_type == "founder_press":
        return ["brand_idea", "mission", "vision"]
    if claim_type == "proof":
        return ["value_proposition", "magnetism"]
    return []


def _recovered_claim_type(text: str, reason: str) -> str:
    if reason not in {"low_strategic_signal", "duplicate"}:
        return ""
    low = text.lower()
    if not low.strip() or _looks_like_form_or_chrome(low):
        return ""
    if any(marker in low for marker in ("smarter way", "new home for your internet", "fresh take")):
        return "hero_claim"
    if any(
        marker in low
        for marker in (
            "browser",
            "tabs",
            "workspaces",
            "split screen",
            "search your internet",
            "ask anything",
            "answers in context",
            "airis",
        )
    ):
        return "product_offer"
    if any(marker in low for marker in ("organize", "flow through", "work smarter", "multitasking", "easier", "faster")):
        return "outcome"
    return ""


def _blocks_for_recovered_claim_type(claim_type: str) -> list[str]:
    return {
        "hero_claim": ["magnetism", "brand_idea"],
        "product_offer": ["value_proposition", "brand_idea"],
        "outcome": ["core_purpose", "value_proposition"],
    }.get(claim_type, [])


def _looks_like_form_or_chrome(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "download free",
            "download started",
            "click here",
            "email below",
            "submit",
            "continue without accepting",
            "privacy policy",
            "terms",
            "copyright",
            "©",
            "in 2022",
            "recap",
            "year in review",
            "blog",
            "what should we call you",
            "how can we reach you",
            "slack",
            "wrong answers",
            "sitemap.xml",
            "robots.txt",
            "key pages found",
            "local image analysis",
            "whitespace ratio",
        )
    )


def _dedupe_claims(
    claims: list[EvidenceClaim],
    *,
    sources: dict[str, ResearchSource],
) -> tuple[list[EvidenceClaim], dict[str, int | float]]:
    deduped: list[EvidenceClaim] = []
    seen: dict[tuple[str, str, str], int] = {}
    duplicate_count = 0
    for claim in claims:
        key = (
            _normalize_url(claim.source_url),
            _claim_family(claim),
            _claim_fingerprint(claim),
        )
        if not any(key):
            deduped.append(claim)
            continue
        existing_index = seen.get(key)
        if existing_index is None:
            seen[key] = len(deduped)
            deduped.append(claim)
            continue
        duplicate_count += 1
        winner, duplicate = _preferred_claim(deduped[existing_index], claim)
        merged = _merge_duplicate_claim(winner, duplicate, sources=sources)
        deduped[existing_index] = merged
    total = len(claims)
    dedupe_rate = float(duplicate_count / total) if total else 0.0
    return deduped, {
        "input_claim_count": total,
        "deduped_claim_count": len(deduped),
        "duplicate_claim_count": duplicate_count,
        "dedupe_rate": round(dedupe_rate, 4),
    }
