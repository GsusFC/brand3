"""Input collection orchestration for Brand3 analysis runs."""

from __future__ import annotations

from dataclasses import dataclass, field
import os

from src.collectors.competitor_collector import (
    CompetitorCollector,
    CompetitorData,
    CompetitorInfo,
    ComparisonResult,
)
from src.collectors.context_collector import ContextCollector, ContextData
from src.collectors.exa_collector import ExaCollector, ExaData, ExaResult
from src.collectors.hyperbrowser_collector import HyperbrowserCollector, HyperbrowserFetchData
from src.collectors.parallel_shadow_collector import ParallelShadowCollector, ParallelShadowData
from src.collectors.social_collector import PlatformMetrics, SocialData
from src.collectors.web_collector import WebCollector, WebData
from src.config import (
    BRAND3_CACHE_TTL_HOURS,
    BRAND3_HYPERBROWSER_ENABLED,
    EXA_API_KEY,
    FIRECRAWL_API_KEY,
)
from src.storage.sqlite_store import SQLiteStore, _MalformedJSONPayload


@dataclass
class RunStorage:
    store: SQLiteStore | None
    run_id: int | None


@dataclass
class RawInputs:
    context_data: ContextData | None
    web_data: WebData | None
    hyperbrowser_data: HyperbrowserFetchData | None
    effective_brand_url: str
    exa_data: ExaData | None
    parallel_shadow_data: ParallelShadowData | None
    social_data: SocialData | None
    social_limitation: str | None
    competitor_data: CompetitorData | None
    raw_input_cache: dict[str, str]
    acquisition_steps: dict[str, "AcquisitionResult"]
    web_collector: WebCollector
    exa_collector: ExaCollector


@dataclass(frozen=True)
class AcquisitionResult:
    source: str
    status: str
    cache_status: str
    eligible: bool
    error: str | None = None
    details: dict[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "source": self.source,
            "status": self.status,
            "cache_status": self.cache_status,
            "eligible": self.eligible,
            "error": self.error,
            "details": dict(self.details),
        }


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


def from_hyperbrowser_payload(payload: dict | None) -> HyperbrowserFetchData | None:
    if not payload:
        return None
    return HyperbrowserFetchData(**payload)


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


def _record_acquisition(
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    *,
    source: str,
    status: str,
    cache_status: str,
    eligible: bool,
    error: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    if acquisition_steps is None:
        return
    existing = acquisition_steps.get(source)
    merged_details = dict(existing.details) if existing else {}
    merged_details.update(details or {})
    acquisition_steps[source] = AcquisitionResult(
        source=source,
        status=status,
        cache_status=cache_status,
        eligible=eligible,
        error=error,
        details=merged_details,
    )


def _set_acquisition_state(
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None,
    *,
    source: str,
    raw_cache_status: str,
    status: str,
    cache_status: str,
    eligible: bool,
    error: str | None = None,
    details: dict[str, object] | None = None,
) -> None:
    raw_input_cache[source] = raw_cache_status
    _record_acquisition(
        acquisition_steps,
        source=source,
        status=status,
        cache_status=cache_status,
        eligible=eligible,
        error=error,
        details=details,
    )


def _record_storage_error(
    acquisition_steps: dict[str, AcquisitionResult] | None,
    *,
    source: str | None,
    action: str,
    error: str,
) -> None:
    if acquisition_steps is None or not source:
        return
    existing = acquisition_steps.get(source)
    details = dict(existing.details) if existing else {}
    storage_errors = list(details.get("storage_errors") or [])
    storage_errors.append({"action": action, "error": error})
    details["storage_errors"] = storage_errors
    acquisition_steps[source] = AcquisitionResult(
        source=source,
        status=existing.status if existing else "storage_error",
        cache_status=existing.cache_status if existing else "unknown",
        eligible=existing.eligible if existing else True,
        error=existing.error if existing else None,
        details=details,
    )


def _merge_acquisition_details(
    acquisition_steps: dict[str, AcquisitionResult] | None,
    *,
    source: str,
    details: dict[str, object],
) -> None:
    if acquisition_steps is None:
        return
    existing = acquisition_steps.get(source)
    merged_details = dict(existing.details) if existing else {}
    merged_details.update(details)
    acquisition_steps[source] = AcquisitionResult(
        source=source,
        status=existing.status if existing else "unknown",
        cache_status=existing.cache_status if existing else "unknown",
        eligible=existing.eligible if existing else True,
        error=existing.error if existing else None,
        details=merged_details,
    )


def _raw_payload_ref(run_id: int, source: str) -> dict[str, object]:
    return {
        "store": "raw_inputs",
        "run_id": run_id,
        "source": source,
    }


def load_cached(
    store,
    brand_name: str,
    url: str,
    source: str,
    ttl_hours: int,
    decoder,
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
):
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
        _record_acquisition(
            acquisition_steps,
            source=source,
            status="cache_error",
            cache_status="error",
            eligible=True,
            details={"cache_error": str(e)},
        )
        print(f"  Cache {source}: skipped ({e})")
        return None
    if not payload:
        return None
    if isinstance(payload, _MalformedJSONPayload):
        _record_acquisition(
            acquisition_steps,
            source=source,
            status="cache_invalid",
            cache_status="invalid",
            eligible=True,
            details={
                "cache_error": payload.error,
                "payload_field": payload.field,
                "raw_json": payload.raw_json,
            },
        )
        print(f"  Cache {source}: invalid payload ({payload.error})")
        return None
    try:
        return decoder(payload)
    except Exception as e:
        _record_acquisition(
            acquisition_steps,
            source=source,
            status="cache_invalid",
            cache_status="invalid",
            eligible=True,
            details={"cache_error": str(e)},
        )
        print(f"  Cache {source}: invalid payload ({e})")
        return None


def store_safely(
    store,
    action: str,
    fn,
    *,
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    source: str | None = None,
) -> bool:
    if not store:
        return False
    try:
        fn()
    except Exception as e:
        _record_storage_error(
            acquisition_steps,
            source=source,
            action=action,
            error=str(e),
        )
        print(f"  Storage {action}: skipped ({e})")
        return False
    return True


def _save_raw_input_safely(
    store,
    run_id: int | None,
    source: str,
    payload,
    *,
    action: str | None = None,
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
) -> bool:
    if not run_id:
        return False
    saved = store_safely(
        store,
        action or f"{source} save",
        lambda: store.save_raw_input(run_id, source, payload),
        acquisition_steps=acquisition_steps,
        source=source,
    )
    if saved:
        _merge_acquisition_details(
            acquisition_steps,
            source=source,
            details={"raw_payload_ref": _raw_payload_ref(run_id, source)},
        )
    return saved


def _use_cached_input(
    *,
    store,
    run_id: int | None,
    source: str,
    payload,
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    details: dict[str, object] | None = None,
    action: str | None = None,
    message: str | None = None,
):
    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source=source,
        raw_cache_status="hit",
        status="hit",
        cache_status="hit",
        eligible=True,
        details=details,
    )
    if message:
        print(message)
    if run_id:
        _save_raw_input_safely(
            store,
            run_id,
            source,
            payload,
            action=action or f"{source} cache save",
            acquisition_steps=acquisition_steps,
        )
    return payload


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
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
):
    def cache_read(source: str, ttl_hours: int, decoder):
        if refresh:
            return None
        return load_cached(store, brand_name, url, source, ttl_hours, decoder, acquisition_steps)

    return cache_read


def _collect_context_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    url: str,
    cache_read,
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    context_evidence_builder,
    context_collector_cls,
) -> ContextData:
    context_data = cache_read("context", 24, from_context_payload)
    if context_data:
        _use_cached_input(
            store=store,
            run_id=run_id,
            source="context",
            payload=context_data,
            raw_input_cache=raw_input_cache,
            acquisition_steps=acquisition_steps,
            details={
                "score": context_data.context_score,
                "confidence": context_data.confidence,
            },
            action="context cache save",
            message=(
                "  Context: cache hit"
                f" (score={context_data.context_score:.0f}, confidence={context_data.confidence:.2f})"
            ),
        )
        if run_id:
            store_safely(
                store,
                "context cache evidence save",
                lambda: store.save_evidence_items(run_id, context_evidence_builder(context_data)),
                acquisition_steps=acquisition_steps,
                source="context",
            )
        return context_data

    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source="context",
        raw_cache_status="miss",
        status="fetched",
        cache_status="miss",
        eligible=True,
    )
    context_data = context_collector_cls().scan(url)
    print(
        "  Context:"
        f" score={context_data.context_score:.0f}"
        f" coverage={context_data.coverage:.2f}"
        f" confidence={context_data.confidence:.2f}"
    )
    if run_id:
        _save_raw_input_safely(
            store,
            run_id,
            "context",
            context_data,
            action="context save",
            acquisition_steps=acquisition_steps,
        )
        store_safely(
            store,
            "context evidence save",
            lambda: store.save_evidence_items(run_id, context_evidence_builder(context_data)),
            acquisition_steps=acquisition_steps,
            source="context",
        )
    return context_data


def _collect_web_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    url: str,
    cache_read,
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    web_collector_cls,
) -> tuple[WebData, WebCollector]:
    web_collector = web_collector_cls(api_key=FIRECRAWL_API_KEY)
    web_data = cache_read("web", BRAND3_CACHE_TTL_HOURS, from_web_payload)
    if web_data:
        _use_cached_input(
            store=store,
            run_id=run_id,
            source="web",
            payload=web_data,
            raw_input_cache=raw_input_cache,
            acquisition_steps=acquisition_steps,
            details={"chars": len(web_data.markdown_content)},
            action="web cache save",
            message=f"  Web: cache hit ({len(web_data.markdown_content)} chars)",
        )
        return web_data, web_collector

    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source="web",
        raw_cache_status="miss",
        status="fetched",
        cache_status="miss",
        eligible=True,
    )
    web_data = web_collector.scrape(url)
    print(f"  Web: {len(web_data.markdown_content)} chars scraped")
    if getattr(web_data, "capture_obstruction", ""):
        _set_acquisition_state(
            raw_input_cache,
            acquisition_steps,
            source="web",
            raw_cache_status="obstructed",
            status="obstructed",
            cache_status="miss",
            eligible=False,
            details={"capture_obstruction": web_data.capture_obstruction},
        )
        print(f"  Web: obstructed ({web_data.capture_obstruction})")
    if run_id:
        _save_raw_input_safely(
            store,
            run_id,
            "web",
            web_data,
            action="web save",
            acquisition_steps=acquisition_steps,
        )
    return web_data, web_collector


def _collect_exa_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    effective_brand_url: str,
    cache_read,
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    exa_collector_cls,
) -> tuple[ExaData, ExaCollector]:
    exa_collector = exa_collector_cls(api_key=EXA_API_KEY)
    exa_data = cache_read("exa", BRAND3_CACHE_TTL_HOURS, from_exa_payload)
    if exa_data:
        _use_cached_input(
            store=store,
            run_id=run_id,
            source="exa",
            payload=exa_data,
            raw_input_cache=raw_input_cache,
            acquisition_steps=acquisition_steps,
            details={
                "mentions": len(exa_data.mentions),
                "news": len(exa_data.news),
            },
            action="exa cache save",
            message=f"  Exa: cache hit ({len(exa_data.mentions)} mentions, {len(exa_data.news)} news)",
        )
        return exa_data, exa_collector

    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source="exa",
        raw_cache_status="miss",
        status="fetched",
        cache_status="miss",
        eligible=True,
    )
    exa_data = exa_collector.collect_brand_data(brand_name, effective_brand_url)
    diagnostics = dict(exa_data.diagnostics or {})
    failed_intents = diagnostics.get("failed_intents") or []
    no_result_intents = diagnostics.get("no_result_intents") or []
    if failed_intents:
        _set_acquisition_state(
            raw_input_cache,
            acquisition_steps,
            source="exa",
            raw_cache_status="partial",
            status="partial",
            cache_status="miss",
            eligible=True,
            details={"failed_intents": list(failed_intents)},
        )
        print(
            f"  Exa: partial ({len(exa_data.mentions)} mentions, {len(exa_data.news)} news)"
            f" failed_intents={','.join(failed_intents)}"
        )
    elif no_result_intents:
        _set_acquisition_state(
            raw_input_cache,
            acquisition_steps,
            source="exa",
            raw_cache_status="miss",
            status="empty",
            cache_status="miss",
            eligible=True,
            details={"no_result_intents": list(no_result_intents)},
        )
        print(
            f"  Exa: {len(exa_data.mentions)} mentions, {len(exa_data.news)} news"
            f" no_results={','.join(no_result_intents)}"
        )
    else:
        _set_acquisition_state(
            raw_input_cache,
            acquisition_steps,
            source="exa",
            raw_cache_status="miss",
            status="ok",
            cache_status="miss",
            eligible=True,
        )
        print(f"  Exa: {len(exa_data.mentions)} mentions, {len(exa_data.news)} news")
    if run_id:
        _save_raw_input_safely(
            store,
            run_id,
            "exa",
            exa_data,
            action="exa save",
            acquisition_steps=acquisition_steps,
        )
    return exa_data, exa_collector


def _collect_parallel_shadow_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    effective_brand_url: str,
    cache_read,
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    parallel_shadow_collector_cls=ParallelShadowCollector,
) -> ParallelShadowData | None:
    if not _parallel_shadow_enabled():
        _set_acquisition_state(
            raw_input_cache,
            acquisition_steps,
            source="parallel_shadow",
            raw_cache_status="disabled",
            status="disabled",
            cache_status="disabled",
            eligible=False,
        )
        return None

    cached = cache_read("parallel_shadow", BRAND3_CACHE_TTL_HOURS, from_parallel_shadow_payload)
    if cached:
        _use_cached_input(
            store=store,
            run_id=run_id,
            source="parallel_shadow",
            payload=cached,
            raw_input_cache=raw_input_cache,
            acquisition_steps=acquisition_steps,
            action="parallel shadow cache save",
        )
        return ParallelShadowData.from_dict(
            {
                **cached,
                "brand_name": cached.get("brand_name") or brand_name,
                "brand_url": cached.get("brand_url") or effective_brand_url,
            }
        )

    collector = parallel_shadow_collector_cls()
    shadow_data = collector.collect(brand_name, effective_brand_url)
    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source="parallel_shadow",
        raw_cache_status=shadow_data.status,
        status=shadow_data.status,
        cache_status="miss",
        eligible=shadow_data.status not in {"error", "failed"},
        details=shadow_data.summary(),
    )
    summary = shadow_data.summary()
    print(
        "  Parallel shadow:"
        f" status={shadow_data.status}"
        f" results={summary['result_total']}"
        f" domains={summary['unique_domain_count']}"
    )
    if run_id:
        _save_raw_input_safely(
            store,
            run_id,
            "parallel_shadow",
            shadow_data.to_dict(),
            action="parallel shadow save",
            acquisition_steps=acquisition_steps,
        )
    return shadow_data


def _parallel_shadow_enabled() -> bool:
    return os.environ.get("BRAND3_PARALLEL_SHADOW_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _hyperbrowser_enabled(run_input_sources: set[str] | None = None) -> bool:
    if run_input_sources is not None:
        return "hyperbrowser" in run_input_sources
    return BRAND3_HYPERBROWSER_ENABLED


def _collect_hyperbrowser_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    url: str,
    cache_read,
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    run_input_sources: set[str] | None = None,
    hyperbrowser_collector_cls=HyperbrowserCollector,
) -> HyperbrowserFetchData | None:
    if not _hyperbrowser_enabled(run_input_sources):
        _set_acquisition_state(
            raw_input_cache,
            acquisition_steps,
            source="hyperbrowser",
            raw_cache_status="disabled",
            status="disabled",
            cache_status="disabled",
            eligible=False,
            details={
                "provider": "hyperbrowser",
                "channel": "web_shadow",
                "evidence_eligibility": "ineligible",
            },
        )
        return None

    cached = cache_read("hyperbrowser", BRAND3_CACHE_TTL_HOURS, from_hyperbrowser_payload)
    if cached:
        _use_cached_input(
            store=store,
            run_id=run_id,
            source="hyperbrowser",
            payload=cached,
            raw_input_cache=raw_input_cache,
            acquisition_steps=acquisition_steps,
            details={
                "provider": "hyperbrowser",
                "channel": "web_shadow",
                "evidence_eligibility": "eligible",
                "source_url": cached.final_url,
                "content_hash": cached.metadata.get("contentHash"),
                "confidence": cached.metadata.get("confidence"),
                "chars": cached.text_chars,
            },
            action="hyperbrowser cache save",
            message=f"  Hyperbrowser: cache hit ({cached.text_chars} chars)",
        )
        return cached

    collector = hyperbrowser_collector_cls()
    data = collector.fetch(
        url,
        include_html=True,
        include_links=True,
        include_branding=True,
        include_screenshot=False,
    )
    status = "ok" if not data.error else "error"
    eligible = not bool(data.error)
    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source="hyperbrowser",
        raw_cache_status="miss" if eligible else "error",
        status=status,
        cache_status="miss",
        eligible=eligible,
        error=data.error or None,
        details={
            "provider": "hyperbrowser",
            "channel": "web_shadow",
            "evidence_eligibility": "eligible" if eligible else "ineligible",
            "source_url": data.final_url,
            "content_hash": data.metadata.get("contentHash"),
            "confidence": data.metadata.get("confidence"),
            "chars": data.text_chars,
        },
    )
    print(
        "  Hyperbrowser:"
        f" status={status}"
        f" chars={data.text_chars}"
        f" links={len(data.links)}"
    )
    if run_id:
        _save_raw_input_safely(
            store,
            run_id,
            "hyperbrowser",
            data,
            action="hyperbrowser save",
            acquisition_steps=acquisition_steps,
        )
    return data


def _collect_social_input(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    web_data: WebData,
    use_social: bool,
    cache_read,
    raw_input_cache: dict[str, str],
    acquisition_steps: dict[str, AcquisitionResult] | None = None,
    social_collector,
) -> tuple[SocialData | None, str | None]:
    if not use_social:
        _set_acquisition_state(
            raw_input_cache,
            acquisition_steps,
            source="social",
            raw_cache_status="skipped",
            status="skipped",
            cache_status="skipped",
            eligible=False,
        )
        return None, None

    social_data = cache_read("social", BRAND3_CACHE_TTL_HOURS, from_social_payload)
    if social_data:
        _use_cached_input(
            store=store,
            run_id=run_id,
            source="social",
            payload=social_data,
            raw_input_cache=raw_input_cache,
            acquisition_steps=acquisition_steps,
            details={"platforms": len(social_data.platforms), "followers": social_data.total_followers},
            action="social cache save",
            message=f"  Social: cache hit ({len(social_data.platforms)} platforms, {social_data.total_followers:,} total followers)",
        )
        return social_data, None

    try:
        social_data, social_limitation = social_collector(
            brand_name,
            web_data.markdown_content,
            api_key=FIRECRAWL_API_KEY,
        )
        platforms_count = len(social_data.platforms)
        if social_limitation:
            _set_acquisition_state(
                raw_input_cache,
                acquisition_steps,
                source="social",
                raw_cache_status=social_limitation,
                status=social_limitation,
                cache_status="miss",
                eligible=True,
                details={"platforms": len(social_data.platforms)},
            )
            print(f"  Social: {social_limitation} - continuing without blocking analysis")
        else:
            _set_acquisition_state(
                raw_input_cache,
                acquisition_steps,
                source="social",
                raw_cache_status="miss",
                status="ok",
                cache_status="miss",
                eligible=True,
                details={"platforms": len(social_data.platforms), "followers": social_data.total_followers},
            )
            print(f"  Social: {platforms_count} platforms, {social_data.total_followers:,} total followers")
        if run_id:
            _save_raw_input_safely(
                store,
                run_id,
                "social",
                social_data,
                action="social save",
                acquisition_steps=acquisition_steps,
            )
        return social_data, social_limitation
    except Exception as e:
        _set_acquisition_state(
            raw_input_cache,
            acquisition_steps,
            source="social",
            raw_cache_status="error",
            status="error",
            cache_status="miss",
            eligible=False,
            error=str(e),
        )
        print(f"  Social: error - {e}")
        social_data = SocialData(brand_name=brand_name, error=str(e))
        if run_id:
            _save_raw_input_safely(
                store,
                run_id,
                "social",
                social_data,
                action="social error save",
                acquisition_steps=acquisition_steps,
            )
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
    acquisition_steps: dict[str, AcquisitionResult] | None,
) -> CompetitorData | None:
    if not use_competitors:
        _set_acquisition_state(
            raw_input_cache,
            acquisition_steps,
            source="competitors",
            raw_cache_status="skipped",
            status="skipped",
            cache_status="skipped",
            eligible=False,
        )
        print("  Competitors: skipped (--fast mode)")
        return None

    competitor_collector = CompetitorCollector(
        exa_collector=exa_collector,
        web_collector=web_collector,
        max_competitors=5,
    )
    competitor_data = cache_read("competitors", BRAND3_CACHE_TTL_HOURS, from_competitor_payload)
    if competitor_data:
        _use_cached_input(
            store=store,
            run_id=run_id,
            source="competitors",
            payload=competitor_data,
            raw_input_cache=raw_input_cache,
            acquisition_steps=acquisition_steps,
            details={"competitors": len(competitor_data.competitors)},
            action="competitor cache save",
            message=f"  Competitors: cache hit ({len(competitor_data.competitors)} competitors)",
        )
        return competitor_data

    _set_acquisition_state(
        raw_input_cache,
        acquisition_steps,
        source="competitors",
        raw_cache_status="miss",
        status="fetched",
        cache_status="miss",
        eligible=True,
    )
    competitor_data = competitor_collector.collect(
        brand_name=brand_name,
        brand_url=effective_brand_url,
        brand_web=web_data,
        exa_data=exa_data,
    )
    if run_id:
        _save_raw_input_safely(
            store,
            run_id,
            "competitors",
            competitor_data,
            action="competitor save",
            acquisition_steps=acquisition_steps,
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
    hyperbrowser_collector_cls=HyperbrowserCollector,
    run_input_sources: set[str] | None = None,
) -> RawInputs:
    raw_input_cache: dict[str, str] = {}
    acquisition_steps: dict[str, AcquisitionResult] = {}
    cache_read = _cache_reader(
        store=store,
        brand_name=brand_name,
        url=url,
        refresh=refresh,
        acquisition_steps=acquisition_steps,
    )
    context_data = _collect_context_input(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        url=url,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        context_evidence_builder=context_evidence_builder,
        context_collector_cls=context_collector_cls,
    )
    web_data, web_collector = _collect_web_input(
        store=store,
        run_id=run_id,
        url=url,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        web_collector_cls=web_collector_cls,
    )
    hyperbrowser_data = _collect_hyperbrowser_input(
        store=store,
        run_id=run_id,
        url=url,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        run_input_sources=run_input_sources,
        hyperbrowser_collector_cls=hyperbrowser_collector_cls,
    )
    effective_brand_url = effective_brand_url_builder(url, web_data)
    exa_data, exa_collector = _collect_exa_input(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        effective_brand_url=effective_brand_url,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        exa_collector_cls=exa_collector_cls,
    )
    parallel_shadow_data = _collect_parallel_shadow_input(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        effective_brand_url=effective_brand_url,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
    )
    social_data, social_limitation = _collect_social_input(
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        web_data=web_data,
        use_social=use_social,
        cache_read=cache_read,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
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
        acquisition_steps=acquisition_steps,
    )
    return RawInputs(
        context_data=context_data,
        web_data=web_data,
        hyperbrowser_data=hyperbrowser_data,
        effective_brand_url=effective_brand_url,
        exa_data=exa_data,
        parallel_shadow_data=parallel_shadow_data,
        social_data=social_data,
        social_limitation=social_limitation,
        competitor_data=competitor_data,
        raw_input_cache=raw_input_cache,
        acquisition_steps=acquisition_steps,
        web_collector=web_collector,
        exa_collector=exa_collector,
    )
