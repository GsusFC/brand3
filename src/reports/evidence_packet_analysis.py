"""Classification helpers for Evidence Packet v0."""

from __future__ import annotations

from src.reports.evidence_packet_analysis_support import (
    BROAD_MARKET_NOISE_MARKERS,
    MARKETPLACE_HOST_MARKERS,
    OWNED_CLAIM_MARKERS,
    REPOSITORY_HOST_MARKERS,
    TECHNICAL_FEATURE_MARKERS,
    TECHNICAL_PATH_MARKERS,
    TRUST_SECURITY_HOST_MARKERS,
    USAGE_CLAIM_MARKERS,
    VISUAL_FEATURE_MARKERS,
    _dedupe,
    _first_url,
    _host,
    _is_http_url,
    _is_marketplace,
    _is_noise,
    _is_repository,
    _is_same_name_different_root,
    _is_same_name_external_profile,
    _is_technical,
    _is_trust_security,
    _is_usage_or_traction_claim,
    _is_visual_internal,
    _looks_like_owned_claim,
    _parse_raw_value,
    _root_domain,
)


def _build_exa_url_metadata(snapshot: dict) -> dict[str, dict]:
    metadata: dict[str, dict] = {}
    for item in snapshot.get("raw_inputs") or []:
        if str(item.get("source") or "") != "exa":
            continue
        payload = item.get("payload") if isinstance(item, dict) else None
        if not isinstance(payload, dict):
            continue
        for field in ("mentions", "news", "competitors", "ai_visibility_results"):
            entries = payload.get(field)
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                url = str(entry.get("url") or "").strip()
                if not url:
                    continue
                existing = metadata.get(url)
                candidate = {
                    "source_class": str(entry.get("source_class") or ""),
                    "relation": str(entry.get("relation") or ""),
                    "classification_reason": str(entry.get("classification_reason") or ""),
                    "requires_human_review": bool(entry.get("requires_human_review")),
                }
                if not existing:
                    metadata[url] = candidate
                    continue
                if _exa_meta_priority(candidate) > _exa_meta_priority(existing):
                    metadata[url] = candidate
    return metadata


def _exa_meta_priority(meta: dict) -> int:
    source_class = str(meta.get("source_class") or "")
    if source_class == "noise":
        return 100
    if source_class == "related_unresolved":
        return 90
    if source_class == "marketplace_listing":
        return 80
    if source_class == "technical_internal":
        return 70
    if source_class == "owned":
        return 50
    if source_class == "external":
        return 40
    return 10


def _classify_candidate(
    candidate: dict,
    *,
    audit_host: str,
    audit_root: str,
    exa_url_metadata: dict[str, dict] | None = None,
) -> dict:
    url = str(candidate.get("url") or "").strip()
    text = str(candidate.get("text") or "").strip()
    host = _host(url)
    root = _root_domain(host)
    feature_name = str(candidate.get("feature_name") or "").lower()
    feature_source = str(candidate.get("feature_source") or "").lower()
    raw_key = str(candidate.get("raw_key") or "").lower()
    haystack = " ".join([text, url, feature_name, feature_source, raw_key]).lower()

    source_class = "external_third_party"
    eligibility = "eligible_for_narrative_finding"
    reason = "source_classified_external_candidate"

    if feature_source == "competitor_web_comparison" and raw_key.startswith("competitor_"):
        source_class = "competitor_comparison"
        eligibility = "eligible_for_narrative_finding"
        reason = "bounded_competitor_comparison_snapshot"
    elif _is_visual_internal(feature_name, feature_source, raw_key, haystack):
        source_class = "visual_internal_metric"
        eligibility = "technical_only"
        reason = "visual_or_internal_analysis_not_market_evidence"
    elif _is_technical(feature_name, feature_source, raw_key, haystack, url):
        source_class = "technical_internal"
        eligibility = "technical_only"
        reason = "technical_context_not_brand_narrative_evidence"
    elif _is_trust_security(host, haystack):
        source_class = "trust_security"
        eligibility = "trust_security_review_only"
        reason = "trust_or_security_source_requires_review"
    elif _is_repository(host):
        source_class = "repository"
        eligibility = "observation_only"
        reason = "repository_activity_not_adoption"
    elif _is_marketplace(host):
        source_class = "marketplace_listing"
        eligibility = "requires_human_review"
        reason = "marketplace_listing_not_automatic_external_validation"
    elif _is_noise(haystack):
        source_class = "noise"
        eligibility = "reject_noise"
        reason = "off_topic_or_broad_market_noise"
    elif _is_same_name_external_profile(text, url, audit_host, audit_root):
        source_class = "related_unresolved"
        eligibility = "requires_human_review"
        reason = "same_name_external_profile_not_alias"
    elif raw_key == "platforms" or "social" in feature_name or "social" in feature_source:
        source_class = "external_third_party"
        eligibility = "observation_only"
        reason = "social_profile_candidate_not_external_validation"
    elif host and host == audit_host:
        source_class = "audited_surface"
        eligibility = "observation_only" if _looks_like_owned_claim(candidate) else "eligible_for_narrative_finding"
        reason = "audited_surface_evidence"
    elif host and root and root == audit_root:
        source_class = "owned_surface"
        eligibility = "observation_only"
        reason = "same_root_or_subdomain_not_external_validation"
    elif _is_same_name_different_root(host, audit_host, root, audit_root):
        source_class = "related_unresolved"
        eligibility = "requires_human_review"
        reason = "same_name_different_root_not_alias"
    elif not url and _looks_like_owned_claim(candidate):
        source_class = "owned_surface"
        eligibility = "observation_only"
        reason = "owned_claim_without_url"
    elif not url:
        source_class = "external_third_party"
        eligibility = "requires_human_review"
        reason = "missing_evidence_url"

    if not url and eligibility == "eligible_for_narrative_finding":
        eligibility = "requires_human_review"
        reason = "missing_evidence_url"
    if not text and eligibility == "eligible_for_narrative_finding":
        eligibility = "blocked_empty_text"
        reason = "empty_text_evidence_blocked"
    if _is_usage_or_traction_claim(haystack) and source_class in {"audited_surface", "owned_surface"}:
        eligibility = "observation_only"
        reason = "owned_usage_or_traction_claim_requires_independent_support"

    exa_meta = (exa_url_metadata or {}).get(url) if url else None
    source_class, eligibility, reason = _apply_exa_metadata_hints(
        source_class=source_class,
        eligibility=eligibility,
        reason=reason,
        exa_meta=exa_meta,
        host=host,
        root=root,
        audit_host=audit_host,
        audit_root=audit_root,
    )

    return {
        **candidate,
        "host": host,
        "root_domain": root,
        "source_class": source_class,
        "eligibility": eligibility,
        "classification_reason": reason,
    }


def _apply_exa_metadata_hints(
    *,
    source_class: str,
    eligibility: str,
    reason: str,
    exa_meta: dict | None,
    host: str,
    root: str,
    audit_host: str,
    audit_root: str,
) -> tuple[str, str, str]:
    if not exa_meta:
        return source_class, eligibility, reason

    mapped_class = _map_exa_source_class_to_packet(
        exa_source_class=str(exa_meta.get("source_class") or ""),
        exa_relation=str(exa_meta.get("relation") or ""),
        host=host,
        root=root,
        audit_host=audit_host,
        audit_root=audit_root,
    )
    mapped_review = bool(exa_meta.get("requires_human_review"))
    mapped_reason = str(exa_meta.get("classification_reason") or "").strip()

    if mapped_class in {"noise", "technical_internal", "marketplace_listing", "related_unresolved"}:
        source_class = mapped_class
    elif mapped_class in {"audited_surface", "owned_surface"} and source_class not in {
        "trust_security",
        "technical_internal",
        "visual_internal_metric",
        "noise",
        "related_unresolved",
        "marketplace_listing",
    }:
        source_class = mapped_class
    elif mapped_class == "external_third_party" and source_class in {"external_third_party", "repository"}:
        source_class = mapped_class

    if mapped_class == "related_unresolved":
        eligibility = "requires_human_review"
        reason = mapped_reason or "exa_related_surface_unresolved"
    elif mapped_class == "marketplace_listing":
        eligibility = "requires_human_review"
        reason = mapped_reason or "exa_marketplace_listing_review_gated"
    elif mapped_class == "technical_internal":
        eligibility = "technical_only"
        reason = mapped_reason or "exa_technical_internal_signal"
    elif mapped_class == "noise":
        eligibility = "reject_noise"
        reason = mapped_reason or "exa_noise_source"
    elif mapped_review and eligibility == "eligible_for_narrative_finding":
        eligibility = "requires_human_review"
        reason = mapped_reason or "exa_requires_human_review"

    return source_class, eligibility, reason


def _map_exa_source_class_to_packet(
    *,
    exa_source_class: str,
    exa_relation: str,
    host: str,
    root: str,
    audit_host: str,
    audit_root: str,
) -> str:
    base = exa_source_class.strip().lower()
    relation = exa_relation.strip().lower()

    if base == "owned":
        if relation == "audited_surface" or host == audit_host:
            return "audited_surface"
        if relation == "same_root_surface" or (root and root == audit_root):
            return "owned_surface"
        return "owned_surface"
    if base == "external":
        return "external_third_party"
    if base == "related_unresolved":
        return "related_unresolved"
    if base == "marketplace_listing":
        return "marketplace_listing"
    if base == "technical_internal":
        return "technical_internal"
    if base == "noise":
        return "noise"
    return ""
