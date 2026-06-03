"""Input collection orchestration for Brand3 analysis runs."""

from __future__ import annotations

from dataclasses import dataclass
import os

from src.collectors.competitor_collector import (
    CompetitorCollector,
    CompetitorData,
    CompetitorInfo,
    ComparisonResult,
)
from src.collectors.context_collector import ContextCollector, ContextData
from src.collectors.exa_collector import ExaCollector, ExaData, ExaResult
from src.collectors.parallel_shadow_collector import ParallelShadowCollector, ParallelShadowData
from src.collectors.social_collector import PlatformMetrics, SocialData
from src.collectors.web_collector import WebCollector, WebData
from src.config import BRAND3_CACHE_TTL_HOURS, EXA_API_KEY, FIRECRAWL_API_KEY
from src.storage.sqlite_store import SQLiteStore


@dataclass
class RunStorage:
    store: SQLiteStore | None
    run_id: int | None


@dataclass
class RawInputs:
    context_data: ContextData | None
    web_data: WebData | None
    effective_brand_url: str
    exa_data: ExaData | None
    parallel_shadow_data: ParallelShadowData | None
    social_data: SocialData | None
    social_limitation: str | None
    competitor_data: CompetitorData | None
    raw_input_cache: dict[str, str]
    web_collector: WebCollector
    exa_collector: ExaCollector


def from_web_payload(payload: dict | None) -> WebData | None:
    if not payload:
        return None
    return WebData(**payload)


def from_exa_payload(payload: dict | None) -> ExaData | None:
    if not payload:
        return None
    return ExaData(
        brand_name=payload.get("brand_name", ""),
        mentions=[ExaResult(**item) for item in payload.get("mentions", [])],
        competitors=[ExaResult(**item) for item in payload.get("competitors", [])],
        ai_visibility_results=[ExaResult(**item) for item in payload.get("ai_visibility_results", [])],
        news=[ExaResult(**item) for item in payload.get("news", [])],
        raw_responses=payload.get("raw_responses", {}),
        diagnostics=payload.get("diagnostics", {}),
    )


def from_parallel_shadow_payload(payload: dict | None) -> dict | None:
    return payload if isinstance(payload, dict) else None


def from_social_payload(payload: dict | None) -> SocialData | None:
    if not payload:
        return None
    return SocialData(
        brand_name=payload.get("brand_name", ""),
        platforms={
            name: PlatformMetrics(**metrics)
            for name, metrics in payload.get("platforms", {}).items()
        },
        profiles_found=payload.get("profiles_found", []),
        total_followers=payload.get("total_followers", 0),
        avg_post_frequency=payload.get("avg_post_frequency", 0.0),
        most_active_platform=payload.get("most_active_platform", ""),
        error=payload.get("error", ""),
    )


def from_competitor_payload(payload: dict | None) -> CompetitorData | None:
    if not payload:
        return None
    return CompetitorData(
        brand_name=payload.get("brand_name", ""),
        brand_url=payload.get("brand_url", ""),
        competitors=[
            CompetitorInfo(
                name=item.get("name", ""),
                url=item.get("url", ""),
                exa_result=ExaResult(**item["exa_result"]) if item.get("exa_result") else None,
                web_data=WebData(**item["web_data"]) if item.get("web_data") else None,
                error=item.get("error", ""),
            )
            for item in payload.get("competitors", [])
        ],
        comparisons=[ComparisonResult(**item) for item in payload.get("comparisons", [])],
        brand_web=WebData(**payload["brand_web"]) if payload.get("brand_web") else None,
        errors=payload.get("errors", []),
    )


def from_context_payload(payload: dict | None) -> ContextData | None:
    if not payload:
        return None
    return ContextData(**payload)


def load_cached(store, brand_name: str, url: str, source: str, ttl_hours: int, decoder):
    if not store:
        return None
    try:
        payload = store.get_latest_raw_input(
            brand_name=brand_name,
            url=url,
            source=source,
            max_age_hours=ttl_hours,
        )
    except Exception as e:
        print(f"  Cache {source}: skipped ({e})")
        return None
    if not payload:
        return None
    try:
        return decoder(payload)
    except Exception as e:
        print(f"  Cache {source}: invalid payload ({e})")
        return None


def store_safely(store, action: str, fn) -> None:
    if not store:
        return
    try:
        fn()
    except Exception as e:
        print(f"  Storage {action}: skipped ({e})")


def start_analysis_run(
    brand_name: str,
    url: str,
    *,
    use_llm: bool,
    use_social: bool,
    db_path: str,
) -> RunStorage:
    try:
        store = SQLiteStore(db_path)
        brand_id = store.upsert_brand(brand_name, url)
        run_id = store.create_run(brand_id, brand_name, url, use_llm, use_social)
        return RunStorage(store=store, run_id=run_id)
    except Exception as e:
        print(f"  Storage: disabled ({e})")
        return RunStorage(store=None, run_id=None)


def _cache_reader(
    *,
    store: SQLiteStore | None,
    brand_name: str,
    url: str,
    refresh: bool,
):
    def cache_read(source: str, ttl_hours: int, decoder):
        if refresh:
            return None
        return load_cached(store, brand_name, url, source, ttl_hours, decoder)

    return cache_read


def _collect_context_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    url: str,
    cache_read,
    raw_input_cache: dict[str, str],
    context_evidence_builder,
    context_collector_cls,
) -> ContextData:
    context_data = cache_read("context", 24, from_context_payload)
    if context_data:
        raw_input_cache["context"] = "hit"
        print(
            "  Context: cache hit"
            f" (score={context_data.context_score:.0f}, confidence={context_data.confidence:.2f})"
        )
        if run_id:
            store_safely(store, "context cache save", lambda: store.save_raw_input(run_id, "context", context_data))
            store_safely(
                store,
                "context cache evidence save",
                lambda: store.save_evidence_items(run_id, context_evidence_builder(context_data)),
            )
        return context_data

    raw_input_cache["context"] = "miss"
    context_data = context_collector_cls().scan(url)
    print(
        "  Context:"
        f" score={context_data.context_score:.0f}"
        f" coverage={context_data.coverage:.2f}"
        f" confidence={context_data.confidence:.2f}"
    )
    if run_id:
        store_safely(store, "context save", lambda: store.save_raw_input(run_id, "context", context_data))
        store_safely(
            store,
            "context evidence save",
            lambda: store.save_evidence_items(run_id, context_evidence_builder(context_data)),
        )
    return context_data


def _collect_web_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    url: str,
    cache_read,
    raw_input_cache: dict[str, str],
    web_collector_cls,
) -> tuple[WebData, WebCollector]:
    web_collector = web_collector_cls(api_key=FIRECRAWL_API_KEY)
    web_data = cache_read("web", BRAND3_CACHE_TTL_HOURS, from_web_payload)
    if web_data:
        raw_input_cache["web"] = "hit"
        print(f"  Web: cache hit ({len(web_data.markdown_content)} chars)")
        if run_id:
            store_safely(store, "web cache save", lambda: store.save_raw_input(run_id, "web", web_data))
        return web_data, web_collector

    raw_input_cache["web"] = "miss"
    web_data = web_collector.scrape(url)
    print(f"  Web: {len(web_data.markdown_content)} chars scraped")
    if run_id:
        store_safely(store, "web save", lambda: store.save_raw_input(run_id, "web", web_data))
    return web_data, web_collector


def _collect_exa_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    effective_brand_url: str,
    cache_read,
    raw_input_cache: dict[str, str],
    exa_collector_cls,
) -> tuple[ExaData, ExaCollector]:
    exa_collector = exa_collector_cls(api_key=EXA_API_KEY)
    exa_data = cache_read("exa", BRAND3_CACHE_TTL_HOURS, from_exa_payload)
    if exa_data:
        raw_input_cache["exa"] = "hit"
        print(f"  Exa: cache hit ({len(exa_data.mentions)} mentions, {len(exa_data.news)} news)")
        if run_id:
            store_safely(store, "exa cache save", lambda: store.save_raw_input(run_id, "exa", exa_data))
        return exa_data, exa_collector

    raw_input_cache["exa"] = "miss"
    exa_data = exa_collector.collect_brand_data(brand_name, effective_brand_url)
    diagnostics = dict(exa_data.diagnostics or {})
    failed_intents = diagnostics.get("failed_intents") or []
    no_result_intents = diagnostics.get("no_result_intents") or []
    if failed_intents:
        raw_input_cache["exa"] = "partial"
        print(
            f"  Exa: partial ({len(exa_data.mentions)} mentions, {len(exa_data.news)} news)"
            f" failed_intents={','.join(failed_intents)}"
        )
    elif no_result_intents:
        print(
            f"  Exa: {len(exa_data.mentions)} mentions, {len(exa_data.news)} news"
            f" no_results={','.join(no_result_intents)}"
        )
    else:
        print(f"  Exa: {len(exa_data.mentions)} mentions, {len(exa_data.news)} news")
    if run_id:
        store_safely(store, "exa save", lambda: store.save_raw_input(run_id, "exa", exa_data))
    return exa_data, exa_collector


def _collect_parallel_shadow_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    effective_brand_url: str,
    cache_read,
    raw_input_cache: dict[str, str],
    parallel_shadow_collector_cls=ParallelShadowCollector,
) -> ParallelShadowData | None:
    if not _parallel_shadow_enabled():
        raw_input_cache["parallel_shadow"] = "disabled"
        return None

    cached = cache_read("parallel_shadow", BRAND3_CACHE_TTL_HOURS, from_parallel_shadow_payload)
    if cached:
        raw_input_cache["parallel_shadow"] = "hit"
        if run_id:
            store_safely(store, "parallel shadow cache save", lambda: store.save_raw_input(run_id, "parallel_shadow", cached))
        return ParallelShadowData.from_dict(
            {
                **cached,
                "brand_name": cached.get("brand_name") or brand_name,
                "brand_url": cached.get("brand_url") or effective_brand_url,
            }
        )

    collector = parallel_shadow_collector_cls()
    shadow_data = collector.collect(brand_name, effective_brand_url)
    raw_input_cache["parallel_shadow"] = shadow_data.status
    summary = shadow_data.summary()
    print(
        "  Parallel shadow:"
        f" status={shadow_data.status}"
        f" results={summary['result_total']}"
        f" domains={summary['unique_domain_count']}"
    )
    if run_id:
        store_safely(store, "parallel shadow save", lambda: store.save_raw_input(run_id, "parallel_shadow", shadow_data.to_dict()))
    return shadow_data


def _parallel_shadow_enabled() -> bool:
    return os.environ.get("BRAND3_PARALLEL_SHADOW_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _collect_social_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    web_data: WebData,
    use_social: bool,
    cache_read,
    raw_input_cache: dict[str, str],
    social_collector,
) -> tuple[SocialData | None, str | None]:
    if not use_social:
        raw_input_cache["social"] = "skipped"
        return None, None

    social_data = cache_read("social", BRAND3_CACHE_TTL_HOURS, from_social_payload)
    if social_data:
        raw_input_cache["social"] = "hit"
        print(f"  Social: cache hit ({len(social_data.platforms)} platforms, {social_data.total_followers:,} total followers)")
        if run_id:
            store_safely(store, "social cache save", lambda: store.save_raw_input(run_id, "social", social_data))
        return social_data, None

    raw_input_cache["social"] = "miss"
    try:
        social_data, social_limitation = social_collector(
            brand_name,
            web_data.markdown_content,
            api_key=FIRECRAWL_API_KEY,
        )
        platforms_count = len(social_data.platforms)
        if social_limitation:
            raw_input_cache["social"] = social_limitation
            print(f"  Social: {social_limitation} - continuing without blocking analysis")
        else:
            print(f"  Social: {platforms_count} platforms, {social_data.total_followers:,} total followers")
        if run_id:
            store_safely(store, "social save", lambda: store.save_raw_input(run_id, "social", social_data))
        return social_data, social_limitation
    except Exception as e:
        raw_input_cache["social"] = "error"
        print(f"  Social: error - {e}")
        social_data = SocialData(brand_name=brand_name, error=str(e))
        if run_id:
            store_safely(store, "social error save", lambda: store.save_raw_input(run_id, "social", social_data))
        return social_data, "error"


def _collect_competitor_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    effective_brand_url: str,
    web_data: WebData,
    exa_data: ExaData,
    exa_collector: ExaCollector,
    web_collector: WebCollector,
    use_competitors: bool,
    cache_read,
    raw_input_cache: dict[str, str],
) -> CompetitorData | None:
    if not use_competitors:
        raw_input_cache["competitors"] = "skipped"
        print("  Competitors: skipped (--fast mode)")
        return None

    competitor_collector = CompetitorCollector(
        exa_collector=exa_collector,
        web_collector=web_collector,
        max_competitors=5,
    )
    competitor_data = cache_read("competitors", BRAND3_CACHE_TTL_HOURS, from_competitor_payload)
    if competitor_data:
        raw_input_cache["competitors"] = "hit"
        print(f"  Competitors: cache hit ({len(competitor_data.competitors)} competitors)")
        if run_id:
            store_safely(
                store,
                "competitor cache save",
                lambda: store.save_raw_input(run_id, "competitors", competitor_data),
            )
        return competitor_data

    raw_input_cache["competitors"] = "miss"
    competitor_data = competitor_collector.collect(
        brand_name=brand_name,
        brand_url=effective_brand_url,
        brand_web=web_data,
        exa_data=exa_data,
    )
    if run_id:
        store_safely(
            store,
            "competitor save",
            lambda: store.save_raw_input(run_id, "competitors", competitor_data),
        )
    return competitor_data


def collect_raw_inputs(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    url: str,
    refresh: bool,
    use_social: bool,
    use_competitors: bool,
    effective_brand_url_builder,
    context_evidence_builder,
    social_collector,
    context_collector_cls=ContextCollector,
    web_collector_cls=WebCollector,
    exa_collector_cls=ExaCollector,
) -> RawInputs:
    raw_input_cache: dict[str, str] = {}
    cache_read = _cache_reader(
        store=store,
        brand_name=brand_name,
        url=url,
        refresh=refresh,
    )
    context_data = _collect_context_input(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        url=url,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        context_evidence_builder=context_evidence_builder,
        context_collector_cls=context_collector_cls,
    )
    web_data, web_collector = _collect_web_input(
        store=store,
        run_id=run_id,
        url=url,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        web_collector_cls=web_collector_cls,
    )
    effective_brand_url = effective_brand_url_builder(url, web_data)
    exa_data, exa_collector = _collect_exa_input(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        effective_brand_url=effective_brand_url,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        exa_collector_cls=exa_collector_cls,
    )
    parallel_shadow_data = _collect_parallel_shadow_input(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        effective_brand_url=effective_brand_url,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
    )
    social_data, social_limitation = _collect_social_input(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        web_data=web_data,
        use_social=use_social,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        social_collector=social_collector,
    )
    competitor_data = _collect_competitor_input(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        effective_brand_url=effective_brand_url,
        web_data=web_data,
        exa_data=exa_data,
        exa_collector=exa_collector,
        web_collector=web_collector,
        use_competitors=use_competitors,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
    )
    return RawInputs(
        context_data=context_data,
        web_data=web_data,
        effective_brand_url=effective_brand_url,
        exa_data=exa_data,
        parallel_shadow_data=parallel_shadow_data,
        social_data=social_data,
        social_limitation=social_limitation,
        competitor_data=competitor_data,
        raw_input_cache=raw_input_cache,
        web_collector=web_collector,
        exa_collector=exa_collector,
    )
