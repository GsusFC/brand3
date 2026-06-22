from __future__ import annotations

from typing import Any
import hashlib
import re

from src.reports.derivation import collect_evidences
from src.reports.strategic_evidence_packet import StrategicEvidenceLine, build_strategic_evidence_packet
from src.research.evidence_graph import ALLOWED_CLAIM_TYPES, EvidenceClaim
from src.research.evidence_graph_sources import ResearchSource, _dict, _normalize_url, _source_id, _unique
from src.research.evidence_graph_support import _clean, _is_entity_boundary_quarantined_source, _snapshot_web_url


_GROUP_TO_CLAIM_TYPE = {
    "hero_claims": "hero_claim",
    "product_offer": "product_offer",
    "audience": "audience",
    "outcome": "outcome",
    "mission_language": "mission",
    "vision_language": "vision",
    "values_language": "values",
    "personality_tone": "personality",
    "proof_points": "proof",
    "third_party_context": "founder_press",
}

_GROUP_TO_BLOCKS = {
    "hero_claims": ["magnetism", "brand_idea"],
    "product_offer": ["value_proposition", "brand_idea"],
    "audience": ["value_proposition"],
    "outcome": ["core_purpose", "value_proposition"],
    "mission_language": ["core_purpose", "mission"],
    "vision_language": ["vision"],
    "values_language": ["values", "attributes"],
    "personality_tone": ["personality", "attributes"],
    "proof_points": ["value_proposition", "magnetism"],
    "third_party_context": ["brand_idea", "mission", "vision"],
}


def build_claims_from_snapshot(
    snapshot: dict[str, Any],
    *,
    sources: dict[str, ResearchSource],
    strategic_packet,
) -> tuple[list[EvidenceClaim], dict[str, Any]]:
    claims = _build_claims(snapshot, sources=sources, strategic_packet=strategic_packet)
    return _dedupe_claims(claims, sources=sources)


def _build_claims(snapshot: dict[str, Any], *, sources: dict[str, ResearchSource], strategic_packet) -> list[EvidenceClaim]:
    claims: list[EvidenceClaim] = []
    seen: set[tuple[str, str, str]] = set()

    def add(
        text: str,
        *,
        claim_type: str,
        source_url: str = "",
        quote: str = "",
        confidence: str = "",
        supports_blocks: list[str] | None = None,
        noise_reason: str = "",
        notes: list[str] | None = None,
        surface_role: str = "",
        entity_scope: str = "",
    ) -> None:
        cleaned = _clean(text)
        source_url_norm = _normalize_url(source_url)
        if not cleaned and not source_url_norm:
            return
        source_id = _source_id(source_url_norm) if source_url_norm else ""
        source = sources.get(source_id)
        source_type = source.source_type if source else ("noise" if claim_type == "noise" else "unknown")
        if source and _is_entity_boundary_quarantined_source(source) and claim_type != "noise":
            claim_type = "noise"
            supports_blocks = []
            noise_reason = noise_reason or "entity_boundary_collision"
            notes = _unique(
                (notes or [])
                + [
                    "Quarantined from TLDR input because the external source appears to reference a near-name entity."
                ]
            )
        key = (cleaned.lower(), source_id, claim_type)
        if key in seen:
            return
        seen.add(key)
        claims.append(
            EvidenceClaim(
                claim_id=_claim_id(claim_type, cleaned, source_id),
                text=cleaned,
                claim_type=claim_type if claim_type in ALLOWED_CLAIM_TYPES else "unknown",
                quote=quote or cleaned,
                source_id=source_id,
                source_url=source_url_norm,
                source_type=source_type,
                surface_role=surface_role or (source.surface_role if source else ""),
                entity_scope=entity_scope or (source.entity_scope if source else ""),
                confidence=confidence or ("high" if source_url_norm and claim_type != "noise" else "low"),
                supports_blocks=_unique(supports_blocks or []),
                noise_reason=noise_reason,
                notes=_unique(notes or []),
            )
        )

    for group, lines in strategic_packet.groups.items():
        claim_type = _GROUP_TO_CLAIM_TYPE.get(group, "unknown")
        supports_blocks = _GROUP_TO_BLOCKS.get(group, [])
        for line in lines:
            if not isinstance(line, StrategicEvidenceLine):
                continue
            add(
                line.text,
                claim_type=claim_type,
                source_url=str(line.url or ""),
                confidence="high" if line.url else "medium",
                supports_blocks=supports_blocks,
                notes=[f"Strategic evidence group: {group}."],
                surface_role=str(line.surface_role or ""),
                entity_scope=str(line.entity_scope or ""),
            )

    for evidence in collect_evidences(snapshot):
        add(
            str(evidence.quote or evidence.url or ""),
            claim_type="feature_evidence",
            source_url=str(evidence.url or ""),
            confidence="medium",
            notes=[f"Feature evidence: {evidence.dimension}/{evidence.feature_name}."],
        )

    for raw_input in snapshot.get("raw_inputs") or []:
        if raw_input.get("source") != "exa":
            continue
        payload = _dict(raw_input.get("payload"))
        for collection in ("news", "mentions", "ai_visibility_results"):
            for item in payload.get(collection) or []:
                if not isinstance(item, dict):
                    continue
                text = _clean(
                    " ".join(
                        part
                        for part in [
                            str(item.get("title") or ""),
                            str(item.get("summary") or ""),
                            str(item.get("text") or ""),
                        ]
                        if part.strip()
                    )
                )
                url = str(item.get("url") or "")
                if not text or not url:
                    continue
                source = sources.get(_source_id(_normalize_url(url)))
                claim_type = _claim_type_for_external_source(source.source_type if source else "unknown", text)
                add(
                    text,
                    claim_type=claim_type,
                    source_url=url,
                    confidence="medium",
                    supports_blocks=_blocks_for_external_claim_type(claim_type),
                    notes=[f"Supplemental external evidence from raw_inputs.exa.{collection}."],
                )

    web_url = _snapshot_web_url(snapshot)
    for item in strategic_packet.rejected:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "")
        recovered_type = _recovered_claim_type(text, str(item.get("reason") or ""))
        if recovered_type:
            add(
                text,
                claim_type=recovered_type,
                source_url=web_url,
                confidence="medium",
                supports_blocks=_blocks_for_recovered_claim_type(recovered_type),
                notes=["Recovered from low-signal strategic packet rejection for EvidenceGraph review."],
            )
        add(
            text,
            claim_type="noise",
            source_url=web_url,
            confidence="low",
            noise_reason=str(item.get("reason") or "rejected_by_strategic_packet"),
            notes=["Rejected while grouping strategic evidence."],
        )

    return sorted(claims, key=lambda claim: (claim.claim_type, claim.source_url, claim.text))


def _dedupe_claims(
    claims: list[EvidenceClaim],
    *,
    sources: dict[str, ResearchSource],
) -> tuple[list[EvidenceClaim], dict[str, Any]]:
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
