#!/usr/bin/env python3
"""Online Search Enrichment Lab runner.

This script is intentionally isolated from canonical Brand3 flows. It can call
real providers when their keys exist in `.env`, normalizes outputs into
BrandSourceObservation, and writes artifacts under `out/`.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from src.collectors.exa_collector import ExaCollector
from src.collectors.parallel_shadow_collector import ParallelShadowCollector
from src.collectors.web_collector import WebCollector
from src.config import EXA_API_KEY, FIRECRAWL_API_KEY
from src.research.brand_intelligence import (
    BrandSeed,
    BrandSourceBakeoffCase,
    BrandSourceObservation,
    build_brand_source_inventory,
    build_brand_source_plan,
    evaluate_brand_source_bakeoff,
    owned_web_source_observation,
    resolve_brand_seed,
    scope_external_observation_to_entity,
    search_source_observation,
)


LAB_VERSION = "search_enrichment_lab_v0_1"
USER_AGENT = "Brand3-Search-Enrichment-Lab/0.1"

DEFAULT_CASES = (
    ("LangChain", "https://www.langchain.com"),
    ("ChatGPT", "https://chatgpt.com"),
    ("Base", "https://base.org"),
)

SEARCH_PROVIDER_KEYS = {
    "exa": "EXA_API_KEY",
    "exa-fast": "EXA_API_KEY",
    "exa-auto": "EXA_API_KEY",
    "exa-deep-lite": "EXA_API_KEY",
    "exa-deep": "EXA_API_KEY",
    "exa-deep-reasoning": "EXA_API_KEY",
    "parallel": "PARALLEL_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "linkup": "LINKUP_API_KEY",
    "brave": "BRAVE_SEARCH_API_KEY",
    "serpapi": "SERPAPI_API_KEY",
}

DEFAULT_SEARCH_PROVIDERS = (
    "exa",
    "parallel",
    "tavily",
    "linkup",
    "brave",
    "serpapi",
)

OWNED_FETCH_PROVIDER_KEYS = {
    "firecrawl": "FIRECRAWL_API_KEY",
    "tinyfish": "TINYFISH_API_KEY",
}

DEFAULT_OWNED_FETCH_PROVIDERS = tuple(OWNED_FETCH_PROVIDER_KEYS)

INTENT_CHANNEL = {
    "entity_disambiguation": "search",
    "external_perception_and_friction": "reviews",
    "reputation_momentum_and_category_context": "news",
    "company_presence_team_and_category": "linkedin",
    "performed_voice_and_current_signals": "social",
    "app_or_product_distribution_surface": "app_store",
    "developer_product_reality": "docs",
    "ecosystem_adoption_and_participation": "community",
}

TECHNICAL_MARKERS = (
    "robots.txt",
    "sitemap.xml",
    "llms.txt",
    "schema.org",
    "/.well-known",
)

MARKETPLACE_HOST_MARKERS = (
    "producthunt.com",
    "peerpush.net",
    "uneed.best",
    "devhunt.org",
    "sourceforge.net",
)

NOISE_HOST_MARKERS = (
    "pinterest.",
    "youtube.com/watch",
    "amazon.",
)

EXA_SEARCH_TYPES = {
    "exa": "fast",
    "exa-fast": "fast",
    "exa-auto": "auto",
    "exa-deep-lite": "deep-lite",
    "exa-deep": "deep",
    "exa-deep-reasoning": "deep-reasoning",
}


@dataclass(frozen=True)
class LabCase:
    brand: str
    url: str

    @property
    def case_id(self) -> str:
        return _slugify(self.brand or self.url)


@dataclass(frozen=True)
class LabAcquisitionStep:
    provider: str
    status: str
    cache_status: str
    eligible: bool
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "cache_status": self.cache_status,
            "eligible": self.eligible,
            "error": self.error,
            "details": self.details,
        }


def main() -> int:
    args = _parse_args()
    providers = _selected_providers(args.providers)
    cases = _load_cases(args.cases_file) if args.cases_file else [LabCase(*item) for item in DEFAULT_CASES]
    if args.max_cases:
        cases = cases[: max(1, args.max_cases)]
    if args.list_providers:
        payload = {
            "version": LAB_VERSION,
            "active_providers": providers,
            "discarded_providers": [
                provider
                for provider in list(OWNED_FETCH_PROVIDER_KEYS) + list(SEARCH_PROVIDER_KEYS)
                if provider not in providers
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if args.plan_only:
        print(
            json.dumps(
                _planned_run_payload(
                    cases,
                    providers,
                    max_queries=args.max_queries,
                    query_profile=args.query_profile,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    output_dir = args.output_dir / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir.mkdir(parents=True, exist_ok=True)

    case_payloads: list[dict[str, Any]] = []
    bakeoff_cases: list[BrandSourceBakeoffCase] = []
    for case in cases:
        payload = run_case(
            case,
            providers=providers,
            max_results=args.results,
            timeout_seconds=args.timeout,
            max_queries=args.max_queries,
            query_profile=args.query_profile,
        )
        case_payloads.append(payload)
        bakeoff_cases.append(
            BrandSourceBakeoffCase(
                case_id=case.case_id,
                plan=_plan_from_payload(payload),
                observations=[
                    BrandSourceObservation(**item)
                    for item in payload.get("observations", [])
                    if isinstance(item, dict)
                ],
            )
        )
        (output_dir / f"{case.case_id}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    bakeoff = evaluate_brand_source_bakeoff(bakeoff_cases)
    provider_scores = _provider_scores(bakeoff.get("provider_metrics") or {}, case_payloads)
    provider_acquisition = _provider_acquisition_rows(case_payloads)
    summary = {
        "version": LAB_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "providers": providers,
        "query_profile": args.query_profile,
        "discarded_providers": _discarded_providers(providers),
        "case_count": len(case_payloads),
        "cases": [_case_summary(item) for item in case_payloads],
        "provider_acquisition": provider_acquisition,
        "provider_scores": provider_scores,
        "bakeoff": bakeoff,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_summary_md(summary), encoding="utf-8")
    print(f"Wrote Search Enrichment Lab output to {output_dir}")
    return 0


def run_case(
    case: LabCase,
    *,
    providers: list[str],
    max_results: int = 3,
    timeout_seconds: int = 30,
    max_queries: int = 0,
    query_profile: str = "compact",
) -> dict[str, Any]:
    seed = BrandSeed(case.url, kind="url", provided_name=case.brand)
    entity = resolve_brand_seed(seed)
    plan = build_brand_source_plan(entity)
    observations: list[BrandSourceObservation] = []
    provider_runs: list[dict[str, Any]] = []

    if "firecrawl" in providers and entity.canonical_url:
        provider_runs.append(_timed_provider("firecrawl", lambda: _run_firecrawl(entity.canonical_url)))
        observations.extend(provider_runs[-1]["observations"])
    if "tinyfish" in providers and entity.canonical_url:
        provider_runs.append(_timed_provider("tinyfish", lambda: _run_tinyfish(entity.canonical_url, timeout_seconds)))
        observations.extend(provider_runs[-1]["observations"])

    query_requests = [request for request in plan.source_requests if request.query]
    if max_queries:
        query_requests = query_requests[: max(1, max_queries)]
    for provider in [item for item in providers if item in SEARCH_PROVIDER_KEYS]:
        for request in query_requests:
            query = _profiled_query(
                request.query,
                profile=query_profile,
                intent=request.intent,
                channel=request.channel,
                case=case,
                entity=entity,
            )
            channel = INTENT_CHANNEL.get(request.intent, request.channel)
            provider_runs.append(
                _timed_provider(
                    provider,
                    lambda provider=provider, query=query, channel=channel: _run_search_provider(
                        provider,
                        query,
                        channel=channel,
                        entity=entity,
                        seed_url=case.url,
                        brand=case.brand,
                        max_results=max_results,
                        timeout_seconds=timeout_seconds,
                    ),
                )
            )
            observations.extend(provider_runs[-1]["observations"])

    inventory = build_brand_source_inventory(plan, observations)
    source_consensus = _source_consensus(observations)
    acquisition_steps = [_provider_run_to_acquisition_step(item).to_dict() for item in provider_runs]
    return {
        "version": LAB_VERSION,
        "case": {"case_id": case.case_id, "brand": case.brand, "url": case.url},
        "entity": entity.to_dict(),
        "plan": plan.to_dict(),
        "query_profile": query_profile,
        "providers": providers,
        "provider_runs": [_provider_run_to_dict(item) for item in provider_runs],
        "acquisition_steps": acquisition_steps,
        "observations": [observation.to_dict() for observation in observations],
        "inventory": inventory.to_dict(),
        "source_consensus": source_consensus,
    }


def _profiled_query(
    query: str,
    *,
    profile: str,
    intent: str,
    channel: str,
    case: LabCase,
    entity,
) -> str:
    if profile != "rich":
        return query
    brand = case.brand or getattr(entity, "resolved_name", "") or query
    url = case.url or getattr(entity, "canonical_url", "") or ""
    resolved_name = getattr(entity, "resolved_name", "") or brand
    resolution_status = getattr(entity, "resolution_status", "") or "unknown"
    if intent == "entity_disambiguation":
        return (
            f'Research the real brand/entity identity for "{brand}" at "{url}". '
            f'The current resolver status is "{resolution_status}" and resolved name is "{resolved_name}". '
            "Find sources that help decide whether this is a real company, product, parent brand, "
            "sub-brand, ecosystem, affiliate page, marketplace listing, or ambiguous same-name entity. "
            "Prioritize official owned surfaces, parent-company evidence, documentation, LinkedIn or company "
            "profiles, external mentions, reviews, community/ecosystem sources, and same-name collisions. "
            "Prefer primary and attributable sources. Return URLs that reduce identity ambiguity."
        )
    return (
        f'Research "{brand}" at "{url}" for the "{intent}" intent and "{channel}" channel. '
        "Prefer attributable URLs that help Brand3 evaluate entity identity, owned surfaces, external context, "
        "source quality, and ambiguity. Avoid generic results that do not reduce uncertainty."
    )


def _run_search_provider(
    provider: str,
    query: str,
    *,
    channel: str,
    entity,
    seed_url: str,
    brand: str,
    max_results: int,
    timeout_seconds: int,
) -> list[BrandSourceObservation]:
    if provider in EXA_SEARCH_TYPES:
        results = _search_exa(
            query,
            max_results=max_results,
            brand_name=brand,
            brand_url=seed_url,
            provider=provider,
            search_type=EXA_SEARCH_TYPES[provider],
            timeout_seconds=timeout_seconds,
        )
    elif provider == "parallel":
        results = _search_parallel(brand, seed_url, max_results=max_results)
    elif provider == "tavily":
        results = _search_tavily(query, max_results=max_results, timeout_seconds=timeout_seconds)
    elif provider == "linkup":
        results = _search_linkup(query, max_results=max_results, timeout_seconds=timeout_seconds)
    elif provider == "brave":
        results = _search_brave(query, max_results=max_results, timeout_seconds=timeout_seconds)
    elif provider == "serpapi":
        results = _search_serpapi(query, max_results=max_results, timeout_seconds=timeout_seconds)
    else:
        return []

    observations: list[BrandSourceObservation] = []
    for result in results[:max_results]:
        source_class, relation, reason, requires_review = _classify_lab_source(
            url=str(result.get("url") or ""),
            brand_url=seed_url,
            brand_name=brand,
        )
        observation = search_source_observation(result, provider=provider, channel=channel)  # type: ignore[arg-type]
        observation = scope_external_observation_to_entity(
            observation,
            result,
            entity=entity,
            seed_url=seed_url,
            brand=brand,
        )
        lab_observation = _with_lab_fields(
            observation,
            query_intent=str(result.get("query_intent") or query),
            source_class=str(result.get("source_class") or source_class),
            relation_to_entity=str(result.get("relation") or relation),
            requires_human_review=bool(result.get("requires_human_review") or requires_review),
            cost_estimate=result.get("cost_estimate") if isinstance(result.get("cost_estimate"), (int, float)) else None,
            diagnostics={
                "raw_provider": provider,
                "classification_reason": reason,
                **(result.get("diagnostics") if isinstance(result.get("diagnostics"), dict) else {}),
            },
        )
        observations.append(
            _guard_lab_entity_boundary(
                lab_observation,
                entity=entity,
            )
        )
    return observations


def _guard_lab_entity_boundary(observation: BrandSourceObservation, *, entity) -> BrandSourceObservation:
    if getattr(entity, "resolution_status", "") == "resolved":
        return observation
    if observation.status != "observed":
        return observation
    if observation.source_class != "external" or observation.relation_to_entity != "external":
        return observation
    from dataclasses import replace

    diagnostics = {
        **observation.diagnostics,
        "lab_guardrail": "unresolved_entity_external_candidate_requires_review",
    }
    return replace(
        observation,
        evidence_eligibility="limited" if observation.evidence_eligibility == "eligible" else observation.evidence_eligibility,
        confidence=min(observation.confidence, 0.45),
        requires_human_review=True,
        reason="unresolved_entity_external_candidate_requires_review",
        diagnostics=diagnostics,
    )


def _search_exa(
    query: str,
    *,
    max_results: int,
    brand_name: str,
    brand_url: str,
    provider: str = "exa",
    search_type: str = "fast",
    timeout_seconds: int = 30,
) -> list[dict[str, Any]]:
    if not _active_key("EXA_API_KEY"):
        return []
    if provider != "exa" or search_type != "fast":
        return _search_exa_direct(
            query,
            max_results=max_results,
            brand_name=brand_name,
            brand_url=brand_url,
            provider=provider,
            search_type=search_type,
            timeout_seconds=timeout_seconds,
        )
    collector = ExaCollector(api_key=EXA_API_KEY)
    return [
        {
            "url": item.url,
            "title": item.title,
            "text": item.text or item.summary or " ".join(str(h) for h in item.highlights),
            "summary": item.summary,
            "score": item.score,
            "published_date": item.published_date,
            "source_class": item.source_class,
            "relation": item.relation,
            "requires_human_review": item.requires_human_review,
            "query_intent": query,
            "diagnostics": {"exa_search_type": "fast", "provider_variant": provider},
        }
        for item in collector.search(
            query,
            num_results=max_results,
            intent="enrichment",
            brand_name=brand_name,
            brand_url=brand_url,
        )
    ]


def _search_exa_direct(
    query: str,
    *,
    max_results: int,
    brand_name: str,
    brand_url: str,
    provider: str,
    search_type: str,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {
        "query": query,
        "type": search_type,
        "numResults": max_results,
        "contents": {
            "highlights": True,
            "text": {"maxCharacters": 3000},
        },
        "systemPrompt": (
            "You are supporting a brand identity research pipeline. Prefer official, primary, "
            "and clearly attributable sources. Do not treat synthesized text as evidence unless "
            "it is grounded in returned URLs."
        ),
    }
    if search_type in {"deep-lite", "deep", "deep-reasoning"}:
        payload["additionalQueries"] = _exa_additional_queries(brand_name, brand_url)
        payload["outputSchema"] = {
            "type": "object",
            "required": ["entity_summary", "source_notes"],
            "properties": {
                "entity_summary": {"type": "string"},
                "source_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }
    data = _json_post(
        "https://api.exa.ai/search",
        payload,
        headers={"x-api-key": os.environ.get("EXA_API_KEY", "")},
        timeout_seconds=timeout_seconds,
    )
    results = data.get("results") if isinstance(data.get("results"), list) else []
    total_cost = _exa_cost_total(data)
    per_result_cost = round(total_cost / len(results), 8) if total_cost and results else None
    output = data.get("output") if isinstance(data.get("output"), dict) else {}
    grounding = output.get("grounding") if isinstance(output.get("grounding"), list) else []
    return [
        {
            "url": item.get("url"),
            "title": item.get("title"),
            "text": item.get("text") or " ".join(str(part) for part in item.get("highlights") or []),
            "summary": item.get("summary"),
            "score": item.get("score"),
            "published_date": item.get("publishedDate"),
            "query_intent": query,
            "cost_estimate": per_result_cost,
            "diagnostics": {
                "exa_search_type": data.get("searchType") or search_type,
                "provider_variant": provider,
                "request_id": data.get("requestId") or "",
                "cost_total": total_cost,
                "output_present": bool(output),
                "grounding_count": len(grounding),
            },
        }
        for item in results[:max_results]
        if isinstance(item, dict)
    ]


def _exa_additional_queries(brand_name: str, brand_url: str) -> list[str]:
    domain = _host(brand_url)
    return [
        f"{brand_name} official company product documentation",
        f"{brand_name} {domain} external reviews mentions competitors",
    ]


def _exa_cost_total(data: dict[str, Any]) -> float | None:
    cost = data.get("costDollars") if isinstance(data.get("costDollars"), dict) else {}
    value = cost.get("total")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _search_parallel(brand: str, url: str, *, max_results: int) -> list[dict[str, Any]]:
    collector = ParallelShadowCollector(limit=max_results)
    data = collector.collect(brand, url, intents=("mentions",))
    results: list[dict[str, Any]] = []
    for intent in data.intents.values():
        for item in intent.results:
            results.append(
                {
                    "url": item.url,
                    "title": item.title,
                    "text": item.excerpt,
                    "published_date": item.published_date,
                    "query_intent": intent.intent,
                }
            )
    return results


def _search_tavily(query: str, *, max_results: int, timeout_seconds: int) -> list[dict[str, Any]]:
    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": "text",
        "include_images": False,
        "include_usage": True,
    }
    data = _json_post(
        "https://api.tavily.com/search",
        payload,
        headers={"Authorization": f"Bearer {os.environ.get('TAVILY_API_KEY', '')}"},
        timeout_seconds=timeout_seconds,
    )
    results = data.get("results") if isinstance(data.get("results"), list) else []
    return [
        {
            "url": item.get("url"),
            "title": item.get("title"),
            "text": item.get("raw_content") or item.get("content"),
            "score": item.get("score"),
            "published_date": item.get("published_date"),
            "query_intent": query,
        }
        for item in results
        if isinstance(item, dict)
    ]


def _search_linkup(query: str, *, max_results: int, timeout_seconds: int) -> list[dict[str, Any]]:
    data = _json_post(
        "https://api.linkup.so/v1/search",
        {"q": query, "depth": "fast", "outputType": "searchResults"},
        headers={"Authorization": f"Bearer {os.environ.get('LINKUP_API_KEY', '')}"},
        timeout_seconds=timeout_seconds,
    )
    results = data.get("results") if isinstance(data.get("results"), list) else []
    return [
        {
            "url": item.get("url"),
            "title": item.get("name") or item.get("title"),
            "text": item.get("content"),
            "query_intent": query,
        }
        for item in results[:max_results]
        if isinstance(item, dict)
    ]


def _search_brave(query: str, *, max_results: int, timeout_seconds: int) -> list[dict[str, Any]]:
    url = "https://api.search.brave.com/res/v1/web/search?" + urlencode(
        {"q": query, "count": max_results, "search_lang": "en", "country": "us"}
    )
    data = _json_get(
        url,
        headers={"X-Subscription-Token": os.environ.get("BRAVE_SEARCH_API_KEY", "")},
        timeout_seconds=timeout_seconds,
    )
    web = data.get("web") if isinstance(data.get("web"), dict) else {}
    results = web.get("results") if isinstance(web.get("results"), list) else []
    return [
        {
            "url": item.get("url"),
            "title": item.get("title"),
            "text": item.get("description") or item.get("extra_snippets"),
            "published_date": item.get("age"),
            "query_intent": query,
        }
        for item in results[:max_results]
        if isinstance(item, dict)
    ]


def _search_serpapi(query: str, *, max_results: int, timeout_seconds: int) -> list[dict[str, Any]]:
    url = "https://serpapi.com/search.json?" + urlencode(
        {"engine": "google", "q": query, "api_key": os.environ.get("SERPAPI_API_KEY", ""), "num": max_results}
    )
    data = _json_get(url, headers={}, timeout_seconds=timeout_seconds)
    results = data.get("organic_results") if isinstance(data.get("organic_results"), list) else []
    return [
        {
            "url": item.get("link"),
            "title": item.get("title"),
            "text": item.get("snippet"),
            "published_date": item.get("date"),
            "query_intent": query,
        }
        for item in results[:max_results]
        if isinstance(item, dict)
    ]


def _run_firecrawl(url: str) -> list[BrandSourceObservation]:
    data = WebCollector(api_key=FIRECRAWL_API_KEY).scrape(url, crawl_subpages=False)
    return [
        _with_lab_fields(
            owned_web_source_observation(
                {
                    "url": data.canonical_url or data.url,
                    "title": data.title,
                    "markdown": data.markdown_content,
                    "error": data.error,
                },
                provider="firecrawl",
            ),
            query_intent="owned_web_capture",
            source_class="owned",
            relation_to_entity="canonical_or_audited_surface",
        )
    ]


def _run_tinyfish(url: str, timeout_seconds: int) -> list[BrandSourceObservation]:
    data = _json_post(
        "https://api.fetch.tinyfish.ai",
        {"urls": [url]},
        headers={"X-API-Key": os.environ.get("TINYFISH_API_KEY", "")},
        timeout_seconds=max(timeout_seconds, 60),
    )
    results = data.get("results") if isinstance(data.get("results"), list) else []
    if not results:
        errors = data.get("errors") if isinstance(data.get("errors"), list) else []
        error = ""
        if errors and isinstance(errors[0], dict):
            error = str(errors[0].get("error") or "")
        return [
            BrandSourceObservation(
                "owned_web",
                "error" if error else "not_observed",
                provider="tinyfish",
                reason="provider_error" if error else "no_results",
                errors=[error] if error else [],
                query_intent="owned_web_capture",
            )
        ]
    item = results[0]
    return [
        _with_lab_fields(
            owned_web_source_observation(
                {
                    "url": item.get("final_url") or item.get("url") or url,
                    "title": item.get("title"),
                    "markdown": item.get("text"),
                    "error": item.get("error") or "",
                },
                provider="tinyfish",
            ),
            query_intent="owned_web_capture",
            source_class="owned",
            relation_to_entity="canonical_or_audited_surface",
            latency_ms=int(item.get("latency_ms") or 0) if isinstance(item, dict) else 0,
        )
    ]


def _timed_provider(provider: str, fn) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        observations = fn()
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "provider": provider,
            "status": "ok",
            "elapsed_ms": elapsed_ms,
            "observation_count": len(observations),
            "observations": [
                _with_lab_fields(observation, latency_ms=observation.latency_ms or elapsed_ms)
                for observation in observations
            ],
        }
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "provider": provider,
            "status": "error",
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
            "observation_count": 1,
            "observations": [
                BrandSourceObservation(
                    "search",
                    "error",
                    provider=provider,
                    reason="provider_exception",
                    errors=[str(exc)],
                    latency_ms=elapsed_ms,
                )
            ],
        }


def _with_lab_fields(
    observation: BrandSourceObservation,
    *,
    query_intent: str | None = None,
    source_class: str | None = None,
    relation_to_entity: str | None = None,
    requires_human_review: bool | None = None,
    latency_ms: int | None = None,
    cost_estimate: float | None = None,
    diagnostics: dict[str, object] | None = None,
) -> BrandSourceObservation:
    from dataclasses import replace

    return replace(
        observation,
        query_intent=observation.query_intent or (query_intent or ""),
        source_class=observation.source_class or (source_class or ""),
        relation_to_entity=observation.relation_to_entity or (relation_to_entity or ""),
        requires_human_review=observation.requires_human_review if requires_human_review is None else requires_human_review,
        cost_estimate=observation.cost_estimate if cost_estimate is None else float(cost_estimate),
        latency_ms=observation.latency_ms or int(latency_ms or 0),
        diagnostics={**observation.diagnostics, **(diagnostics or {})},
    )


def _classify_lab_source(
    *,
    url: str,
    brand_url: str | None,
    brand_name: str,
) -> tuple[str, str, str, bool]:
    host = _host(url)
    root = _root(host)
    brand_host = _host(brand_url)
    brand_root = _root(brand_host)
    brand_token = _brand_token(brand_name)
    haystack = f"{host} {url}".lower()

    if host and host == brand_host:
        return ("owned", "audited_surface", "same_host_owned_surface", False)
    if host and brand_root and root == brand_root:
        return ("owned", "same_root_surface", "same_root_owned_surface", False)
    if any(marker in haystack for marker in TECHNICAL_MARKERS):
        return ("technical_internal", "external", "technical_artifact", False)
    if any(marker in haystack for marker in MARKETPLACE_HOST_MARKERS):
        return ("marketplace_listing", "external", "marketplace_listing_review_gated", True)
    if any(marker in haystack for marker in NOISE_HOST_MARKERS):
        return ("noise", "external", "likely_noise_source", True)
    if brand_token and brand_token in host and root and brand_root and root != brand_root:
        return ("related_unresolved", "unresolved", "same_name_different_root_domain", True)
    return ("external", "external", "external_candidate", False)


def _brand_token(brand_name: str) -> str:
    for token in (brand_name or "").lower().replace("-", " ").replace("_", " ").split():
        cleaned = "".join(ch for ch in token if ch.isalnum())
        if len(cleaned) >= 4:
            return cleaned
    return ""


def _host(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path or "").lower().strip("/")
    return host.removeprefix("www.")


def _root(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _json_post(url: str, payload: dict[str, Any], *, headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT, **headers},
        method="POST",
    )
    return _read_json(request, timeout_seconds)


def _json_get(url: str, *, headers: dict[str, str], timeout_seconds: int) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT, **headers}, method="GET")
    return _read_json(request, timeout_seconds)


def _read_json(request: Request, timeout_seconds: int) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise RuntimeError(f"HTTP {exc.code}: {body[:500]}") from exc


def _selected_providers(raw: str) -> list[str]:
    requested = [item.strip().lower() for item in raw.split(",") if item.strip()] if raw else []
    default_providers = list(DEFAULT_OWNED_FETCH_PROVIDERS) + list(DEFAULT_SEARCH_PROVIDERS)
    all_providers = list(OWNED_FETCH_PROVIDER_KEYS) + list(SEARCH_PROVIDER_KEYS)
    candidates = requested or all_providers
    if not requested:
        candidates = default_providers
    return [provider for provider in candidates if _provider_active(provider)]


def _provider_active(provider: str) -> bool:
    env_name = OWNED_FETCH_PROVIDER_KEYS.get(provider) or SEARCH_PROVIDER_KEYS.get(provider)
    return bool(env_name and _active_key(env_name))


def _discarded_providers(active: list[str]) -> list[str]:
    all_providers = list(OWNED_FETCH_PROVIDER_KEYS) + list(SEARCH_PROVIDER_KEYS)
    return [provider for provider in all_providers if provider not in active]


def _active_key(env_name: str) -> bool:
    value = os.environ.get(env_name, "").strip()
    return bool(value and not value.startswith("your-") and not value.startswith("replace-"))


def _load_cases(path: Path) -> list[LabCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("cases") if isinstance(data, dict) else data
    cases: list[LabCase] = []
    for item in rows or []:
        if isinstance(item, dict):
            cases.append(LabCase(str(item.get("brand") or item.get("name") or ""), str(item.get("url") or "")))
        elif isinstance(item, list) and len(item) >= 2:
            cases.append(LabCase(str(item[0]), str(item[1])))
    return cases


def _planned_run_payload(
    cases: list[LabCase],
    providers: list[str],
    *,
    max_queries: int = 0,
    query_profile: str = "compact",
) -> dict[str, Any]:
    owned_providers = [provider for provider in providers if provider in OWNED_FETCH_PROVIDER_KEYS]
    search_providers = [provider for provider in providers if provider in SEARCH_PROVIDER_KEYS]
    case_rows: list[dict[str, Any]] = []
    total_calls_by_provider = {provider: 0 for provider in providers}
    for case in cases:
        seed = BrandSeed(case.url, kind="url", provided_name=case.brand)
        entity = resolve_brand_seed(seed)
        plan = build_brand_source_plan(entity)
        query_requests = [request for request in plan.source_requests if request.query]
        if max_queries:
            query_requests = query_requests[: max(1, max_queries)]
        calls_by_provider = {
            provider: (1 if provider in owned_providers and entity.canonical_url else len(query_requests))
            for provider in providers
        }
        for provider, count in calls_by_provider.items():
            total_calls_by_provider[provider] += count
        case_rows.append(
            {
                "case_id": case.case_id,
                "brand": case.brand,
                "resolution_status": entity.resolution_status,
                "resolved_name": entity.resolved_name,
                "query_count": len(query_requests),
                "owned_fetch_count": 1 if entity.canonical_url else 0,
                "calls_by_provider": calls_by_provider,
                "query_intents": [request.intent for request in query_requests],
                "queries": [
                    _profiled_query(
                        request.query,
                        profile=query_profile,
                        intent=request.intent,
                        channel=request.channel,
                        case=case,
                        entity=entity,
                    )
                    for request in query_requests
                ],
            }
        )
    return {
        "version": LAB_VERSION,
        "mode": "plan_only",
        "providers": providers,
        "query_profile": query_profile,
        "discarded_providers": _discarded_providers(providers),
        "case_count": len(cases),
        "estimated_provider_call_count": sum(total_calls_by_provider.values()),
        "estimated_calls_by_provider": total_calls_by_provider,
        "cases": case_rows,
    }


def _plan_from_payload(payload: dict[str, Any]):
    from src.research.brand_intelligence import BrandSourcePlan, BrandSourceRequest

    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
    return BrandSourcePlan(
        resolution_status=plan.get("resolution_status") or "unresolved",
        resolved_name=plan.get("resolved_name") or "",
        interpretation_ready=bool(plan.get("interpretation_ready")),
        source_requests=[
            BrandSourceRequest(**item)
            for item in plan.get("source_requests", [])
            if isinstance(item, dict)
        ],
        required_missing=list(plan.get("required_missing") or []),
        limitations=list(plan.get("limitations") or []),
    )


def _case_summary(payload: dict[str, Any]) -> dict[str, Any]:
    inventory = payload.get("inventory") if isinstance(payload.get("inventory"), dict) else {}
    consensus = payload.get("source_consensus") if isinstance(payload.get("source_consensus"), dict) else {}
    return {
        "case_id": (payload.get("case") or {}).get("case_id"),
        "brand": (payload.get("case") or {}).get("brand"),
        "providers": payload.get("providers") or [],
        "observation_count": len(payload.get("observations") or []),
        "eligible_channels": inventory.get("eligible_channels") or [],
        "missing_required_channels": inventory.get("missing_required_channels") or [],
        "limitations": _lab_limitations(inventory, consensus),
        "consensus_source_count": len(consensus.get("consensus_sources") or []),
        "single_provider_source_count": len(consensus.get("single_provider_sources") or []),
        "consensus_sources": consensus.get("consensus_sources") or [],
    }


def _lab_limitations(inventory: dict[str, Any], consensus: dict[str, Any]) -> list[str]:
    limitations = list(inventory.get("limitations") or [])
    if consensus.get("consensus_sources"):
        limitations = [item for item in limitations if item != "duplicate_source_observations"]
    return limitations


def _provider_run_to_dict(run: dict[str, Any]) -> dict[str, Any]:
    payload = dict(run)
    payload["observations"] = [
        item.to_dict() if isinstance(item, BrandSourceObservation) else item
        for item in payload.get("observations", [])
    ]
    return payload


def _provider_run_to_acquisition_step(run: dict[str, Any]) -> LabAcquisitionStep:
    payload = dict(run)
    observations = payload.get("observations") if isinstance(payload.get("observations"), list) else []
    observation_rows = [
        item.to_dict() if isinstance(item, BrandSourceObservation) else item
        for item in observations
        if isinstance(item, (BrandSourceObservation, dict))
    ]
    observation_rows = [item for item in observation_rows if isinstance(item, dict)]
    error = str(payload.get("error") or "")
    status = str(payload.get("status") or "")
    step_status = "error" if status == "error" or error else ("empty" if not observation_rows else "ok")
    eligible = step_status != "error" and any(
        str(item.get("evidence_eligibility") or "") in {"eligible", "limited"} for item in observation_rows
    )
    first_row = observation_rows[0] if observation_rows else {}
    diagnostics = first_row.get("diagnostics") if isinstance(first_row.get("diagnostics"), dict) else {}
    source_classes = sorted({str(item.get("source_class") or "unknown") for item in observation_rows if item.get("source_class")})
    channels = sorted({str(item.get("channel") or "unknown") for item in observation_rows if item.get("channel")})
    return LabAcquisitionStep(
        provider=str(payload.get("provider") or "unknown"),
        status=step_status,
        cache_status="n/a",
        eligible=eligible,
        error=error or (str(first_row.get("reason") or "") if step_status == "error" else ""),
        details={
            "elapsed_ms": int(payload.get("elapsed_ms") or 0),
            "observation_count": len(observation_rows),
            "provider_variant": str(diagnostics.get("provider_variant") or payload.get("provider") or "unknown"),
            "query_intent": str(first_row.get("query_intent") or ""),
            "source_classes": source_classes,
            "channels": channels,
        },
    )


def _source_consensus(observations: list[BrandSourceObservation]) -> dict[str, Any]:
    by_url: dict[str, list[BrandSourceObservation]] = {}
    for observation in observations:
        key = _source_url_key(observation.source_url)
        if not key:
            continue
        by_url.setdefault(key, []).append(observation)

    rows: list[dict[str, Any]] = []
    for url, items in sorted(by_url.items()):
        providers = sorted({item.provider or "unknown" for item in items})
        channels = sorted({item.channel for item in items})
        source_classes = sorted({item.source_class or "unknown" for item in items})
        eligible_count = sum(
            1
            for item in items
            if item.status == "observed" and item.evidence_eligibility in {"eligible", "limited"}
        )
        rows.append(
            {
                "url": url,
                "provider_count": len(providers),
                "providers": providers,
                "channels": channels,
                "source_classes": source_classes,
                "observation_count": len(items),
                "eligible_count": eligible_count,
                "requires_human_review": any(item.requires_human_review for item in items),
                "titles": sorted({item.title for item in items if item.title}),
            }
        )
    consensus_sources = [row for row in rows if row["provider_count"] >= 2]
    single_provider_sources = [row for row in rows if row["provider_count"] == 1]
    return {
        "source_count": len(rows),
        "consensus_source_count": len(consensus_sources),
        "single_provider_source_count": len(single_provider_sources),
        "consensus_sources": consensus_sources,
        "single_provider_sources": single_provider_sources,
    }


def _provider_scores(provider_metrics: dict[str, Any], case_payloads: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    consensus_hits: dict[str, int] = {}
    for payload in case_payloads:
        consensus = payload.get("source_consensus") if isinstance(payload.get("source_consensus"), dict) else {}
        for row in consensus.get("consensus_sources") or []:
            if not isinstance(row, dict):
                continue
            for provider in row.get("providers") or []:
                consensus_hits[str(provider)] = consensus_hits.get(str(provider), 0) + 1

    scores: dict[str, dict[str, Any]] = {}
    for provider, raw_metrics in sorted(provider_metrics.items()):
        metrics = raw_metrics if isinstance(raw_metrics, dict) else {}
        source_class_counts = metrics.get("source_class_counts") if isinstance(metrics.get("source_class_counts"), dict) else {}
        latency = float(metrics.get("average_latency_ms") or 0.0)
        latency_penalty = round(min(4.0, latency / 1000.0), 4) if latency else 0.0
        owned_hits = int(source_class_counts.get("owned") or 0)
        marketplace_hits = int(source_class_counts.get("marketplace_listing") or 0)
        unresolved_hits = int(source_class_counts.get("related_unresolved") or 0)
        noise_hits = int(source_class_counts.get("noise") or 0)
        score = (
            float(metrics.get("eligible_count") or 0) * 3.0
            + float(consensus_hits.get(provider, 0)) * 2.0
            + float(owned_hits) * 1.25
            - float(metrics.get("ineligible_count") or 0) * 1.5
            - float(metrics.get("human_review_count") or 0) * 1.0
            - float(marketplace_hits) * 1.0
            - float(unresolved_hits) * 2.0
            - float(noise_hits) * 2.0
            - float(metrics.get("error_count") or 0) * 3.0
            - latency_penalty
        )
        scores[provider] = {
            "score": round(score, 4),
            "eligible_count": int(metrics.get("eligible_count") or 0),
            "consensus_hits": int(consensus_hits.get(provider, 0)),
            "owned_hits": owned_hits,
            "marketplace_hits": marketplace_hits,
            "related_unresolved_hits": unresolved_hits,
            "noise_hits": noise_hits,
            "ineligible_count": int(metrics.get("ineligible_count") or 0),
            "human_review_count": int(metrics.get("human_review_count") or 0),
            "error_count": int(metrics.get("error_count") or 0),
            "latency_penalty": latency_penalty,
        }
    return dict(sorted(scores.items(), key=lambda item: item[1]["score"], reverse=True))


def _render_summary_md(summary: dict[str, Any]) -> str:
    provider_metrics = ((summary.get("bakeoff") or {}).get("provider_metrics") or {})
    provider_scores = summary.get("provider_scores") if isinstance(summary.get("provider_scores"), dict) else {}
    provider_acquisition = summary.get("provider_acquisition") if isinstance(summary.get("provider_acquisition"), list) else []
    lines = [
        "# Search Enrichment Lab Summary",
        "",
        f"- version: `{summary.get('version')}`",
        f"- created_at: `{summary.get('created_at')}`",
        f"- providers: `{', '.join(summary.get('providers') or [])}`",
        f"- cases: `{summary.get('case_count')}`",
        "",
        "| Case | Observations | Consensus | Single-provider | Eligible channels | Missing required |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for case in summary.get("cases") or []:
        lines.append(
            "| {case_id} | {observation_count} | {consensus} | {single_provider} | {eligible} | {missing} |".format(
                case_id=case.get("case_id") or "",
                observation_count=case.get("observation_count") or 0,
                consensus=case.get("consensus_source_count") or 0,
                single_provider=case.get("single_provider_source_count") or 0,
                eligible=", ".join(case.get("eligible_channels") or []),
                missing=", ".join(case.get("missing_required_channels") or []),
            )
        )
    lines.append("")
    lines.extend(
        [
            "## Provider Metrics",
            "",
            "| Provider | Observed | Eligible | Limited | Ineligible | Errors | Review | Avg latency | Total cost | Avg cost | Channels | Source classes | Avg confidence |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |",
        ]
    )
    for provider, metrics in sorted(provider_metrics.items()):
        source_classes = metrics.get("source_class_counts") if isinstance(metrics.get("source_class_counts"), dict) else {}
        lines.append(
            "| {provider} | {observed} | {eligible} | {limited} | {ineligible} | {errors} | {review} | {latency} | {total_cost} | {avg_cost} | {channels} | {source_classes} | {confidence} |".format(
                provider=provider,
                observed=metrics.get("observed_count") or 0,
                eligible=metrics.get("eligible_count") or 0,
                limited=metrics.get("limited_count") or 0,
                ineligible=metrics.get("ineligible_count") or 0,
                errors=metrics.get("error_count") or 0,
                review=metrics.get("human_review_count") or 0,
                latency=metrics.get("average_latency_ms") or 0,
                total_cost=metrics.get("total_cost_estimate") or 0,
                avg_cost=metrics.get("average_cost_estimate") or 0,
                channels=", ".join(metrics.get("covered_channels") or []),
                source_classes=", ".join(f"{key}:{value}" for key, value in sorted(source_classes.items())),
                confidence=metrics.get("average_confidence") or 0,
            )
        )
    lines.append("")
    if provider_acquisition:
        lines.extend(
            [
                "## Provider Acquisition Steps",
                "",
                "| Case | Provider | Status | Eligible | Cache | Observations | Latency | Error |",
                "| --- | --- | --- | ---: | --- | ---: | ---: | --- |",
            ]
        )
        for row in provider_acquisition:
            lines.append(
                "| {case_id} | {provider} | {status} | {eligible} | {cache_status} | {observations} | {latency} | {error} |".format(
                    case_id=row.get("case_id") or "",
                    provider=row.get("provider") or "",
                    status=row.get("status") or "",
                    eligible="yes" if row.get("eligible") else "no",
                    cache_status=row.get("cache_status") or "",
                    observations=row.get("observation_count") or 0,
                    latency=row.get("elapsed_ms") or 0,
                    error=(row.get("error") or "").replace("|", "\\|")[:160],
                )
            )
        lines.append("")
    if provider_scores:
        lines.extend(
            [
                "## Experimental Provider Score",
                "",
                "| Provider | Score | Eligible | Consensus | Owned | Marketplace | Unresolved | Noise | Ineligible | Review | Errors | Latency penalty |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for provider, score in provider_scores.items():
            lines.append(
                "| {provider} | {value} | {eligible} | {consensus} | {owned} | {marketplace} | {unresolved} | {noise} | {ineligible} | {review} | {errors} | {latency} |".format(
                    provider=provider,
                    value=score.get("score") or 0,
                    eligible=score.get("eligible_count") or 0,
                    consensus=score.get("consensus_hits") or 0,
                    owned=score.get("owned_hits") or 0,
                    marketplace=score.get("marketplace_hits") or 0,
                    unresolved=score.get("related_unresolved_hits") or 0,
                    noise=score.get("noise_hits") or 0,
                    ineligible=score.get("ineligible_count") or 0,
                    review=score.get("human_review_count") or 0,
                    errors=score.get("error_count") or 0,
                    latency=score.get("latency_penalty") or 0,
                )
            )
        lines.extend(
            [
                "",
                "Formula: `eligible*3 + consensus*2 + owned*1.25 - ineligible*1.5 - review - marketplace - unresolved*2 - noise*2 - errors*3 - latency_penalty`.",
                "",
            ]
        )
    discarded = summary.get("discarded_providers") or []
    if discarded:
        lines.extend(
            [
                "## Discarded Providers",
                "",
                ", ".join(f"`{provider}`" for provider in discarded),
                "",
            ]
        )
    consensus_rows = _summary_consensus_rows(summary)
    if consensus_rows:
        lines.extend(
            [
                "## Consensus Sources",
                "",
                "| Case | Providers | URL | Classes |",
                "| --- | --- | --- | --- |",
            ]
        )
        for row in consensus_rows:
            lines.append(
                "| {case_id} | {providers} | {url} | {classes} |".format(
                    case_id=row["case_id"],
                    providers=", ".join(row["providers"]),
                    url=row["url"],
                    classes=", ".join(row["source_classes"]),
                )
            )
        lines.append("")
    error_rows = _provider_error_rows(summary)
    if error_rows:
        lines.extend(
            [
                "## Provider Errors",
                "",
                "| Case | Provider | Error |",
                "| --- | --- | --- |",
            ]
        )
        for row in error_rows:
            lines.append(
                "| {case_id} | {provider} | {error} |".format(
                    case_id=row["case_id"],
                    provider=row["provider"],
                    error=row["error"].replace("|", "\\|")[:240],
                )
            )
        lines.append("")
    return "\n".join(lines)


def _summary_consensus_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in summary.get("cases") or []:
        for row in case.get("consensus_sources") or []:
            rows.append({"case_id": case.get("case_id") or "", **row})
    return rows


def _provider_acquisition_rows(case_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in case_payloads:
        case_id = str((payload.get("case") or {}).get("case_id") or "")
        for step in payload.get("acquisition_steps") or []:
            if not isinstance(step, dict):
                continue
            details = step.get("details") if isinstance(step.get("details"), dict) else {}
            rows.append(
                {
                    "case_id": case_id,
                    "provider": str(step.get("provider") or "unknown"),
                    "status": str(step.get("status") or "unknown"),
                    "eligible": bool(step.get("eligible")),
                    "cache_status": str(step.get("cache_status") or ""),
                    "observation_count": int(details.get("observation_count") or 0),
                    "elapsed_ms": int(details.get("elapsed_ms") or 0),
                    "error": str(step.get("error") or ""),
                }
            )
    return rows


def _source_url_key(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).lower().removeprefix("www.")
    path = parsed.path if parsed.netloc else ""
    normalized_path = path.rstrip("/")
    return f"https://{host}{normalized_path}" if host else ""


def _provider_error_rows(summary: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in ((summary.get("bakeoff") or {}).get("results") or []):
        case_id = str(result.get("case_id") or "")
        inventory = result.get("inventory") if isinstance(result.get("inventory"), dict) else {}
        for observation in inventory.get("observations") or []:
            if not isinstance(observation, dict) or observation.get("status") != "error":
                continue
            error = "; ".join(str(item) for item in observation.get("errors") or [] if str(item).strip())
            rows.append(
                {
                    "case_id": case_id,
                    "provider": str(observation.get("provider") or "unknown"),
                    "error": error or str(observation.get("reason") or "provider_error"),
                }
            )
    return rows


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value or "case")
    return "-".join(part for part in cleaned.split("-") if part) or "case"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-file", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("out/search_enrichment_lab"))
    parser.add_argument("--providers", default="", help="Comma-separated provider allowlist. Defaults to active keys.")
    parser.add_argument("--results", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-cases", type=int, default=0, help="Limit cases for low-cost smoke tests.")
    parser.add_argument("--max-queries", type=int, default=0, help="Limit query requests per case for low-cost smoke tests.")
    parser.add_argument(
        "--query-profile",
        choices=("compact", "rich"),
        default="compact",
        help="Use compact generated queries or richer research prompts.",
    )
    parser.add_argument("--list-providers", action="store_true", help="Print active/discarded providers without network calls.")
    parser.add_argument("--plan-only", action="store_true", help="Print estimated calls/cases without network calls.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
