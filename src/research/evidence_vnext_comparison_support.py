"""Private helper support for evidence vNext comparisons."""

from __future__ import annotations

from typing import Any

from src.research.evidence_graph import EvidenceClaim


def _compare_field(field: str, current_value: Any, vnext_value: Any):
    from src.research.pack_comparison import FieldComparison

    current_normalized = _normalize_value(current_value)
    vnext_normalized = _normalize_value(vnext_value)
    return FieldComparison(
        field=field,
        legacy_empty=not bool(current_normalized),
        graph_empty=not bool(vnext_normalized),
        changed=current_normalized != vnext_normalized,
        legacy_preview=_preview(current_value),
        graph_preview=_preview(vnext_value),
    )


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split()).strip()
    if isinstance(value, list):
        return "\n".join(_normalize_value(item) for item in value if _normalize_value(item))
    if isinstance(value, dict):
        return " ".join(str(value.get(key) or "") for key in sorted(value))
    return str(value).strip()


def _preview(value: Any, limit: int = 180) -> str:
    if isinstance(value, list):
        parts = []
        for item in value[:3]:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("source_url") or item)[:80])
            else:
                parts.append(str(item)[:80])
        text = " | ".join(parts)
    elif isinstance(value, dict):
        text = str(value)
    else:
        text = str(value or "")
    return " ".join(text.split())[:limit]


def _reclassified_to_noise_count(claims: list[EvidenceClaim]) -> int:
    return sum(
        1
        for claim in claims
        if claim.claim_type == "noise"
        and any("Rejected by evidence vNext gate." == note for note in claim.notes)
    )


def _scorecard_status(
    *,
    material_lost: list[str],
    non_material_lost: list[str],
    review_count: int,
    rejected_count: int,
) -> dict[str, Any]:
    reason_codes: list[str] = []
    if material_lost:
        reason_codes.append("material_fields_lost")
    if non_material_lost:
        reason_codes.append("non_material_fields_lost")
    if review_count:
        reason_codes.append("review_required_evidence_present")
    if rejected_count:
        reason_codes.append("rejected_evidence_present")

    if material_lost:
        status = "blocked"
    elif non_material_lost or review_count:
        status = "review_required"
    else:
        status = "promising"

    return {
        "status": status,
        "reason_codes": reason_codes or ["no_material_regressions_detected"],
        "material_lost_fields": list(material_lost),
        "non_material_lost_fields": list(non_material_lost),
    }


def _preview_looks_nonmaterial(value: str) -> bool:
    low = str(value or "").lower()
    return any(
        marker in low
        for marker in (
            "robots.txt",
            "sitemap.xml",
            "local image analysis",
            "whitespace ratio",
            "dominant color",
            "contrast signal",
            "schema.org",
            "key pages found",
        )
    )


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text_key(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _url_key(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _filter_claims(claims: list[EvidenceClaim], gate) -> list[EvidenceClaim]:
    accepted_url_keys = {_url_key(item.url) for item in gate.accepted if item.url}
    unresolved_profile_url_keys = {
        _url_key(item.url)
        for item in gate.review_required
        if item.url and item.classification_reason == "same_name_external_profile_not_alias"
    }
    review_or_rejected_url_keys = {
        _url_key(item.url)
        for item in (*gate.review_required, *gate.rejected)
        if item.url
    }
    accepted_text_keys = {_text_key(item.text) for item in gate.accepted if item.text}
    accepted_url_by_text_key = {
        _text_key(item.text): item.url
        for item in gate.accepted
        if item.text and item.url
    }
    review_or_rejected_text_keys = {
        _text_key(item.text)
        for item in (*gate.review_required, *gate.rejected)
        if item.text
    }
    filtered: list[EvidenceClaim] = []
    for claim in claims:
        claim = _claim_with_inferred_url(claim, accepted_url_by_text_key)
        if _claim_rejected_by_gate(
            claim,
            accepted_url_keys=accepted_url_keys,
            unresolved_profile_url_keys=unresolved_profile_url_keys,
            review_or_rejected_url_keys=review_or_rejected_url_keys,
            accepted_text_keys=accepted_text_keys,
            review_or_rejected_text_keys=review_or_rejected_text_keys,
        ):
            filtered.append(
                EvidenceClaim(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type="noise",
                    quote=claim.quote,
                    source_id=claim.source_id,
                    source_url=claim.source_url,
                    source_type="noise",
                    surface_role=claim.surface_role,
                    entity_scope=claim.entity_scope,
                    confidence="low",
                    noise_reason=claim.noise_reason or _claim_noise_reason(claim, unresolved_profile_url_keys),
                    notes=_unique(
                        list(claim.notes)
                        + [_claim_noise_note(claim, unresolved_profile_url_keys)]
                    ),
                )
            )
            continue
        filtered.append(claim)
    return filtered


def _claim_with_inferred_url(claim: EvidenceClaim, accepted_url_by_text_key: dict[str, str]) -> EvidenceClaim:
    if claim.source_url:
        return claim
    inferred_url = accepted_url_by_text_key.get(_text_key(claim.text or claim.quote))
    if not inferred_url:
        return claim
    return EvidenceClaim(
        claim_id=claim.claim_id,
        text=claim.text,
        claim_type=claim.claim_type,
        quote=claim.quote,
        source_id=claim.source_id,
        source_url=inferred_url,
        source_type=claim.source_type,
        surface_role=claim.surface_role,
        entity_scope=claim.entity_scope,
        confidence=claim.confidence,
        freshness_days=claim.freshness_days,
        supports_blocks=list(claim.supports_blocks),
        contradicts=list(claim.contradicts),
        secondary_source_ids=list(claim.secondary_source_ids),
        secondary_source_urls=list(claim.secondary_source_urls),
        secondary_origins=list(claim.secondary_origins),
        noise_reason=claim.noise_reason,
        notes=_unique(list(claim.notes) + ["Source URL inferred by evidence vNext from same feature evidence_url."]),
    )


def _claim_rejected_by_gate(
    claim: EvidenceClaim,
    *,
    accepted_url_keys: set[str],
    unresolved_profile_url_keys: set[str],
    review_or_rejected_url_keys: set[str],
    accepted_text_keys: set[str],
    review_or_rejected_text_keys: set[str],
) -> bool:
    if claim.claim_type == "noise" or claim.source_type == "noise":
        return False
    claim_url_key = _url_key(claim.source_url)
    claim_text_key = _text_key(claim.text or claim.quote)

    if claim.source_type.startswith("owned_") and claim.claim_type != "feature_evidence":
        return False
    if claim.claim_type == "feature_evidence" and not claim.source_url:
        return True
    if claim_url_key and claim_url_key in unresolved_profile_url_keys:
        return True
    if claim_url_key and claim_url_key in accepted_url_keys:
        return False
    if claim_text_key and claim_text_key in accepted_text_keys:
        return False
    if claim_url_key and claim_url_key in review_or_rejected_url_keys:
        return True
    if claim_text_key and claim_text_key in review_or_rejected_text_keys:
        return True
    if claim.source_type in {"unknown", "third_party_context", "third_party_review", "press_founder"}:
        return claim.claim_type in {"unknown", "feature_evidence"} and not claim.source_url
    return False


def _claim_noise_reason(claim: EvidenceClaim, unresolved_profile_url_keys: set[str]) -> str:
    if _url_key(claim.source_url) in unresolved_profile_url_keys:
        return "unresolved_external_profile_source"
    return "evidence_vnext_gate_rejected"


def _claim_noise_note(claim: EvidenceClaim, unresolved_profile_url_keys: set[str]) -> str:
    if _url_key(claim.source_url) in unresolved_profile_url_keys:
        return "Quarantined by evidence vNext because source URL is an unresolved same-name external profile."
    return "Rejected by evidence vNext gate."


def _vnext_gaps(gate, claims: list[EvidenceClaim]) -> list[str]:
    gaps: list[str] = []
    if gate.review_required:
        gaps.append("Evidence vNext found review-required evidence; excluded from vNext interpretation.")
    if gate.rejected and not any(claim.claim_type != "noise" for claim in claims):
        gaps.append("Evidence vNext rejected all interpretation candidates.")
    return gaps


def _vnext_warnings(gate) -> list[str]:
    warnings: list[str] = []
    if gate.review_required:
        warnings.append("evidence_vnext_review_required")
    if gate.rejected:
        warnings.append("evidence_vnext_rejected_candidates")
    return warnings
