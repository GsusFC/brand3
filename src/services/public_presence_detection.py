"""Low-level public presence candidate detection helpers."""

from __future__ import annotations

from urllib.parse import urlparse


_MIN_USABLE_WEB_CHARS = 200
_LLM_ALLOWED_CONTENT_SOURCES = {
    "firecrawl",
    "browser_fallback",
    "owned_fallback",
    "official_related",
}


def _normalize_public_url(value: str) -> str:
    candidate = (value or "").strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    return candidate.rstrip("/")


def _public_host(value: str) -> str:
    parsed = urlparse(_normalize_public_url(value))
    host = (parsed.netloc or parsed.path).lower()
    return host[4:] if host.startswith("www.") else host


def _root_domain(host: str) -> str:
    parts = [part for part in (host or "").split(".") if part]
    if len(parts) <= 2:
        return ".".join(parts)
    return ".".join(parts[-2:])


def _is_public_http_page(value: str) -> bool:
    parsed = urlparse(_normalize_public_url(value))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return not parsed.path.lower().endswith((".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".zip"))


def _merge_source_token(left: str, right: str) -> str:
    tokens: list[str] = []
    for value in (left, right):
        for token in (value or "").split("+"):
            if token and token not in tokens:
                tokens.append(token)
    return "+".join(tokens)


def _public_presence_page_type(candidate_url: str, title_or_snippet: str = "") -> str:
    host = _public_host(candidate_url)
    path = urlparse(candidate_url).path.lower()
    text = f"{host} {path} {title_or_snippet}".lower()
    if "docs." in host or "/docs" in path or "documentation" in text:
        return "docs"
    if "support." in host or "/support" in path or "/help" in path or "help center" in text:
        return "support"
    if "/news" in path or "/blog" in path or "newsroom" in text or "press" in text:
        return "news_or_blog"
    if "/trust" in path or "/security" in path or "safety" in text or "compliance" in text:
        return "trust_or_safety"
    return "primary"


def _classify_public_presence_candidate(
    *,
    brand_name: str,
    input_url: str,
    candidate_url: str,
    title_or_snippet: str = "",
) -> tuple[str, str, float]:
    input_host = _public_host(input_url)
    candidate_host = _public_host(candidate_url)
    candidate_path = urlparse(candidate_url).path.lower()
    evidence = f"{candidate_host} {candidate_path} {title_or_snippet}".lower()
    brand = (brand_name or "").lower()
    if candidate_url.rstrip("/") == input_url.rstrip("/"):
        return "primary", "primary_domain", 1.0
    page_type = _public_presence_page_type(candidate_url, title_or_snippet)
    if candidate_host == input_host:
        return page_type if page_type != "primary" else "same_domain_page", "same_domain", 0.95
    if _root_domain(candidate_host) == _root_domain(input_host):
        return page_type if page_type != "primary" else "same_domain_page", "same_domain", 0.85
    if brand == "claude" and (
        candidate_host == "anthropic.com" or candidate_host.endswith(".anthropic.com")
    ) and ("claude" in evidence or "anthropic" in evidence):
        return page_type if page_type != "primary" else "official_related", "official_related", 0.9
    compact_brand = "".join(ch for ch in brand if ch.isalnum())
    compact_host = "".join(ch for ch in candidate_host if ch.isalnum())
    if compact_brand and compact_brand in compact_host and brand in evidence:
        return page_type if page_type != "primary" else "official_related", "official_related", 0.72
    return "third_party", "third_party", 0.2


def _add_public_presence_candidate(
    candidates: dict[str, dict[str, object]],
    *,
    brand_name: str,
    input_url: str,
    candidate_url: str,
    source: str,
    title_or_snippet: str,
    text_chars: int,
    content_source: str,
    search_metadata_only: bool,
) -> None:
    normalized = _normalize_public_url(candidate_url)
    page_type, relation, confidence = _classify_public_presence_candidate(
        brand_name=brand_name,
        input_url=input_url,
        candidate_url=normalized,
        title_or_snippet=title_or_snippet,
    )
    usable_brand = relation in {"primary_domain", "same_domain", "official_related"} and text_chars >= _MIN_USABLE_WEB_CHARS
    if search_metadata_only:
        usable_brand = False
    usable_perception = relation == "third_party" and bool(title_or_snippet or text_chars)
    existing = candidates.get(normalized)
    if existing:
        existing["source"] = _merge_source_token(str(existing["source"]), source)
        existing["confidence"] = max(float(existing["confidence"]), confidence)
        existing["text_chars"] = max(int(existing["text_chars"]), int(text_chars or 0))
        existing["usable_for_brand_evidence"] = bool(existing["usable_for_brand_evidence"] or usable_brand)
        existing["usable_for_perception_evidence"] = bool(existing["usable_for_perception_evidence"] or usable_perception)
        if not existing["title_or_snippet"] and title_or_snippet:
            existing["title_or_snippet"] = title_or_snippet[:200]
        if existing["content_source"] in {"metadata_only", "exa_metadata"} and content_source not in {"metadata_only", "exa_metadata"}:
            existing["content_source"] = content_source
        return
    candidates[normalized] = {
        "candidate_url": normalized,
        "host": _public_host(normalized),
        "page_type": page_type,
        "relation_to_brand": relation,
        "confidence": confidence,
        "source": source,
        "title_or_snippet": (title_or_snippet or "")[:200],
        "content_source": content_source,
        "text_chars": int(text_chars or 0),
        "usable_for_brand_evidence": usable_brand,
        "usable_for_perception_evidence": usable_perception,
    }
