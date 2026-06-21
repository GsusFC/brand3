"""Reusable service layer for Brand3 Scoring operations."""

from __future__ import annotations

import json
import logging
import multiprocessing as mp
import os
import queue
import tempfile
from datetime import datetime
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any
from urllib.parse import unquote, urlparse

from src.collectors.competitor_collector import (
    ComparisonResult,
    CompetitorCollector,
    CompetitorData,
    CompetitorInfo,
)
from src.collectors.context_collector import ContextCollector, ContextData
from src.collectors.exa_collector import ExaCollector, ExaData, ExaResult
from src.collectors.social_collector import PlatformMetrics, SocialCollector, SocialData
from src.collectors.web_collector import WebCollector, WebData
from src.config import (
    AUDIT_ANALYST_MODEL,
    BRAND3_CACHE_TTL_HOURS,
    BRAND3_DB_PATH,
    BRAND3_NICHE_AUTO_APPLY_MIN_CONFIDENCE,
    BRAND3_PROMOTION_MAX_COMPOSITE_DROP,
    BRAND3_PROMOTION_MAX_DIMENSION_DROPS,
    BRAND3_SCREENSHOT_DIR,
    EXA_API_KEY,
    FIRECRAWL_API_KEY,
    LLM_CHEAP_MODEL,
    SCREENSHOT_PROVIDER,
)
from src.discovery.enrichment import build_discovery_enrichment
from src.discovery.evidence_preview import build_discovery_evidence_preview
from src.discovery.calibration import apply_discovery_calibration_hint, build_discovery_calibration_hint
from src.discovery.entity_discovery import discover_entity
from src.discovery.summary import format_discovery_summary
from src.discovery.trust_basis import build_discovery_trust_basis
from src.discovery.search_plan import build_discovery_search_plan
from src.reports.brand_audit_analyst import run_brand_audit_analyst_pass
from src.reports.entity_research_packet import build_entity_research_packet
from src.research.research_pack_facade import build_recommended_research_pack
from src.niche import classify_brand_niche, list_calibration_profiles, select_calibration_profile
from src.features.llm_analyzer import LLMAnalyzer
from src.features.percepcion import PercepcionExtractor
from src.features.coherencia import CoherenciaExtractor
from src.features.diferenciacion import DiferenciacionExtractor
from src.features.presencia import PresenciaExtractor
from src.features.vitalidad import VitalidadExtractor
from src.learning.calibration import CalibrationAnalyzer
from src.quality.dimension_confidence import dimension_confidence_from_features, dimension_confidence_from_snapshot
from src.quality.evidence_summary import summarize_evidence_from_features, summarize_evidence_records
from src.quality.trust import quality_label
from src.scoring.engine import ScoringEngine
from src.services.calibration_state import _build_experiment_summary
from src.services.analysis_reporting import (
    benchmark_profiles as _benchmark_profiles_impl,
    brand_report as _brand_report_impl,
    compare_benchmarks as _compare_benchmarks_impl,
)
from src.services.acquisition_audit import (
    _acquisition_audit_payload,
    _acquisition_provenance_summary,
    _context_evidence_items,
)
from src.services.brand_profiles import _build_brand_profile, _slugify
from src.services.calibration_workflows import (
    _build_run_audit_context as _build_run_audit_context_impl,
    _default_gate_config as _default_gate_config_impl,
    _evaluate_promotion_gate as _evaluate_promotion_gate_impl,
    _load_gate_config as _load_gate_config_impl,
    _read_calibration_state as _read_calibration_state_impl,
    _restore_calibration_state as _restore_calibration_state_impl,
    apply_candidates as _apply_candidates_impl,
    compare_version as _compare_version_impl,
    get_gate_config as _get_gate_config_impl,
    list_baselines as _list_baselines_impl,
    list_candidates as _list_candidates_impl,
    list_experiments as _list_experiments_impl,
    list_versions as _list_versions_impl,
    promote_baseline as _promote_baseline_impl,
    propose_calibration as _propose_calibration_impl,
    review_candidate as _review_candidate_impl,
    rollback_version as _rollback_version_impl,
    run_experiment as _run_experiment_impl,
    set_gate_config as _set_gate_config_impl,
)
from src.services.content_web import (
    _aggregate_exa_content,
    _build_content_web,
    _effective_brand_url,
    _has_usable_web_content,
    _recover_owned_web_content,
    _web_content_changed,
)
from src.services.diagnostics import _log_timing, _print_feature_details
from src.services.discovery_payloads import _annotate_content_source
from src.services.feature_pipeline import run_feature_pipeline
from src.services.input_collection import collect_raw_inputs, start_analysis_run, store_safely as _store_safely
from src.services.job_orchestration import (
    cancel_analysis_job as _cancel_analysis_job,
    claim_next_job as _claim_next_job,
    enqueue_analysis_job as _enqueue_analysis_job,
    execute_analysis_job as _execute_analysis_job,
    get_analysis_job as _get_analysis_job,
    list_analysis_jobs as _list_analysis_jobs,
    run_claimed_job as _run_claimed_job,
    retry_analysis_job as _retry_analysis_job,
)
from src.services.llm_policy import (
    _audit_analyst_llm as _build_audit_analyst_llm,
    _cost_policy_summary,
    _infer_llm_provider,
    _llm_cache_summary,
    _llm_provider_payload,
)
from src.services.output_files import _save_result
from src.services.public_presence import (
    _context_effective_readiness,
    _context_enrichment_summary,
    _public_presence_inventory_summary,
)
from src.services.report_summaries import (
    _audit_analyst_llm,
    _context_confidence_summary,
    _dimension_confidence_summary,
    _llm_model_roles_payload,
    _persist_report_readiness,
    _trust_summary_payload,
)
from src.services.runtime_helpers import (
    _compute_data_quality as _compute_data_quality_impl,
    _should_skip_llm_for_low_context as _should_skip_llm_for_low_context_impl,
)
from src.services.visual_signature_runtime import (
    _content_web_from_snapshot as _content_web_from_snapshot_impl,
    _run_visual_signature_shadow as _run_visual_signature_shadow_impl,
    _screenshot_capture_from_snapshot as _screenshot_capture_from_snapshot_impl,
    _snapshot_has_visual_signature_scan as _snapshot_has_visual_signature_scan_impl,
    _visual_signature_shadow_failure_payload as _visual_signature_shadow_failure_payload_impl,
    _visual_signature_shadow_screenshot_payload as _visual_signature_shadow_screenshot_payload_impl,
    _web_data_from_snapshot as _web_data_from_snapshot_impl,
    ensure_visual_signature_for_existing_run as _ensure_visual_signature_for_existing_run_impl,
    run_visual_signature_for_existing_run as _run_visual_signature_for_existing_run_impl,
)
from src.services.run_payloads import _build_run_audit_payload, _build_run_data_sources_payload
from src.services.run_preparation import plan_content, select_niche_profile, setup_llm
from src.services.serialization import _to_jsonable
from src.services.scoring_pipeline import score_features
from src.storage.sqlite_store import SQLiteStore
from src.visual_signature import build_visual_signature_scan, extract_visual_signature
from src.visual_signature.persistence import (
    build_visual_signature_persistence_bundle,
    persist_visual_signature_bundle,
    persist_visual_signature_result,
)
from src.visual_signature.vision import enrich_visual_signature_with_vision

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIMENSIONS_PATH = (PROJECT_ROOT / "src" / "dimensions.py").resolve()
ENGINE_PATH = (PROJECT_ROOT / "src" / "scoring" / "engine.py").resolve()
_SOCIAL_COLLECTION_TIMEOUT_SECONDS = int(os.environ.get("BRAND3_SOCIAL_TIMEOUT_SECONDS", "25"))
_VISUAL_SCREENSHOT_TIMEOUT_SECONDS = int(os.environ.get("BRAND3_VISUAL_SCREENSHOT_TIMEOUT_SECONDS", "75"))
_LLM_ALLOWED_CONTENT_SOURCES = {
    "firecrawl",
    "browser_fallback",
    "owned_fallback",
    "official_related",
}
_PARTIAL_DIMENSIONS = ("coherencia", "diferenciacion")


class AnalysisJobCancelled(Exception):
    """Raised when a background analysis job is cancelled."""


def _entity_discovery_payload(
    *,
    brand_name: str,
    url: str,
    web_data: WebData | None,
    exa_data: ExaData | None,
    context_data: ContextData | None,
) -> dict[str, object]:
    try:
        return _to_jsonable(
            discover_entity(
                brand_name=brand_name,
                url=url,
                web_data=web_data,
                exa_data=exa_data,
                context_data=context_data,
            )
        )
    except Exception:
        return {
            "entity_type": "unknown",
            "analysis_scope": "url_only",
            "confidence": 0.0,
            "warnings": ["entity_discovery_failed"],
        }


def _discovery_search_plan_payload(
    *, entity_discovery: dict[str, object], brand_name: str, url: str
) -> dict[str, object]:
    try:
        return _to_jsonable(
            build_discovery_search_plan(
                entity_discovery=entity_discovery, brand_name=brand_name, url=url
            )
        )
    except Exception:
        primary_entity = brand_name or url or "Unknown"
        return {
            "primary_entity": primary_entity,
            "requested_entity": brand_name or primary_entity,
            "analysis_mode": "url_only",
            "queries": [
                f"{primary_entity} brand positioning",
                f"{primary_entity} latest updates",
                f"{primary_entity} reviews reputation",
                f"{primary_entity} competitors",
            ],
            "owned_urls": [url] if url else [],
        }


def _compute_data_quality(exa_data: ExaData | None, content_source: str) -> str:
    return _compute_data_quality_impl(exa_data, content_source)


def _has_effective_owned_content_for_llm(
    content_web: WebData | None,
    content_source: str,
) -> bool:
    return (
        content_source in _LLM_ALLOWED_CONTENT_SOURCES
        and _has_usable_web_content(content_web)
    )


def _should_skip_llm_for_low_context(
    context_data: ContextData | None,
    content_web: WebData | None,
    content_source: str,
) -> bool:
    return _should_skip_llm_for_low_context_impl(context_data, content_web, content_source)


def _social_collect_worker(
    output_queue,
    api_key: str | None,
    brand_name: str,
    web_content: str,
) -> None:
    try:
        data = SocialCollector(api_key=api_key).collect(brand_name, web_content)
        output_queue.put(("ok", data))
    except Exception as exc:
        output_queue.put(("error", str(exc)))


def _collect_social_with_budget(
    brand_name: str,
    web_content: str,
    *,
    api_key: str | None = None,
    timeout_seconds: int = _SOCIAL_COLLECTION_TIMEOUT_SECONDS,
) -> tuple[SocialData, str | None]:
    if timeout_seconds <= 0:
        try:
            return SocialCollector(api_key=api_key).collect(brand_name, web_content), None
        except Exception as exc:
            return SocialData(brand_name=brand_name, error=str(exc)), "error"

    import sys
    method = "spawn" if sys.platform == "darwin" else ("fork" if "fork" in mp.get_all_start_methods() else "spawn")
    ctx = mp.get_context(method)
    output_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_social_collect_worker,
        args=(output_queue, api_key, brand_name, web_content),
    )
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join(2)
        error = f"social_collection_timeout_after_{timeout_seconds}s"
        return SocialData(brand_name=brand_name, error=error), "timeout"

    try:
        status, payload = output_queue.get_nowait()
    except queue.Empty:
        error = "social_collection_no_result"
        return SocialData(brand_name=brand_name, error=error), "error"

    if status == "ok" and isinstance(payload, SocialData):
        return payload, None

    error = str(payload or "social_collection_error")
    return SocialData(brand_name=brand_name, error=error), "error"


def _normalized_screenshot_provider(provider: str | None = None) -> str:
    value = (provider or SCREENSHOT_PROVIDER or "firecrawl").strip().lower()
    return value if value in {"firecrawl", "playwright"} else "firecrawl"


def _take_firecrawl_screenshot(url: str) -> dict[str, object]:
    from src.features.visual_analyzer import VisualAnalyzer

    data = VisualAnalyzer().take_screenshot(url)
    data.setdefault("screenshot_provider", "firecrawl_screenshot")
    return data


def _screenshot_has_capture(data: dict[str, object] | None) -> bool:
    return bool(isinstance(data, dict) and str(data.get("screenshot_url") or "").strip())


def _take_playwright_screenshot_with_firecrawl_fallback(url: str) -> dict[str, object]:
    primary = _take_playwright_screenshot(url)
    if _screenshot_has_capture(primary):
        return primary

    fallback_reason = str(primary.get("error_type") or primary.get("error") or "missing_screenshot_url")
    try:
        fallback = _take_firecrawl_screenshot(url)
    except Exception as exc:
        primary["fallback_attempted"] = True
        primary["fallback_provider"] = "firecrawl_screenshot"
        primary["fallback_error"] = str(exc)
        return primary

    fallback["fallback_from_provider"] = "playwright"
    fallback["fallback_reason"] = fallback_reason
    if not _screenshot_has_capture(fallback) and primary.get("error"):
        fallback.setdefault("primary_error", primary.get("error"))
        fallback.setdefault("primary_error_type", primary.get("error_type"))
    return fallback


def _screenshot_capture_worker(output_queue, url: str, provider: str) -> None:
    try:
        if provider == "playwright":
            output_queue.put(("ok", _take_playwright_screenshot_with_firecrawl_fallback(url)))
            return

        output_queue.put(("ok", _take_firecrawl_screenshot(url)))
    except Exception as exc:
        output_queue.put(("error", str(exc)))


def _take_playwright_screenshot(url: str, *, timeout_ms: int = 30000) -> dict[str, object]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return {
            "error": f"Playwright not available: {exc}",
            "error_type": "missing_dependency",
            "screenshot_provider": "playwright",
        }

    screenshot_dir = Path(BRAND3_SCREENSHOT_DIR)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    fd, screenshot_path = tempfile.mkstemp(
        prefix="brand3-screenshot-", suffix=".png", dir=str(screenshot_dir)
    )
    os.close(fd)
    browser = None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1200},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            page.screenshot(path=screenshot_path, full_page=False, timeout=60000, animations="disabled")
            title = page.title()
            browser.close()
            browser = None
        return {
            "screenshot_url": Path(screenshot_path).as_uri(),
            "screenshot_path": screenshot_path,
            "metadata": {"title": title},
            "screenshot_provider": "playwright",
        }
    except PlaywrightTimeoutError as exc:
        return {
            "error": str(exc),
            "error_type": "timeout",
            "screenshot_provider": "playwright",
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "error_type": "browser_error",
            "screenshot_provider": "playwright",
        }
    finally:
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass
        # Failed captures leave an empty file behind now that screenshots
        # land in permanent storage — drop it.
        try:
            leftover = Path(screenshot_path)
            if leftover.exists() and leftover.stat().st_size == 0:
                leftover.unlink()
        except OSError:
            pass


def _take_screenshot_with_budget(
    url: str,
    *,
    timeout_seconds: int = _VISUAL_SCREENSHOT_TIMEOUT_SECONDS,
    provider: str | None = None,
) -> tuple[dict[str, object], str | None]:
    provider_name = _normalized_screenshot_provider(provider)
    if timeout_seconds <= 0:
        if provider_name == "playwright":
            return _take_playwright_screenshot_with_firecrawl_fallback(url), None

        try:
            return _take_firecrawl_screenshot(url), None
        except Exception as exc:
            return {"error": str(exc), "screenshot_provider": "firecrawl_screenshot"}, "error"

    if provider_name == "playwright":
        return _take_playwright_screenshot_with_firecrawl_fallback(url), None

    import sys
    method = "spawn" if sys.platform == "darwin" else ("fork" if "fork" in mp.get_all_start_methods() else "spawn")
    ctx = mp.get_context(method)
    output_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(target=_screenshot_capture_worker, args=(output_queue, url, provider_name))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(2)
        if process.is_alive():
            process.kill()
            process.join(2)
        return {
            "error": f"visual_screenshot_timeout_after_{timeout_seconds}s",
            "error_type": "timeout",
            "screenshot_provider": provider_name if provider_name == "playwright" else "firecrawl_screenshot",
        }, "timeout"

    try:
        status, payload = output_queue.get_nowait()
    except queue.Empty:
        return {
            "error": "visual_screenshot_no_result",
            "error_type": "unknown",
            "screenshot_provider": provider_name if provider_name == "playwright" else "firecrawl_screenshot",
        }, "error"

    if status == "ok" and isinstance(payload, dict):
        return payload, None
    return {
        "error": str(payload or "visual_screenshot_error"),
        "error_type": "browser_error" if provider_name == "playwright" else "capture_error",
        "screenshot_provider": provider_name if provider_name == "playwright" else "firecrawl_screenshot",
    }, "error"


def _screenshot_capture_diagnostic(
    *,
    attempted: bool,
    screenshot_data: dict[str, object] | None = None,
    limitation: str | None = None,
    skipped_reason: str | None = None,
) -> dict[str, object]:
    if not attempted:
        return {
            "attempted": False,
            "success": False,
            "status": "skipped",
            "reason": skipped_reason or "not_attempted",
        }

    data = screenshot_data or {}
    screenshot_url = str(data.get("screenshot_url") or "")
    source = str(data.get("screenshot_provider") or "firecrawl_screenshot")
    if screenshot_url:
        return {
            "attempted": True,
            "success": True,
            "status": "captured",
            "source": source,
            "error_type": None,
            "error_message": None,
            "screenshot_url": screenshot_url,
        }

    error_message = str(data.get("error") or limitation or "screenshot_capture_failed")
    error_type = str(data.get("error_type") or limitation or _classify_screenshot_error(error_message))
    return {
        "attempted": True,
        "success": False,
        "status": "error" if error_type != "timeout" else "timeout",
        "source": source,
        "error_type": error_type,
        "error_message": error_message[:300],
    }


def _classify_screenshot_error(error_message: str) -> str:
    normalized = (error_message or "").lower()
    if "timeout" in normalized or "timed out" in normalized:
        return "timeout"
    if "payment required" in normalized or "insufficient credit" in normalized:
        return "payment_required"
    if "api_key" in normalized or "api key" in normalized or "not set" in normalized:
        return "missing_api_key"
    if "no screenshot url" in normalized:
        return "missing_screenshot_url"
    return "capture_error"


def _visual_signature_shadow_screenshot_payload(
    screenshot_capture: dict[str, object] | None,
    *,
    page_url: str,
) -> dict[str, object] | None:
    return _visual_signature_shadow_screenshot_payload_impl(screenshot_capture, page_url=page_url)


def _visual_signature_shadow_failure_payload(
    *,
    brand_name: str,
    url: str,
    error: str,
) -> dict[str, object]:
    return _visual_signature_shadow_failure_payload_impl(brand_name=brand_name, url=url, error=error)


def _run_visual_signature_shadow(
    *,
    enabled: bool,
    store: SQLiteStore | None,
    run_id: int | None,
    brand_name: str,
    url: str,
    web_data: WebData | None,
    content_web: WebData | None,
    screenshot_capture: dict[str, object] | None,
    extractor=extract_visual_signature,
    vision_enricher=enrich_visual_signature_with_vision,
    persistence_fn=persist_visual_signature_bundle,
) -> dict[str, object]:
    return _run_visual_signature_shadow_impl(
        enabled=enabled,
        store=store,
        run_id=run_id,
        brand_name=brand_name,
        url=url,
        web_data=web_data,
        content_web=content_web,
        screenshot_capture=screenshot_capture,
        extractor=extractor,
        vision_enricher=vision_enricher,
        persistence_fn=persistence_fn,
    )


def run_visual_signature_for_existing_run(
    *,
    store: SQLiteStore,
    run_id: int,
    extractor=extract_visual_signature,
    vision_enricher=enrich_visual_signature_with_vision,
    persistence_fn=persist_visual_signature_bundle,
) -> dict[str, object]:
    return _run_visual_signature_for_existing_run_impl(
        store=store,
        run_id=run_id,
        extractor=extractor,
        vision_enricher=vision_enricher,
        persistence_fn=persistence_fn,
    )


def ensure_visual_signature_for_existing_run(
    *,
    store: SQLiteStore,
    run_id: int,
    extractor=extract_visual_signature,
    vision_enricher=enrich_visual_signature_with_vision,
    persistence_fn=persist_visual_signature_bundle,
) -> dict[str, object]:
    return _ensure_visual_signature_for_existing_run_impl(
        store=store,
        run_id=run_id,
        extractor=extractor,
        vision_enricher=vision_enricher,
        persistence_fn=persistence_fn,
    )


def _snapshot_has_visual_signature_scan(snapshot: dict[str, Any]) -> bool:
    return _snapshot_has_visual_signature_scan_impl(snapshot)


def _web_data_from_snapshot(snapshot: dict[str, Any], *, fallback_url: str) -> WebData:
    return _web_data_from_snapshot_impl(snapshot, fallback_url=fallback_url)


def _content_web_from_snapshot(snapshot: dict[str, Any], *, fallback: WebData) -> WebData:
    return _content_web_from_snapshot_impl(snapshot, fallback=fallback)


def _screenshot_capture_from_snapshot(snapshot: dict[str, Any]) -> dict[str, object] | None:
    return _screenshot_capture_from_snapshot_impl(snapshot)


def _emit_progress(progress_cb, phase: str) -> None:
    if progress_cb is None:
        return
    progress_cb(phase)


def _build_research_pack_for_feature_prompts(
    *,
    store: SQLiteStore | None,
    run_id: int | None,
):
    if not store or run_id is None:
        return None
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            return None
        return build_recommended_research_pack(snapshot).pack
    except Exception as exc:
        print(f"  Research pack prompt input: skipped ({exc})")
        return None


def _check_cancel(cancel_check) -> None:
    if cancel_check is not None and cancel_check():
        raise AnalysisJobCancelled("Cancelled by user")


def _load_gate_config(store: SQLiteStore | None = None) -> dict:
    return _load_gate_config_impl(
        store,
        db_path=BRAND3_DB_PATH,
        default_gate_config=_default_gate_config,
    )


def _audit_analyst_llm(feature_llm: LLMAnalyzer | None) -> LLMAnalyzer | None:
    return _build_audit_analyst_llm(
        feature_llm,
        analyzer_cls=LLMAnalyzer,
        audit_analyst_model=AUDIT_ANALYST_MODEL,
    )


def _default_gate_config() -> dict:
    return _default_gate_config_impl(
        max_composite_drop=BRAND3_PROMOTION_MAX_COMPOSITE_DROP,
        max_dimension_drops=BRAND3_PROMOTION_MAX_DIMENSION_DROPS,
    )


def _evaluate_promotion_gate(experiment: dict | None, gate_config: dict | None = None) -> dict:
    return _evaluate_promotion_gate_impl(
        experiment,
        gate_config=gate_config,
        default_gate_config=_default_gate_config,
        default_max_composite_drop=BRAND3_PROMOTION_MAX_COMPOSITE_DROP,
        default_max_dimension_drops=BRAND3_PROMOTION_MAX_DIMENSION_DROPS,
    )


def _read_calibration_state(store: SQLiteStore | None = None) -> dict[str, object]:
    return _read_calibration_state_impl(
        store,
        dimensions_path=DIMENSIONS_PATH,
        engine_path=ENGINE_PATH,
        load_gate_config=_load_gate_config,
    )


def _restore_calibration_state(version: dict, store: SQLiteStore | None = None) -> None:
    _restore_calibration_state_impl(
        version,
        store,
        db_path=BRAND3_DB_PATH,
        dimensions_path=DIMENSIONS_PATH,
        engine_path=ENGINE_PATH,
    )


def _build_run_audit_context(
    store: SQLiteStore | None = None,
    calibration_profile: str = "base",
    niche_classification: dict | None = None,
) -> dict:
    return _build_run_audit_context_impl(
        store=store,
        db_path=BRAND3_DB_PATH,
        dimensions_path=DIMENSIONS_PATH,
        engine_path=ENGINE_PATH,
        load_gate_config=_load_gate_config,
        calibration_profile=calibration_profile,
        niche_classification=niche_classification,
    )


def run(
    url: str,
    brand_name: str = None,
    use_llm: bool = True,
    use_social: bool = True,
    use_competitors: bool = True,
    calibration_profile_override: str | None = None,
    skip_visual_analysis: bool = False,
    enable_visual_signature_shadow_run: bool = False,
    refresh: bool = False,
    run_input_sources: set[str] | None = None,
    progress_cb=None,
    cancel_check=None,
) -> dict:
    if not brand_name:
        brand_name = url.replace("https://", "").replace("http://", "").split("/")[0]

    run_started = perf_counter()
    storage = start_analysis_run(
        brand_name,
        url,
        use_llm=use_llm,
        use_social=use_social,
        db_path=BRAND3_DB_PATH,
    )
    store = storage.store
    run_id = storage.run_id

    try:
        _check_cancel(cancel_check)
        phase_started = perf_counter()
        step_started = phase_started
        print(f"[1/4] Collecting data for {brand_name}...")

        raw_inputs = collect_raw_inputs(
            store=store,
            run_id=run_id,
            brand_name=brand_name,
            url=url,
            refresh=refresh,
            use_social=use_social,
            use_competitors=use_competitors,
            effective_brand_url_builder=_effective_brand_url,
            context_evidence_builder=_context_evidence_items,
            run_input_sources=run_input_sources,
            social_collector=_collect_social_with_budget,
            context_collector_cls=ContextCollector,
            web_collector_cls=WebCollector,
            exa_collector_cls=ExaCollector,
        )
        context_data = raw_inputs.context_data
        web_data = raw_inputs.web_data
        effective_brand_url = raw_inputs.effective_brand_url
        exa_data = raw_inputs.exa_data
        social_data = raw_inputs.social_data
        social_limitation = raw_inputs.social_limitation
        competitor_data = raw_inputs.competitor_data
        raw_input_cache = raw_inputs.raw_input_cache
        acquisition_steps = raw_inputs.acquisition_steps
        web_collector = raw_inputs.web_collector
        step_started = _log_timing("phase 1a raw inputs", step_started)

        niche = select_niche_profile(
            brand_name=brand_name,
            url=url,
            web_data=web_data,
            exa_data=exa_data,
            competitor_data=competitor_data,
            calibration_profile_override=calibration_profile_override,
            min_confidence=BRAND3_NICHE_AUTO_APPLY_MIN_CONFIDENCE,
            classify_brand_niche=classify_brand_niche,
            select_calibration_profile=select_calibration_profile,
        )
        niche_classification = niche.classification
        calibration_profile = niche.calibration_profile
        profile_source = niche.profile_source
        if run_id:
            _store_safely(store, "run classification", lambda: store.update_run_classification(run_id, niche_classification, calibration_profile, profile_source))
        step_started = _log_timing("phase 1b niche profile", step_started)

        content_plan = plan_content(
            url=url,
            brand_name=brand_name,
            web_data=web_data,
            context_data=context_data,
            web_collector=web_collector,
            exa_data=exa_data,
            recover_owned_web_content=_recover_owned_web_content,
            build_content_web=_build_content_web,
            compute_data_quality=_compute_data_quality,
            partial_dimensions=_PARTIAL_DIMENSIONS,
        )
        content_web = content_plan.content_web
        content_source = content_plan.content_source
        data_sources = content_plan.data_sources
        data_quality = content_plan.data_quality
        partial_dimensions = content_plan.partial_dimensions
        step_started = _log_timing("phase 1c content plan", step_started)
        entity_discovery = _entity_discovery_payload(brand_name=brand_name, url=url, web_data=content_web or web_data, exa_data=exa_data, context_data=context_data)
        discovery_search_plan = _discovery_search_plan_payload(entity_discovery=entity_discovery, brand_name=brand_name, url=url)
        entity_research_packet = build_entity_research_packet(
            input_url=url,
            brand_name=brand_name,
            entity_discovery=entity_discovery,
            discovery_search_plan=discovery_search_plan,
            web_data=content_web or web_data,
            exa_data=exa_data,
        ).to_dict()
        if run_id:
            _store_safely(store, "entity research packet save", lambda: store.save_raw_input(run_id, "entity_research_packet", entity_research_packet))
        step_started = _log_timing("phase 1d entity research packet", step_started)
        discovery_evidence_preview = _to_jsonable(build_discovery_evidence_preview(discovery_search_plan, exa_data=exa_data, web_data=content_web or web_data, context_data=context_data))
        discovery_enrichment = build_discovery_enrichment(discovery_search_plan, discovery_evidence_preview, exa_data=exa_data, web_data=content_web or web_data, web_collector=web_collector, exa_collector=raw_inputs.exa_collector, entity_research_packet=entity_research_packet)
        raw_web_data = web_data
        exa_data = discovery_enrichment.exa_data
        content_web = discovery_enrichment.web_data or content_web
        web_data = discovery_enrichment.web_data or web_data
        if run_id and _web_content_changed(raw_web_data, content_web):
            effective_web_payload = _to_jsonable(content_web)
            if isinstance(effective_web_payload, dict):
                # Run-scoped derived evidence: snapshot readers keep preferring
                # the newest "web" row, but the cross-run cache must skip it so
                # a later run never treats enriched content as a raw capture.
                effective_web_payload["derived"] = "discovery_enrichment"
            _store_safely(
                store,
                "effective web input save",
                lambda: store.save_raw_input(run_id, "web", effective_web_payload),
            )
        discovery_enrichment_payload = discovery_enrichment.payload
        step_started = _log_timing("phase 1e discovery enrichment", step_started)
        acquisition_provenance = _acquisition_provenance_summary(
            brand_name=brand_name,
            url=url,
            web_data=web_data,
            exa_data=exa_data,
            context_data=context_data,
            discovery_enrichment_payload=discovery_enrichment_payload,
            raw_input_cache=raw_input_cache,
            content_source=content_source,
            data_quality=data_quality,
        )
        discovery_trust_basis = build_discovery_trust_basis(entity_discovery, discovery_search_plan, discovery_evidence_preview, discovery_enrichment_payload)
        discovery_calibration_hint = build_discovery_calibration_hint(entity_discovery, discovery_trust_basis, niche_classification)
        available_profiles = {item["profile_id"] for item in list_calibration_profiles()}
        discovery_calibration_decision = apply_discovery_calibration_hint(current_profile=calibration_profile, current_profile_source=profile_source, discovery_calibration_hint=discovery_calibration_hint, discovery_evidence_preview=discovery_evidence_preview, discovery_enrichment=discovery_enrichment_payload, available_profiles=available_profiles)
        calibration_profile = str(discovery_calibration_decision["calibration_profile"])
        profile_source = str(discovery_calibration_decision["profile_source"])
        discovery_payload = {"entity_discovery": entity_discovery, "discovery_search_plan": discovery_search_plan, "discovery_evidence_preview": discovery_evidence_preview, "discovery_trust_basis": discovery_trust_basis, "discovery_calibration_hint": discovery_calibration_hint}
        research_pack_for_feature_prompts = _build_research_pack_for_feature_prompts(
            store=store,
            run_id=run_id,
        )
        step_started = _log_timing("phase 1f provenance+calibration", step_started)

        llm_setup = setup_llm(
            use_llm=use_llm,
            context_data=context_data,
            content_web=content_web,
            content_source=content_source,
            llm_cls=LLMAnalyzer,
            cheap_model=LLM_CHEAP_MODEL,
            provider_payload_builder=_llm_provider_payload,
            should_skip_llm_for_low_context=_should_skip_llm_for_low_context,
        )
        llm = llm_setup.llm
        llm_provider = llm_setup.provider
        llm_skipped_reason = llm_setup.skipped_reason
        _log_timing("phase 1g llm setup", step_started)
        _log_timing("phase 1 collect+prepare", phase_started)

        _emit_progress(progress_cb, "extracting")
        _check_cancel(cancel_check)
        phase_started = perf_counter()
        print("[2/4] Extracting features...")

        feature_result = run_feature_pipeline(
            url=url,
            skip_visual_analysis=skip_visual_analysis,
            web_data=web_data,
            content_web=content_web,
            exa_data=exa_data,
            social_data=social_data,
            context_data=context_data,
            competitor_data=competitor_data,
            llm=llm,
            use_llm=use_llm,
            data_quality=data_quality,
            content_source=content_source,
            research_pack=research_pack_for_feature_prompts,
            take_screenshot_with_budget=_take_screenshot_with_budget,
            screenshot_capture_diagnostic=_screenshot_capture_diagnostic,
            presencia_cls=PresenciaExtractor,
            vitalidad_cls=VitalidadExtractor,
            coherencia_cls=CoherenciaExtractor,
            diferenciacion_cls=DiferenciacionExtractor,
            percepcion_cls=PercepcionExtractor,
            annotate_content_source=_annotate_content_source,
        )
        features_by_dim = feature_result.features_by_dim
        screenshot_capture = feature_result.screenshot_capture
        if run_id:
            _store_safely(
                store,
                "screenshot capture raw input save",
                lambda: store.save_raw_input(
                    run_id,
                    "screenshot_capture",
                    {
                        "version": "screenshot_capture_v1",
                        "url": url,
                        "content_source": content_source,
                        "skip_visual_analysis": skip_visual_analysis,
                        "capture": screenshot_capture,
                    },
                ),
            )
        _run_visual_signature_shadow(
            enabled=enable_visual_signature_shadow_run,
            store=store,
            run_id=run_id,
            brand_name=brand_name,
            url=url,
            web_data=web_data,
            content_web=content_web,
            screenshot_capture=screenshot_capture,
        )
        print(f"[timing] phase 2 features: {(perf_counter() - phase_started):.2f}s")

        _emit_progress(progress_cb, "scoring")
        _check_cancel(cancel_check)
        phase_started = perf_counter()
        print("[3/4] Scoring...")
        scoring = score_features(
            url=url,
            brand_name=brand_name,
            features_by_dim=features_by_dim,
            partial_dimensions=partial_dimensions,
            data_quality=data_quality,
            calibration_profile=calibration_profile,
            store=store,
            run_id=run_id,
            scoring_engine_cls=ScoringEngine,
            store_safely=_store_safely,
        )
        engine = scoring.engine
        brand_score = scoring.brand_score
        print(f"[timing] phase 3 scoring: {(perf_counter() - phase_started):.2f}s")

        _emit_progress(progress_cb, "finalizing")
        _check_cancel(cancel_check)
        phase_started = perf_counter()
        step_started = phase_started
        print("[4/4] Generating report...\n")
        summary = engine.generate_summary(brand_score)
        print(summary)
        print("\n".join([""] + format_discovery_summary(discovery_payload)))
        _print_feature_details(brand_score)
        step_started = _log_timing("phase 4a summary output", step_started)

        dimension_confidence = _dimension_confidence_summary(
            features_by_dim,
            evidence_items=_context_evidence_items(context_data),
            data_quality=data_quality,
            context_data=context_data,
        )
        evidence_summary = summarize_evidence_from_features(
            features_by_dim,
            evidence_items=_context_evidence_items(context_data),
        )
        confidence_summary = _context_confidence_summary(context_data)
        llm_cache = _llm_cache_summary(llm, llm_skipped_reason)
        public_presence_inventory = _public_presence_inventory_summary(
            brand_name=brand_score.brand_name,
            url=brand_score.url,
            web_data=web_data,
            content_web=content_web,
            content_source=content_source,
            exa_data=exa_data,
            context_data=context_data,
        )
        context_enrichment_summary = _context_enrichment_summary(
            public_presence_inventory=public_presence_inventory,
            context_summary=confidence_summary,
        )
        context_effective_readiness = _context_effective_readiness(
            public_presence_inventory=public_presence_inventory,
            context_summary=confidence_summary,
        )
        trust_summary = _trust_summary_payload(data_quality=data_quality, context_summary=confidence_summary, evidence_summary=evidence_summary, dimension_confidence=dimension_confidence, context_enrichment_summary=context_enrichment_summary, context_effective_readiness=context_effective_readiness)
        trust_summary["evidence_basis_summary"] = discovery_trust_basis["user_message"]
        step_started = _log_timing("phase 4b confidence+trust summaries", step_started)
        run_audit_context = (
            _build_run_audit_context(
                store,
                calibration_profile=calibration_profile,
                niche_classification=niche_classification,
            )
            if store
            else _build_run_audit_context(
                calibration_profile=calibration_profile,
                niche_classification=niche_classification,
            )
        )
        step_started = _log_timing("phase 4c audit context", step_started)
        run_audit_context["executive_analysis_v2"] = run_brand_audit_analyst_pass(
            llm=_audit_analyst_llm(llm),
            brand_name=brand_score.brand_name,
            url=brand_score.url,
            research_pack=research_pack_for_feature_prompts,
            dimensions=brand_score.breakdown,
            features_by_dim=features_by_dim,
        )
        step_started = _log_timing("phase 4d analyst pass", step_started)

        result = {
            "brand": brand_score.brand_name,
            "brand_profile": _build_brand_profile(brand_score.brand_name, brand_score.url, store),
            "url": brand_score.url,
            "run_id": run_id,
            "entity_discovery": entity_discovery,
            "discovery_search_plan": discovery_search_plan,
            "discovery_evidence_preview": discovery_evidence_preview,
            "discovery_enrichment": discovery_enrichment_payload,
            "entity_research_packet": entity_research_packet,
            "discovery_trust_basis": discovery_trust_basis,
            "discovery_calibration_hint": discovery_calibration_hint,
            "discovery_calibration_decision": discovery_calibration_decision,
            "niche_classification": niche_classification,
            "calibration_profile": calibration_profile,
            "profile_source": profile_source,
            "data_quality": data_quality,
            "data_sources": _build_run_data_sources_payload(
                base_data_sources=data_sources,
                acquisition_provenance=acquisition_provenance,
                acquisition_steps=acquisition_steps,
                public_presence_inventory=public_presence_inventory,
                screenshot_capture=screenshot_capture,
                social_limitation=social_limitation,
                raw_input_cache=raw_input_cache,
                llm_provider=llm_provider,
                llm_model_roles=_llm_model_roles_payload(),
                llm_cache=llm_cache,
                cost_policy=_cost_policy_summary(
                    raw_input_cache=raw_input_cache,
                    llm_cache=llm_cache,
                    use_llm=use_llm,
                    use_social=use_social,
                    social_limitation=social_limitation,
                    use_competitors=use_competitors,
                    skip_visual_analysis=skip_visual_analysis,
                    context_data=context_data,
                    data_quality=data_quality,
                ),
            ),
            "context_readiness": _to_jsonable(context_data),
            "context_enrichment_summary": context_enrichment_summary,
            "context_effective_readiness": context_effective_readiness,
            "confidence_summary": confidence_summary,
            "dimension_confidence": dimension_confidence,
            "evidence_summary": evidence_summary,
            "trust_summary": trust_summary,
            "composite_score": brand_score.composite_score,
            "composite_reliable": data_quality != "insufficient",
            "partial_score": data_quality == "insufficient",
            "partial_dimensions": partial_dimensions,
            "dimensions": brand_score.breakdown,
            "llm_used": use_llm and llm is not None,
            "social_scraped": social_data is not None and len(social_data.platforms) > 0,
            "audit": run_audit_context,
            "timestamp": datetime.now().isoformat(),
        }
        step_started = _log_timing("phase 4e result assembly", step_started)
        result["audit"].update(
            _build_run_audit_payload(
                acquisition_provenance=acquisition_provenance,
                acquisition_steps=acquisition_steps,
                raw_input_cache=raw_input_cache,
                screenshot_capture=screenshot_capture,
                data_quality=data_quality,
                content_source=content_source,
                discovery_calibration_decision=discovery_calibration_decision,
            )
        )
        if run_id:
            _store_safely(store, "run audit save", lambda: store.save_run_audit(run_id, result["audit"]))

        print("\n--- JSON ---")
        print(json.dumps(result, indent=2))
        output_path = _save_result(result)
        print(f"\nSaved result to: {output_path}")
        step_started = _log_timing("phase 4f json+output save", step_started)
        if run_id:
            _store_safely(
                store,
                "visual signature persistence",
                lambda: persist_visual_signature_result(store, run_id, result),
            )
        if run_id:
            _store_safely(
                store,
                "run finalize",
                lambda: store.finalize_run(
                    run_id=run_id,
                    composite_score=brand_score.composite_score,
                    llm_used=use_llm and llm is not None,
                    social_scraped=social_data is not None and len(social_data.platforms) > 0,
                    result_path=str(output_path),
                    summary=summary,
                ),
            )
        step_started = _log_timing("phase 4g finalize persistence", step_started)
        if run_id:
            _store_safely(
                store,
                "report readiness persistence",
                lambda: _persist_report_readiness(store, run_id, result["audit"]),
            )
        if run_id and llm is not None:
            def _persist_report_narrative() -> None:
                from src.reports.dossier import (
                    REPORT_NARRATIVE_SOURCE,
                    build_report_narrative_payload,
                )

                snapshot = store.get_run_snapshot(run_id)
                if not snapshot:
                    return
                store.save_raw_input(
                    run_id,
                    REPORT_NARRATIVE_SOURCE,
                    build_report_narrative_payload(
                        snapshot,
                        analyzer=llm,
                        analyst_pass=run_audit_context.get("executive_analysis_v2"),
                    ),
                )

            _store_safely(store, "report narrative persistence", _persist_report_narrative)
        _log_timing("phase 4h report narrative", step_started)
        _log_timing("phase 4 report+persist", phase_started)
        _log_timing("total run", run_started)
        return result
    except AnalysisJobCancelled:
        if run_id:
            _store_safely(store, "run status cancelled", lambda: store.mark_run_status(run_id, "cancelled"))
        raise
    except Exception:
        if run_id:
            _store_safely(store, "run status failed", lambda: store.mark_run_status(run_id, "failed"))
        raise
    finally:
        if store:
            _store_safely(store, "close", store.close)


def add_feedback(
    note: str,
    run_id: int | None = None,
    brand_name: str | None = None,
    url: str | None = None,
    dimension_name: str | None = None,
    feature_name: str | None = None,
    expected_score: float | None = None,
    actual_score: float | None = None,
) -> int:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        target_run_id = run_id or store.get_latest_run_id(brand_name=brand_name, url=url)
        if not target_run_id:
            raise ValueError("No matching run found for feedback")
        annotation_id = store.add_annotation(
            run_id=target_run_id,
            note=note,
            dimension_name=dimension_name,
            feature_name=feature_name,
            expected_score=expected_score,
            actual_score=actual_score,
        )
        print(f"Saved annotation {annotation_id} for run {target_run_id}")
        return annotation_id
    finally:
        store.close()


def learn(run_id: int | None = None, brand_name: str | None = None, url: str | None = None) -> list[dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        target_run_id = run_id or store.get_latest_run_id(brand_name=brand_name, url=url)
        if not target_run_id:
            raise ValueError("No matching run found for learning analysis")

        snapshot = store.get_run_snapshot(target_run_id)
        analyzer = CalibrationAnalyzer()
        recommendations = analyzer.analyze_snapshot(snapshot)
        recommendations.extend(analyzer.analyze_annotations(store.list_annotations(brand_name=brand_name)))

        payload = [
            {
                "scope": rec.scope,
                "target": rec.target,
                "severity": rec.severity,
                "message": rec.message,
                "evidence": rec.evidence,
            }
            for rec in recommendations
        ]
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def list_runs(brand_name: str | None = None, url: str | None = None, limit: int = 20) -> list[dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        runs = store.list_runs(brand_name=brand_name, url=url, limit=limit)
        print(json.dumps(runs, indent=2))
        return runs
    finally:
        store.close()


def list_brands(limit: int = 50) -> list[dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        brands = store.list_brands(limit=limit)
        print(json.dumps(brands, indent=2))
        return brands
    finally:
        store.close()


def list_profiles() -> list[dict]:
    payload = list_calibration_profiles()
    print(json.dumps(payload, indent=2))
    return payload


def benchmark_profiles(
    spec_path: str,
    *,
    profiles: list[str] | None = None,
    include_auto: bool = True,
    use_llm: bool = True,
    use_social: bool = True,
    use_competitors: bool = True,
) -> dict:
    return _benchmark_profiles_impl(
        spec_path,
        profiles=profiles,
        include_auto=include_auto,
        use_llm=use_llm,
        use_social=use_social,
        use_competitors=use_competitors,
    )


def compare_benchmarks(before_path: str, after_path: str) -> dict:
    return _compare_benchmarks_impl(before_path, after_path)


def list_feedback(brand_name: str | None = None) -> list[dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        annotations = store.list_annotations(brand_name=brand_name)
        print(json.dumps(annotations, indent=2))
        return annotations
    finally:
        store.close()


def show_run(run_id: int) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        print(json.dumps(snapshot, indent=2))
        return snapshot
    finally:
        store.close()


def run_evidence_summary(run_id: int) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        summary = summarize_evidence_records(
            snapshot.get("features") or [],
            evidence_items=snapshot.get("evidence_items") or [],
        )
        print(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()


def run_dimension_confidence(run_id: int) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        summary = dimension_confidence_from_snapshot(snapshot)
        print(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()


def run_trust_summary(run_id: int) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
        if not snapshot:
            raise ValueError(f"Run {run_id} not found")
        run_payload = snapshot.get("run") or {}
        context_summary = _context_readiness_from_snapshot(snapshot)
        evidence_summary = summarize_evidence_records(
            snapshot.get("features") or [],
            evidence_items=snapshot.get("evidence_items") or [],
        )
        dimension_confidence = dimension_confidence_from_snapshot(snapshot)
        trust_summary = _trust_summary_payload(
            data_quality=run_payload.get("data_quality") or "unknown",
            context_summary=context_summary,
            evidence_summary=evidence_summary,
            dimension_confidence=dimension_confidence,
        )
        payload = {
            "run_id": run_id,
            **trust_summary,
            "trust_summary": trust_summary,
            "context_readiness": context_summary,
            "evidence_summary": evidence_summary,
            "dimension_confidence": dimension_confidence,
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def _context_readiness_from_snapshot(snapshot: dict) -> dict:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") != "context" or not isinstance(item.get("payload"), dict):
            continue
        payload = item["payload"]
        coverage = float(payload.get("coverage") or 0.0)
        confidence = float(payload.get("confidence") or 0.0)
        if coverage < 0.3:
            status = "insufficient_data"
        elif confidence < 0.6:
            status = "degraded"
        else:
            status = "good"
        return {
            "available": True,
            "coverage": coverage,
            "confidence": confidence,
            "coverage_label": quality_label(coverage),
            "confidence_label": quality_label(confidence),
            "status": status,
            "confidence_reason": payload.get("confidence_reason") or [],
            "context_score": payload.get("context_score"),
        }
    return {
        "available": False,
        "coverage": 0.0,
        "confidence": 0.0,
        "coverage_label": "baja",
        "confidence_label": "baja",
        "status": "insufficient_data",
        "confidence_reason": ["context_scan_unavailable"],
    }


def brand_report(brand_name: str, limit: int = 10) -> dict:
    return _brand_report_impl(brand_name, limit=limit, db_path=BRAND3_DB_PATH)


def propose_calibration(brand_name: str, limit: int = 20, persist: bool = False) -> list[dict]:
    return _propose_calibration_impl(
        brand_name,
        db_path=BRAND3_DB_PATH,
        limit=limit,
        persist=persist,
    )


def list_candidates(brand_name: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
    return _list_candidates_impl(brand_name, status, limit, db_path=BRAND3_DB_PATH)


def review_candidate(candidate_id: int, status: str) -> dict:
    return _review_candidate_impl(candidate_id, status, db_path=BRAND3_DB_PATH)


def apply_candidates(candidate_ids: list[int] | None = None, brand_name: str | None = None) -> list[dict]:
    return _apply_candidates_impl(
        candidate_ids=candidate_ids,
        brand_name=brand_name,
        db_path=BRAND3_DB_PATH,
        dimensions_path=DIMENSIONS_PATH,
        engine_path=ENGINE_PATH,
        read_calibration_state=_read_calibration_state,
    )


def run_experiment(brand_name: str, candidate_ids: list[int] | None = None) -> dict:
    return _run_experiment_impl(
        brand_name,
        candidate_ids=candidate_ids,
        db_path=BRAND3_DB_PATH,
        run_fn=run,
        apply_candidates_fn=apply_candidates,
    )


def list_experiments(brand_name: str | None = None, limit: int = 20) -> list[dict]:
    return _list_experiments_impl(brand_name, limit, db_path=BRAND3_DB_PATH)


def list_versions(limit: int = 20) -> list[dict]:
    return _list_versions_impl(limit, db_path=BRAND3_DB_PATH)


def rollback_version(version_id: int) -> dict:
    return _rollback_version_impl(
        version_id,
        db_path=BRAND3_DB_PATH,
        read_calibration_state=_read_calibration_state,
        restore_calibration_state=_restore_calibration_state,
    )


def promote_baseline(version_id: int, label: str | None = None, force: bool = False) -> dict:
    return _promote_baseline_impl(
        version_id,
        label=label,
        force=force,
        db_path=BRAND3_DB_PATH,
        load_gate_config=_load_gate_config,
        evaluate_promotion_gate=_evaluate_promotion_gate,
    )


def list_baselines(limit: int = 20) -> dict:
    return _list_baselines_impl(limit, db_path=BRAND3_DB_PATH)


def get_gate_config() -> dict:
    return _get_gate_config_impl(db_path=BRAND3_DB_PATH, load_gate_config=_load_gate_config)


def set_gate_config(max_composite_drop: float | None = None, dimension_drops: dict | None = None) -> dict:
    return _set_gate_config_impl(
        max_composite_drop=max_composite_drop,
        dimension_drops=dimension_drops,
        db_path=BRAND3_DB_PATH,
        load_gate_config=_load_gate_config,
    )


def compare_version(version_id: int, brand_name: str) -> dict:
    return _compare_version_impl(
        version_id,
        brand_name,
        db_path=BRAND3_DB_PATH,
        evaluate_promotion_gate=_evaluate_promotion_gate,
        load_gate_config=_load_gate_config,
    )


def enqueue_analysis_job(
    url: str,
    brand_name: str | None = None,
    use_llm: bool = True,
    use_social: bool = True,
) -> dict:
    return _enqueue_analysis_job(
        BRAND3_DB_PATH,
        url,
        brand_name=brand_name,
        use_llm=use_llm,
        use_social=use_social,
    )


def get_analysis_job(job_id: int) -> dict:
    return _get_analysis_job(BRAND3_DB_PATH, job_id)


def list_analysis_jobs(
    brand_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    return _list_analysis_jobs(BRAND3_DB_PATH, brand_name=brand_name, status=status, limit=limit)


def execute_analysis_job(job_id: int) -> dict:
    return _execute_analysis_job(BRAND3_DB_PATH, job_id, run_fn=run, cancel_exc=AnalysisJobCancelled)


def run_claimed_job(job: dict) -> dict:
    """Run the pipeline for a job already claimed (status='running').

    Intended for the polling worker: `claim_pending_job()` returns the claimed
    job, which is then passed here. Callers with a specific job id should use
    `execute_analysis_job(job_id)` instead — it handles the claim.
    """
    return _run_claimed_job(BRAND3_DB_PATH, job, run_fn=run, cancel_exc=AnalysisJobCancelled)


def claim_next_job(worker_id: str | None = None) -> dict | None:
    return _claim_next_job(BRAND3_DB_PATH, worker_id=worker_id)


def cancel_analysis_job(job_id: int) -> dict:
    return _cancel_analysis_job(BRAND3_DB_PATH, job_id)


def retry_analysis_job(job_id: int) -> dict:
    return _retry_analysis_job(BRAND3_DB_PATH, job_id)
