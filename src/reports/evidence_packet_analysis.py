"""Classification helpers for Evidence Packet v0."""

from __future__ import annotations

import ast
import json
from typing import Any
from urllib.parse import urlparse


TRUST_SECURITY_HOST_MARKERS = (
    "scamadviser",
    "joesandbox",
    "any.run",
    "blacklist",
    "virustotal",
    "urlscan",
    "malware",
    "phish",
    "threat",
    "abuse",
)

TECHNICAL_PATH_MARKERS = (
    "robots.txt",
    "sitemap",
    "llms.txt",
    "schema",
    "whois",
    "dns",
)

TECHNICAL_FEATURE_MARKERS = (
    "context",
    "site_structure",
    "context_readiness",
    "activity_surface",
    "review_surface",
    "structured_identity",
    "content_depth_signal",
)

VISUAL_FEATURE_MARKERS = (
    "visual",
    "screenshot",
    "color",
    "contrast",
    "whitespace",
    "typography",
)

OWNED_CLAIM_MARKERS = (
    "the brand describes itself",
    "brand describes itself",
    "the brand claims",
    "states",
    "make email your most valuable channel",
    "email-first operating system",
    "content feels original",
)

BROAD_MARKET_NOISE_MARKERS = (
    "ssl adoption statistics",
    "market share",
    "competitors similar",
    "pricing tiers",
    "perishablenews",
    "honey watermelons",
    "fresh-pro announces",
    "brand refresh new mascot",
)

REPOSITORY_HOST_MARKERS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
)

MARKETPLACE_HOST_MARKERS = (
    "producthunt.com",
    "peerpush.net",
    "uneed.best",
    "devhunt.org",
    "sourceforge.net",
    "slashdot.org",
    "softwaresuggest.com",
)

USAGE_CLAIM_MARKERS = (
    "daily users",
    "users",
    "installs",
    "downloads",
    "contributors",
    "followers",
    "stars",
    "forks",
    "upvotes",
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


def _host(url: str | None) -> str:
    candidate = (url or "").strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str | None) -> str:
    host = (host or "").strip(".").lower()
    if not host:
        return ""
    parts = [part for part in host.split(".") if part]
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _is_visual_internal(feature_name: str, feature_source: str, raw_key: str, haystack: str) -> bool:
    return (
        "visual" in feature_source
        or "visual" in feature_name
        or raw_key == "evidence_insights"
        or any(marker in haystack for marker in VISUAL_FEATURE_MARKERS)
    )


def _is_technical(feature_name: str, feature_source: str, raw_key: str, haystack: str, url: str) -> bool:
    return (
        "context" in feature_source
        or any(marker in feature_name for marker in TECHNICAL_FEATURE_MARKERS)
        or any(marker in haystack for marker in ("robots_found", "sitemap_found", "schema_types", "crawl", "technical site"))
        or any(marker in url.lower() for marker in TECHNICAL_PATH_MARKERS)
        or raw_key == "evidence_item" and any(marker in haystack for marker in TECHNICAL_PATH_MARKERS)
    )


def _is_trust_security(host: str, haystack: str) -> bool:
    return any(marker in host or marker in haystack for marker in TRUST_SECURITY_HOST_MARKERS)


def _is_repository(host: str) -> bool:
    return any(marker == host or host.endswith(f".{marker}") for marker in REPOSITORY_HOST_MARKERS)


def _is_marketplace(host: str) -> bool:
    return any(marker in host for marker in MARKETPLACE_HOST_MARKERS)


def _is_usage_or_traction_claim(haystack: str) -> bool:
    return any(marker in haystack for marker in USAGE_CLAIM_MARKERS)


def _is_noise(haystack: str) -> bool:
    return any(marker in haystack for marker in BROAD_MARKET_NOISE_MARKERS)


def _looks_like_owned_claim(candidate: dict) -> bool:
    text = str(candidate.get("text") or "").lower()
    source = str(candidate.get("feature_source") or "").lower()
    raw_key = str(candidate.get("raw_key") or "").lower()
    return (
        "web_scrape" in source
        or raw_key in {"evidence_snippet", "gap_self_says"}
        or any(marker in text for marker in OWNED_CLAIM_MARKERS)
    )


def _is_same_name_different_root(host: str, audit_host: str, root: str, audit_root: str) -> bool:
    if not host or not audit_host or root == audit_root:
        return False
    audit_tokens = [part for part in audit_host.split(".") if len(part) >= 4]
    return any(token in host for token in audit_tokens)


def _is_same_name_external_profile(text: str, url: str, audit_host: str, audit_root: str) -> bool:
    host = _host(url)
    if not url or not audit_host or not host or _root_domain(host) == audit_root:
        return False
    audit_tokens = [part for part in audit_host.split(".") if len(part) >= 5]
    haystack = f"{text} {url}".lower()
    profile_hosts = (
        "crunchbase.com",
        "linkedin.com",
        "producthunt.com",
        "softwaresuggest.com",
        "sourceforge.net",
        "slashdot.org",
    )
    if not any(marker in host for marker in profile_hosts):
        return False
    return any(token in haystack for token in audit_tokens)


def _parse_raw_value(raw: Any) -> Any:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        return raw
    stripped = raw.strip()
    try:
        return ast.literal_eval(stripped)
    except (ValueError, SyntaxError, MemoryError):
        pass
    try:
        return json.loads(stripped)
    except (ValueError, TypeError):
        return raw


def _is_http_url(value: Any) -> bool:
    candidate = str(value or "").strip()
    return candidate.startswith("http://") or candidate.startswith("https://")


def _first_url(value: Any) -> str:
    if isinstance(value, str):
        return value if _is_http_url(value) else ""
    if isinstance(value, dict):
        for key in ("url", "source_url", "homepage", "target_url"):
            found = value.get(key)
            if _is_http_url(found):
                return str(found)
        for item in value.values():
            found = _first_url(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _first_url(item)
            if found:
                return found
    return ""


def _dedupe(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out

