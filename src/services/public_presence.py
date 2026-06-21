"""Read-only public presence inventory helpers for brand analysis."""

from __future__ import annotations

from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.web_collector import WebData
from src.services.public_presence_detection import (
    _LLM_ALLOWED_CONTENT_SOURCES,
    _add_public_presence_candidate,
    _is_public_http_page,
    _normalize_public_url,
)


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
