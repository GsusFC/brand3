from __future__ import annotations

from typing import Any

from src.reports.derivation import collect_evidences
from src.reports.strategic_evidence_packet import StrategicEvidenceLine, build_strategic_evidence_packet
from src.research.evidence_graph_impl import ALLOWED_CLAIM_TYPES, EvidenceClaim
from src.research.evidence_graph_sources import ResearchSource, _dict, _normalize_url, _source_id, _unique
from src.research.evidence_graph_support import _clean, _is_entity_boundary_quarantined_source, _snapshot_web_url
from src.research.evidence_graph_claims_support import (
    _blocks_for_external_claim_type,
    _blocks_for_recovered_claim_type,
    _claim_family,
    _claim_fingerprint,
    _claim_id,
    _claim_priority,
    _claim_type_for_external_source,
    _dedupe_claims,
    _looks_like_form_or_chrome,
    _merge_duplicate_claim,
    _preferred_claim,
    _recovered_claim_type,
)


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
