"""Execution trace for Brand Research acquisition plans.

The acquisition plan is intentional: what the system thinks it should fetch or
search. This trace is operational: what this run actually observed through the
existing collectors, cache, and discovery enrichment.
"""

from __future__ import annotations

from typing import Any


TRACE_VERSION = "brand_research_acquisition_trace_v0_1"
QUALITY_SUMMARY_VERSION = "brand_research_acquisition_quality_v0_1"


def build_brand_research_acquisition_trace(
    *,
    acquisition_plan: dict[str, Any],
    discovery_enrichment: dict[str, Any] | None = None,
    raw_input_cache: dict[str, str] | None = None,
    content_source: str = "",
    data_quality: str = "",
    web_data: Any | None = None,
    exa_data: Any | None = None,
) -> dict[str, object]:
    enrichment = discovery_enrichment if isinstance(discovery_enrichment, dict) else {}
    cache = raw_input_cache if isinstance(raw_input_cache, dict) else {}
    observed_urls = _observed_urls(web_data, enrichment)
    enrichment_urls = {str(url).rstrip("/") for url in enrichment.get("urls_used") or []}
    planned_sources = [
        _source_trace(source, observed_urls=observed_urls, enrichment_urls=enrichment_urls, content_source=content_source)
        for source in acquisition_plan.get("sources_to_fetch") or []
        if isinstance(source, dict)
    ]
    planned_queries = [
        _query_trace(query, enrichment_queries=enrichment.get("queries_used") or [])
        for query in acquisition_plan.get("queries_to_run") or []
    ]
    observed_source_count = sum(1 for source in planned_sources if source["status"] == "observed")
    executed_query_count = sum(1 for query in planned_queries if query["status"] == "executed")
    return {
        "version": TRACE_VERSION,
        "plan_version": acquisition_plan.get("version"),
        "seed_url": acquisition_plan.get("seed_url"),
        "resolved_entity": acquisition_plan.get("resolved_entity"),
        "analysis_mode": acquisition_plan.get("analysis_mode"),
        "provider_summary": {
            "content_source": content_source or "unknown",
            "data_quality": data_quality or "unknown",
            "web_cache": cache.get("web") or "unknown",
            "exa_cache": cache.get("exa") or "unknown",
            "exa_mentions": len(getattr(exa_data, "mentions", []) or []),
            "exa_news": len(getattr(exa_data, "news", []) or []),
            "discovery_enrichment_applied": bool(enrichment.get("applied")),
            "discovery_added_owned_evidence": int(enrichment.get("added_owned_evidence") or 0),
            "discovery_added_third_party_evidence": int(enrichment.get("added_third_party_evidence") or 0),
        },
        "sources": planned_sources,
        "queries": planned_queries,
        "coverage": {
            "planned_sources": len(planned_sources),
            "observed_sources": observed_source_count,
            "planned_queries": len(planned_queries),
            "executed_queries": executed_query_count,
            "deferred_sources": sum(1 for source in planned_sources if source["status"] == "deferred"),
        },
        "limitations": _limitations(acquisition_plan, planned_sources, planned_queries),
    }


def build_brand_research_acquisition_quality_summary(trace: dict[str, Any]) -> dict[str, object]:
    """Summarize acquisition execution quality into stable comparison metrics."""
    coverage = trace.get("coverage") if isinstance(trace.get("coverage"), dict) else {}
    provider = trace.get("provider_summary") if isinstance(trace.get("provider_summary"), dict) else {}
    sources = trace.get("sources") if isinstance(trace.get("sources"), list) else []
    planned_sources = int(coverage.get("planned_sources") or 0)
    observed_sources = int(coverage.get("observed_sources") or 0)
    planned_queries = int(coverage.get("planned_queries") or 0)
    executed_queries = int(coverage.get("executed_queries") or 0)
    source_coverage = _ratio(observed_sources, planned_sources)
    query_coverage = _ratio(executed_queries, planned_queries)
    planned_not_observed = [
        source for source in sources
        if isinstance(source, dict) and source.get("status") == "planned_not_observed"
    ]
    critical_misses = [
        source for source in planned_not_observed
        if str(source.get("fetch_intent") or "") != "defer_by_default"
        and int(source.get("priority") or 999) <= 60
    ]
    fallback_penalty = _fallback_penalty(str(provider.get("content_source") or ""))
    score = round(
        100
        - ((1.0 - source_coverage) * 45)
        - ((1.0 - query_coverage) * 20 if planned_queries else 0)
        - (len(critical_misses) * 12)
        - fallback_penalty
    )
    score = max(0, min(100, score))
    label = _quality_label(score)
    return {
        "version": QUALITY_SUMMARY_VERSION,
        "trace_version": trace.get("version"),
        "score": score,
        "label": label,
        "metrics": {
            "source_coverage_ratio": round(source_coverage, 4),
            "query_execution_ratio": round(query_coverage, 4),
            "planned_sources": planned_sources,
            "observed_sources": observed_sources,
            "planned_queries": planned_queries,
            "executed_queries": executed_queries,
            "critical_source_misses": len(critical_misses),
            "deferred_sources": int(coverage.get("deferred_sources") or 0),
            "fallback_penalty": fallback_penalty,
            "owned_evidence_added": int(provider.get("discovery_added_owned_evidence") or 0),
            "third_party_evidence_added": int(provider.get("discovery_added_third_party_evidence") or 0),
        },
        "warnings": _quality_warnings(
            source_coverage=source_coverage,
            query_coverage=query_coverage,
            planned_queries=planned_queries,
            critical_misses=critical_misses,
            provider=provider,
        ),
        "strengths": _quality_strengths(
            source_coverage=source_coverage,
            query_coverage=query_coverage,
            planned_queries=planned_queries,
            provider=provider,
        ),
    }


def _source_trace(
    source: dict[str, Any],
    *,
    observed_urls: set[str],
    enrichment_urls: set[str],
    content_source: str,
) -> dict[str, object]:
    url = str(source.get("url") or "").strip()
    key = url.rstrip("/")
    fetch_intent = str(source.get("fetch_intent") or "")
    if fetch_intent == "defer_by_default":
        status = "deferred"
        observed_via = ""
    elif key in observed_urls:
        status = "observed"
        observed_via = "discovery_enrichment" if key in enrichment_urls else (content_source or "web")
    else:
        status = "planned_not_observed"
        observed_via = ""
    return {
        "url": url,
        "role": source.get("role") or "",
        "entity_scope": source.get("entity_scope") or "",
        "fetch_intent": fetch_intent,
        "priority": source.get("priority"),
        "status": status,
        "observed_via": observed_via,
        "reason": source.get("reason") or "",
    }


def _query_trace(query: Any, *, enrichment_queries: list[Any]) -> dict[str, object]:
    value = str(query or "").strip()
    executed = value in {str(item or "").strip() for item in enrichment_queries}
    return {
        "query": value,
        "status": "executed" if executed else "not_executed",
        "observed_via": "discovery_enrichment" if executed else "",
    }


def _observed_urls(web_data: Any | None, enrichment: dict[str, Any]) -> set[str]:
    urls = {str(url).rstrip("/") for url in enrichment.get("urls_used") or [] if url}
    if web_data is not None:
        for value in [getattr(web_data, "url", ""), getattr(web_data, "canonical_url", "")]:
            if value:
                urls.add(str(value).rstrip("/"))
        for value in getattr(web_data, "owned_fallback_urls", []) or []:
            if value:
                urls.add(str(value).rstrip("/"))
    return urls


def _limitations(
    acquisition_plan: dict[str, Any],
    sources: list[dict[str, object]],
    queries: list[dict[str, object]],
) -> list[str]:
    limitations = [str(item) for item in acquisition_plan.get("limitations") or [] if item]
    if any(source["status"] == "planned_not_observed" for source in sources):
        limitations.append("planned_sources_not_observed")
    if any(query["status"] == "not_executed" for query in queries):
        limitations.append("planned_queries_not_executed")
    return _unique(limitations)


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return max(0.0, min(1.0, numerator / denominator))


def _fallback_penalty(content_source: str) -> int:
    if content_source in {"none", "unknown"}:
        return 25
    if content_source == "exa_fallback":
        return 18
    if content_source in {"metadata_only", "exa_metadata"}:
        return 14
    return 0


def _quality_label(score: int) -> str:
    if score >= 80:
        return "good"
    if score >= 55:
        return "degraded"
    return "insufficient"


def _quality_warnings(
    *,
    source_coverage: float,
    query_coverage: float,
    planned_queries: int,
    critical_misses: list[dict[str, Any]],
    provider: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if source_coverage < 0.75:
        warnings.append("low_planned_source_coverage")
    if planned_queries and query_coverage < 0.5:
        warnings.append("low_query_execution_coverage")
    if critical_misses:
        warnings.append("critical_planned_sources_missing")
    if str(provider.get("content_source") or "") in {"exa_fallback", "none", "unknown", "metadata_only", "exa_metadata"}:
        warnings.append("high_fallback_dependency")
    return warnings


def _quality_strengths(
    *,
    source_coverage: float,
    query_coverage: float,
    planned_queries: int,
    provider: dict[str, Any],
) -> list[str]:
    strengths: list[str] = []
    if source_coverage >= 0.8:
        strengths.append("planned_sources_well_covered")
    if not planned_queries or query_coverage >= 0.75:
        strengths.append("planned_queries_well_covered")
    if int(provider.get("discovery_added_owned_evidence") or 0) > 0:
        strengths.append("owned_evidence_enriched")
    if str(provider.get("data_quality") or "") == "good":
        strengths.append("collector_data_quality_good")
    return strengths
