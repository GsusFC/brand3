"""External-source raw input collection helpers."""

from __future__ import annotations

import logging
import os

from src.collectors.hyperbrowser_collector import HyperbrowserCollector, HyperbrowserFetchData
from src.collectors.parallel_shadow_collector import ParallelShadowCollector, ParallelShadowData
from src.config import (
    BRAND3_CACHE_TTL_HOURS,
    BRAND3_HYPERBROWSER_ENABLED,
)
from src.services.input_collection_payloads import (
    from_hyperbrowser_payload,
    from_parallel_shadow_payload,
)
from src.services.input_collection_state import (
    AcquisitionResult,
    _save_raw_input_safely,
    _set_acquisition_state,
    _use_cached_input,
)
from src.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


def _parallel_shadow_enabled() -> bool:
    return os.environ.get("BRAND3_PARALLEL_SHADOW_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _hyperbrowser_enabled(run_input_sources: set[str] | None = None) -> bool:
    if run_input_sources is not None:
        return "hyperbrowser" in run_input_sources
    return BRAND3_HYPERBROWSER_ENABLED


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
    logger.info(
        "parallel shadow input collected",
        extra={
            "source": "parallel_shadow",
            "status": shadow_data.status,
            "results": summary["result_total"],
            "domains": summary["unique_domain_count"],
        },
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
    logger.info(
        "hyperbrowser input collected",
        extra={"source": "hyperbrowser", "status": status, "chars": data.text_chars, "links": len(data.links)},
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
