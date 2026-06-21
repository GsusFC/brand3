"""Content web selection and fallback helpers for brand analysis."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from src.collectors.context_collector import ContextData
from src.collectors.exa_collector import ExaData
from src.collectors.web_collector import WebCollector, WebData


_MIN_USABLE_WEB_CHARS = 200
_MIN_STRATEGIC_WEB_CHARS = 2500
_MIN_EXA_FALLBACK_MENTIONS = 3
_MIN_EXA_FALLBACK_CHARS = 300
_MAX_EXA_FALLBACK_ITEMS = 8
_OWNED_FALLBACK_PATHS = (
    "/about",
    "/products",
    "/product",
    "/collections",
    "/shop",
    "/solutions",
    "/pricing",
    "/docs",
    "/blog",
    "/news",
    "/reviews",
    "/testimonials",
    "/customers",
    "/case-studies",
    "/help",
    "/support",
    "/trust",
    "/security",
)


def _effective_brand_url(original_url: str, web_data: WebData | None) -> str:
    if web_data and getattr(web_data, "canonical_url", ""):
        return web_data.canonical_url
    return original_url


def _has_usable_web_content(web_data: WebData | None) -> bool:
    if not web_data or getattr(web_data, "error", ""):
        return False
    return len((web_data.markdown_content or "").strip()) >= _MIN_USABLE_WEB_CHARS


def _has_strategic_web_coverage(web_data: WebData | None) -> bool:
    if not _has_usable_web_content(web_data):
        return False
    if getattr(web_data, "owned_fallback_urls", None):
        return True
    return len((web_data.markdown_content or "").strip()) >= _MIN_STRATEGIC_WEB_CHARS


def _should_enrich_owned_web_content(
    web_data: WebData | None,
    context_data: ContextData | None,
) -> bool:
    if not _has_usable_web_content(web_data):
        return True
    if _has_strategic_web_coverage(web_data):
        return False
    if not context_data:
        return False
    return any(bool(found) for found in (context_data.key_pages or {}).values())


def _aggregate_exa_content(exa_data: ExaData | None) -> tuple[str, int]:
    if not exa_data or len(exa_data.mentions) < _MIN_EXA_FALLBACK_MENTIONS:
        return "", 0

    aggregate_parts: list[str] = []
    used = 0
    for item in exa_data.mentions[:_MAX_EXA_FALLBACK_ITEMS]:
        title = (item.title or "").strip()
        snippet = (
            (item.text or "").strip()
            or (item.summary or "").strip()
            or " ".join(str(highlight).strip() for highlight in (item.highlights or []) if str(highlight).strip())
        )
        snippet = snippet[:500]
        if not title and not snippet:
            continue
        used += 1
        aggregate_parts.append("\n".join(part for part in [title, snippet] if part))

    aggregate = "\n\n---\n\n".join(aggregate_parts).strip()
    if len(aggregate) < _MIN_EXA_FALLBACK_CHARS:
        return "", 0
    return aggregate, used


def _owned_fallback_urls(url: str) -> list[str]:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if not parsed.netloc:
        return []
    scheme = parsed.scheme or "https"
    return [
        urlunparse((scheme, parsed.netloc, path, "", "", ""))
        for path in _OWNED_FALLBACK_PATHS
    ]


def _recover_owned_web_content(
    url: str,
    web_data: WebData | None,
    web_collector: WebCollector,
    context_data: ContextData | None = None,
) -> WebData | None:
    if not _should_enrich_owned_web_content(web_data, context_data):
        return None

    candidates = _owned_fallback_urls(url)
    if not candidates:
        return None

    recovered_pages = [
        page for page in web_collector.scrape_multiple(candidates)
        if _has_usable_web_content(page)
    ]
    if not recovered_pages:
        return None

    aggregate_parts = []
    if web_data and (web_data.markdown_content or "").strip():
        aggregate_parts.append(
            f"Source: {web_data.url or url}\n\n{(web_data.markdown_content or '').strip()}"
        )
    aggregate_parts.extend(
        f"Source: {page.url}\n\n{(page.markdown_content or '').strip()}"
        for page in recovered_pages
    )
    aggregate = "\n\n---\n\n".join(aggregate_parts).strip()
    if len(aggregate) < _MIN_USABLE_WEB_CHARS:
        return None

    base = web_data or WebData(url=url)
    first = recovered_pages[0]
    recovered = WebData(
        url=base.url or url,
        title=(base.title or first.title or "").strip(),
        meta_description=(base.meta_description or first.meta_description or "").strip(),
        markdown_content=aggregate,
        html=base.html or first.html,
        canonical_url=base.canonical_url or first.canonical_url,
        alternate_domains=list(base.alternate_domains or first.alternate_domains or []),
        links=list(base.links or []) + [link for page in recovered_pages for link in (page.links or [])],
        images=list(base.images or []) + [image for page in recovered_pages for image in (page.images or [])],
        screenshot_path=base.screenshot_path or first.screenshot_path,
        tech_stack=list(base.tech_stack or first.tech_stack or []),
        load_time_ms=base.load_time_ms or first.load_time_ms,
        error="",
    )
    recovered.owned_fallback_urls = [page.url for page in recovered_pages]
    recovered.content_source = "owned_fallback"
    return recovered


def _build_content_web(
    url: str,
    brand_name: str | None,
    web_data: WebData | None,
    exa_data: ExaData | None,
) -> tuple[WebData | None, str, dict[str, object]]:
    if _has_usable_web_content(web_data):
        content_source = getattr(web_data, "content_source", "") or "firecrawl"
        web_scrape = content_source if content_source in ("browser_fallback", "owned_fallback") else "firecrawl"
        return web_data, content_source, {
            "web_scrape": web_scrape,
            "exa_mentions": len(exa_data.mentions) if exa_data else 0,
            "content_source": content_source,
            "exa_fallback_mentions_used": 0,
            "owned_fallback_urls": list(getattr(web_data, "owned_fallback_urls", []) or []),
        }

    aggregate, mentions_used = _aggregate_exa_content(exa_data)
    if aggregate:
        base = web_data or WebData(url=url)
        fallback_title = (
            (base.title or "").strip()
            or (exa_data.mentions[0].title.strip() if exa_data and exa_data.mentions and exa_data.mentions[0].title else "")
            or (brand_name or "")
        )
        fallback_web = WebData(
            url=base.url or url,
            title=fallback_title,
            meta_description=base.meta_description,
            markdown_content=aggregate,
            html=base.html,
            canonical_url=base.canonical_url,
            alternate_domains=list(base.alternate_domains or []),
            links=list(base.links or []),
            images=list(base.images or []),
            screenshot_path=base.screenshot_path,
            tech_stack=list(base.tech_stack or []),
            load_time_ms=base.load_time_ms,
            error="",
        )
        return fallback_web, "exa_fallback", {
            "web_scrape": "failed",
            "exa_mentions": len(exa_data.mentions) if exa_data else 0,
            "content_source": "exa_fallback",
            "exa_fallback_mentions_used": mentions_used,
            "owned_fallback_urls": [],
        }

    return None, "none", {
        "web_scrape": "failed",
        "exa_mentions": len(exa_data.mentions) if exa_data else 0,
        "content_source": "none",
        "exa_fallback_mentions_used": 0,
        "owned_fallback_urls": [],
    }


def _web_content_changed(original: WebData | None, effective: WebData | None) -> bool:
    if not effective:
        return False
    if not original:
        return True
    return (
        (original.markdown_content or "") != (effective.markdown_content or "")
        or list(original.owned_fallback_urls or []) != list(effective.owned_fallback_urls or [])
        or (original.content_source or "") != (effective.content_source or "")
    )
