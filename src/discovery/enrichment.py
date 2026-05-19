"""Optional discovery evidence enrichment.

This module may use already configured collectors, but it keeps the added data
separate and does not touch scoring weights, prompts, cache keys, or calibration.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.web_collector import WebData


@dataclass(frozen=True)
class DiscoveryEnrichmentResult:
    exa_data: ExaData | None
    web_data: WebData | None
    payload: dict[str, object] = field(default_factory=dict)


_MAX_ENRICHMENT_RESULTS = 15


def build_discovery_enrichment(search_plan: dict, evidence_preview: dict, *, exa_data=None, web_data=None, web_collector=None, exa_collector=None) -> DiscoveryEnrichmentResult:
    urls = list(search_plan.get("owned_urls") or [])
    queries = list(search_plan.get("queries") or [])
    if not evidence_preview.get("recommended_to_use_for_scoring"):
        return DiscoveryEnrichmentResult(exa_data, web_data, _payload(False, [], [], 0, 0))

    added_pages = _collect_owned_pages(urls, web_collector)
    added_results, diagnostics = _collect_exa_results(queries, exa_collector)
    enriched_web = _merge_web(web_data, added_pages)
    enriched_exa = _merge_exa(exa_data, added_results)
    owned_domains = {_domain(url) for url in urls if url}
    owned_added = sum(1 for item in added_results if _domain(item.url) in owned_domains)
    third_added = sum(1 for item in added_results if _domain(item.url) not in owned_domains)
    return DiscoveryEnrichmentResult(
        enriched_exa,
        enriched_web,
        _payload(
            True,
            urls,
            queries,
            owned_added + len(added_pages),
            third_added,
            diagnostics=diagnostics,
        ),
    )


def _payload(
    applied: bool,
    urls: list[str],
    queries: list[str],
    owned: int,
    third_party: int,
    *,
    diagnostics: dict | None = None,
) -> dict[str, object]:
    return {
        "applied": applied,
        "urls_used": urls if applied else [],
        "queries_used": queries if applied else [],
        "added_owned_evidence": owned,
        "added_third_party_evidence": third_party,
        "diagnostics": diagnostics or {},
    }


def _collect_owned_pages(urls: list[str], web_collector) -> list[WebData]:
    if not urls or not web_collector:
        return []
    try:
        return [page for page in web_collector.scrape_multiple(urls) if getattr(page, "markdown_content", "")]
    except Exception:
        return []


def _collect_exa_results(queries: list[str], exa_collector) -> tuple[list[ExaResult], dict[str, object]]:
    if not queries or not exa_collector:
        return [], {"applied_cap": False, "cap": _MAX_ENRICHMENT_RESULTS, "truncated": 0}
    results: list[ExaResult] = []
    failures: list[dict[str, str]] = []
    for query in queries:
        try:
            found = exa_collector.search(query, num_results=5, intent="enrichment")
            for item in found:
                item.metadata = {
                    **(item.metadata or {}),
                    "enrichment_query": query,
                    "enrichment_rationale": "discovery_search_plan_query_match",
                    "enrichment_inserted": True,
                }
            results.extend(found)
        except Exception as exc:
            failures.append({"query": query, "error": str(exc)})
            continue
    unique = _unique_results(results)
    capped = unique[:_MAX_ENRICHMENT_RESULTS]
    return capped, {
        "applied_cap": len(unique) > _MAX_ENRICHMENT_RESULTS,
        "cap": _MAX_ENRICHMENT_RESULTS,
        "truncated": max(0, len(unique) - _MAX_ENRICHMENT_RESULTS),
        "query_failures": failures,
    }


def _merge_web(web_data: WebData | None, pages: list[WebData]) -> WebData | None:
    if not pages:
        return web_data
    base = web_data or WebData(url=pages[0].url)
    extra = "\n\n---\n\n".join(f"Source: {page.url}\n\n{page.markdown_content.strip()}" for page in pages)
    existing = (base.markdown_content or "").strip()
    return replace(
        base,
        markdown_content="\n\n---\n\n".join(part for part in [existing, extra] if part),
        links=list(base.links or []) + [link for page in pages for link in (page.links or [])],
        owned_fallback_urls=list(dict.fromkeys(list(base.owned_fallback_urls or []) + [page.url for page in pages])),
        content_source=getattr(base, "content_source", "") or "discovery_enrichment",
    )


def _merge_exa(exa_data: ExaData | None, results: list[ExaResult]) -> ExaData | None:
    if not results:
        return exa_data
    base = exa_data or ExaData(brand_name="")
    diagnostics = dict(base.diagnostics or {})
    diagnostics["enrichment_insertions"] = len(results)
    return replace(base, mentions=_unique_results(list(base.mentions or []) + results), diagnostics=diagnostics)


def _unique_results(results: list[ExaResult]) -> list[ExaResult]:
    seen: set[str] = set()
    unique: list[ExaResult] = []
    for item in results:
        key = (item.url or item.title or item.text or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _domain(value: str) -> str:
    return value.split("://", 1)[-1].split("/", 1)[0].removeprefix("www.").lower()
