"""Read-only public presence inventory helpers for brand analysis."""

from __future__ import annotations

from urllib.parse import urlparse

from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.web_collector import WebData


_MIN_USABLE_WEB_CHARS = 200
_LLM_ALLOWED_CONTENT_SOURCES = {
    "firecrawl",
    "browser_fallback",
    "owned_fallback",
    "official_related",
}


def _public_presence_inventory_summary(
    *,
    brand_name: str,
    url: str,
    web_data: WebData | None,
    content_web: WebData | None,
    content_source: str,
    exa_data: ExaData | None,
    context_data: ContextData | None,
) -> dict[str, object]:
    """Summarize public official pages already observed by approved collectors.

    This is deliberately read-only and does not perform additional fetches. It
    keeps ContextCollector facts separate from the raw context_readiness payload.
    """
    input_url = _normalize_public_url(url)
    candidates: dict[str, dict[str, object]] = {}

    primary_text_chars = 0
    if content_source in _LLM_ALLOWED_CONTENT_SOURCES and content_web:
        primary_text_chars = len(content_web.markdown_content or "")
    elif web_data:
        primary_text_chars = len(web_data.markdown_content or "")
    _add_public_presence_candidate(
        candidates,
        brand_name=brand_name,
        input_url=input_url,
        candidate_url=input_url,
        source="input",
        title_or_snippet=(getattr(web_data, "title", "") or getattr(content_web, "title", "") or ""),
        text_chars=primary_text_chars,
        content_source=content_source,
        search_metadata_only=False,
    )

    for candidate_url in getattr(web_data, "owned_fallback_urls", []) or []:
        _add_public_presence_candidate(
            candidates,
            brand_name=brand_name,
            input_url=input_url,
            candidate_url=candidate_url,
            source="owned_fallback",
            title_or_snippet="owned fallback page",
            text_chars=0,
            content_source="owned_fallback",
            search_metadata_only=False,
        )

    for candidate_url in getattr(web_data, "links", []) or []:
        if _is_public_http_page(candidate_url):
            _add_public_presence_candidate(
                candidates,
                brand_name=brand_name,
                input_url=input_url,
                candidate_url=str(candidate_url),
                source="web_links",
                title_or_snippet="",
                text_chars=0,
                content_source="metadata_only",
                search_metadata_only=False,
            )

    if context_data:
        for name, found in (context_data.key_pages or {}).items():
            if not found:
                continue
            _add_public_presence_candidate(
                candidates,
                brand_name=brand_name,
                input_url=input_url,
                candidate_url=f"{input_url}/{name.replace('_', '-')}",
                source="context",
                title_or_snippet=f"context key page: {name}",
                text_chars=0,
                content_source="metadata_only",
                search_metadata_only=False,
            )

    if exa_data:
        for result in list(exa_data.mentions or []) + list(exa_data.news or []):
            if not result.url or not _is_public_http_page(result.url):
                continue
            snippet = result.title or result.summary or (result.text or "")[:200]
            _add_public_presence_candidate(
                candidates,
                brand_name=brand_name,
                input_url=input_url,
                candidate_url=result.url,
                source="exa",
                title_or_snippet=snippet,
                text_chars=0,
                content_source="exa_metadata",
                search_metadata_only=True,
            )

    rows = list(candidates.values())
    official_rows = [
        row for row in rows
        if row["relation_to_brand"] in {"primary_domain", "same_domain", "official_related"}
    ]
    usable_brand_rows = [row for row in rows if row["usable_for_brand_evidence"]]
    usable_perception_rows = [row for row in rows if row["usable_for_perception_evidence"]]
    official_related_usable = [
        row for row in usable_brand_rows if row["relation_to_brand"] == "official_related"
    ]
    primary = candidates.get(input_url)
    primary_chars = int(primary["text_chars"]) if primary else 0
    primary_usable = bool(primary and primary["usable_for_brand_evidence"])
    recommended = len(usable_brand_rows) >= 2 or (primary_usable and primary_chars >= 1500)
    return {
        "mode": "read_only_public_pages",
        "total_public_pages_found": len(rows),
        "official_pages_found": len(official_rows),
        "usable_brand_evidence_pages": len(usable_brand_rows),
        "usable_public_perception_pages": len(usable_perception_rows),
        "primary_page": {
            "url": input_url,
            "collection_method": str(primary["content_source"] if primary else content_source),
            "text_chars": primary_chars,
            "usable_for_brand_evidence": primary_usable,
        },
        "official_related_usable_count": len(official_related_usable),
        "docs_candidates": sum(1 for row in official_rows if row["page_type"] == "docs"),
        "support_candidates": sum(1 for row in official_rows if row["page_type"] == "support"),
        "news_or_blog_candidates": sum(1 for row in official_rows if row["page_type"] == "news_or_blog"),
        "trust_or_safety_candidates": sum(1 for row in official_rows if row["page_type"] == "trust_or_safety"),
        "third_party_candidates": sum(1 for row in rows if row["relation_to_brand"] == "third_party"),
        "candidate_sources": sorted({source for row in rows for source in str(row["source"]).split("+") if source}),
        "recommended_evidence_base": recommended,
        "note": "Read-only summary from public URLs observed by existing collectors; no scoring or readiness decisions changed.",
    }


def _context_enrichment_summary(
    *,
    public_presence_inventory: dict[str, object] | None,
    context_summary: dict[str, object] | None,
) -> dict[str, object]:
    """Derive a read-only context note from the public presence inventory.

    This does not alter raw ContextCollector output or trust status. It only
    explains when existing observed official pages reduce the apparent
    contradiction of a failed homepage pre-scan.
    """
    inventory = public_presence_inventory or {}
    context = context_summary or {}
    raw_context_limited = (
        context.get("status") == "insufficient_data"
        or float(context.get("coverage") or 0.0) == 0.0
    )
    recommended = bool(inventory.get("recommended_evidence_base"))
    if not recommended or not raw_context_limited:
        return {
            "source": "public_presence_inventory",
            "applied": False,
            "reason": "not_applicable",
        }

    limitations = ["raw_context_readiness_unchanged"]
    if context.get("status") == "insufficient_data" or float(context.get("coverage") or 0.0) == 0.0:
        limitations.insert(0, "homepage_pre_scan_unavailable")

    return {
        "source": "public_presence_inventory",
        "applied": True,
        "status": "raw_context_limited_but_public_inventory_available",
        "reason": "official_public_pages_available",
        "official_pages_found": int(inventory.get("official_pages_found") or 0),
        "usable_brand_evidence_pages": int(inventory.get("usable_brand_evidence_pages") or 0),
        "usable_public_perception_pages": int(inventory.get("usable_public_perception_pages") or 0),
        "docs_candidates": int(inventory.get("docs_candidates") or 0),
        "support_candidates": int(inventory.get("support_candidates") or 0),
        "news_or_blog_candidates": int(inventory.get("news_or_blog_candidates") or 0),
        "trust_or_safety_candidates": int(inventory.get("trust_or_safety_candidates") or 0),
        "recommended_evidence_base": recommended,
        "message": "homepage pre-scan limited, but public official pages were detected through existing collectors",
        "limitations": limitations,
    }


def _context_effective_readiness(
    *,
    public_presence_inventory: dict[str, object] | None,
    context_summary: dict[str, object] | None,
) -> dict[str, object]:
    inventory = public_presence_inventory or {}
    context = context_summary or {}
    raw_context_limited = (
        context.get("status") == "insufficient_data"
        or float(context.get("coverage") or 0.0) == 0.0
    )
    if (
        not raw_context_limited
        or not bool(inventory.get("recommended_evidence_base"))
        or int(inventory.get("usable_brand_evidence_pages") or 0) <= 0
    ):
        return {
            "source": "public_presence_inventory",
            "applied": False,
            "reason": "not_applicable",
        }

    return {
        "source": "public_presence_inventory",
        "applied": True,
        "status": "degraded",
        "coverage": 0.45,
        "confidence": 0.45,
        "confidence_reason": ["homepage_unavailable_but_public_inventory_available"],
        "reason": "homepage_unavailable_but_public_inventory_available",
        "official_pages_found": int(inventory.get("official_pages_found") or 0),
        "usable_brand_evidence_pages": int(inventory.get("usable_brand_evidence_pages") or 0),
        "usable_public_perception_pages": int(inventory.get("usable_public_perception_pages") or 0),
        "recommended_evidence_base": True,
        "limitations": [
            "homepage_pre_scan_unavailable",
            "raw_context_readiness_unchanged",
        ],
    }


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
