"""Low-level helpers for Evidence Packet v0 classification."""

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
