"""Reusable service layer for Brand3 Scoring operations."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from urllib.parse import urlparse

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
    BRAND3_CACHE_TTL_HOURS,
    BRAND3_DB_PATH,
    BRAND3_NICHE_AUTO_APPLY_MIN_CONFIDENCE,
    BRAND3_PROMOTION_MAX_COMPOSITE_DROP,
    BRAND3_PROMOTION_MAX_DIMENSION_DROPS,
    EXA_API_KEY,
    FIRECRAWL_API_KEY,
)
from src.niche import (
    classify_brand_niche,
    get_calibration_profile,
    list_calibration_profiles,
    select_calibration_profile,
)
from src.features.llm_analyzer import LLMAnalyzer
from src.features.percepcion import PercepcionExtractor
from src.features.coherencia import CoherenciaExtractor
from src.features.diferenciacion import DiferenciacionExtractor
from src.features.presencia import PresenciaExtractor
from src.features.vitalidad import VitalidadExtractor
from src.learning.applier import CandidateApplyError, apply_candidate
from src.learning.calibration import CalibrationAnalyzer
from src.quality.dimension_confidence import dimension_confidence_from_features, dimension_confidence_from_snapshot
from src.quality.evidence_summary import summarize_evidence_from_features, summarize_evidence_records
from src.scoring.engine import ScoringEngine
from src.storage.sqlite_store import SQLiteStore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIMENSIONS_PATH = (PROJECT_ROOT / "src" / "dimensions.py").resolve()
ENGINE_PATH = (PROJECT_ROOT / "src" / "scoring" / "engine.py").resolve()
_MIN_USABLE_WEB_CHARS = 200
_MIN_EXA_FALLBACK_MENTIONS = 3
_MIN_EXA_FALLBACK_CHARS = 300
_MAX_EXA_FALLBACK_ITEMS = 8
_PARTIAL_DIMENSIONS = ("coherencia", "diferenciacion")


class AnalysisJobCancelled(Exception):
    """Raised when a background analysis job is cancelled."""


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part) or "brand"


def _derive_brand_profile(brand_name: str | None, url: str | None) -> dict[str, object]:
    parsed = urlparse(url if url and "://" in url else f"https://{url}" if url else "")
    domain = (parsed.netloc or parsed.path or "").strip().lower() or None
    if domain and domain.startswith("www."):
        domain = domain[4:]
    logo_key = _slugify(brand_name) if brand_name else None
    if not logo_key and domain:
        logo_key = _slugify(domain.split(".")[0])
    return {
        "name": brand_name,
        "domain": domain,
        "logo_key": logo_key,
        "logo_url": None,
    }


def _build_brand_profile(
    brand_name: str | None,
    url: str | None,
    store: SQLiteStore | None = None,
) -> dict[str, object]:
    should_close = False
    if store is None:
        try:
            store = SQLiteStore(BRAND3_DB_PATH)
            should_close = True
        except Exception:
            return _derive_brand_profile(brand_name, url)
    try:
        return store.get_brand_profile(brand_name, url)
    except Exception:
        return _derive_brand_profile(brand_name, url)
    finally:
        if should_close:
            store.close()


def _to_jsonable(value):
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def _save_result(result: dict) -> Path:
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{_slugify(result['brand'])}-{timestamp}.json"
    output_path = output_dir / filename
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return output_path


def _save_benchmark_result(result: dict) -> Path:
    output_dir = PROJECT_ROOT / "output" / "benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    spec_name = _slugify(result.get("benchmark_name", "benchmark"))
    output_path = output_dir / f"{spec_name}-{timestamp}.json"
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return output_path


def _save_benchmark_comparison_result(result: dict) -> Path:
    output_dir = PROJECT_ROOT / "output" / "benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    before_name = _slugify(result.get("before_benchmark", "before"))
    after_name = _slugify(result.get("after_benchmark", "after"))
    output_path = output_dir / f"{after_name}-vs-{before_name}-{timestamp}.json"
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return output_path


def _from_web_payload(payload: dict | None) -> WebData | None:
    if not payload:
        return None
    return WebData(**payload)


def _effective_brand_url(original_url: str, web_data: WebData | None) -> str:
    if web_data and getattr(web_data, "canonical_url", ""):
        return web_data.canonical_url
    return original_url


def _has_usable_web_content(web_data: WebData | None) -> bool:
    if not web_data or getattr(web_data, "error", ""):
        return False
    return len((web_data.markdown_content or "").strip()) >= _MIN_USABLE_WEB_CHARS


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


def _build_content_web(
    url: str,
    brand_name: str | None,
    web_data: WebData | None,
    exa_data: ExaData | None,
) -> tuple[WebData | None, str, dict[str, object]]:
    if _has_usable_web_content(web_data):
        return web_data, "firecrawl", {
            "web_scrape": "firecrawl",
            "exa_mentions": len(exa_data.mentions) if exa_data else 0,
            "content_source": "firecrawl",
            "exa_fallback_mentions_used": 0,
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
        }

    return None, "none", {
        "web_scrape": "failed",
        "exa_mentions": len(exa_data.mentions) if exa_data else 0,
        "content_source": "none",
        "exa_fallback_mentions_used": 0,
    }


def _annotate_content_source(features_by_dim: dict[str, dict], content_source: str) -> None:
    feature_names = {
        "coherencia": {
            "visual_consistency",
            "messaging_consistency",
            "tone_consistency",
            "cross_channel_coherence",
        },
        "diferenciacion": {
            "positioning_clarity",
            "uniqueness",
            "content_authenticity",
            "brand_personality",
        },
    }
    for dim_name, names in feature_names.items():
        for feature_name, feature in features_by_dim.get(dim_name, {}).items():
            if feature_name not in names:
                continue
            if not isinstance(feature.raw_value, dict):
                continue
            feature.raw_value["content_source"] = content_source


def _compute_data_quality(exa_data: ExaData | None, content_source: str) -> str:
    mentions_count = len(exa_data.mentions) if exa_data else 0
    if content_source == "firecrawl" and mentions_count >= 5:
        return "good"
    if content_source == "exa_fallback" and mentions_count >= 3:
        return "degraded"
    return "insufficient"


def _from_exa_payload(payload: dict | None) -> ExaData | None:
    if not payload:
        return None
    return ExaData(
        brand_name=payload.get("brand_name", ""),
        mentions=[ExaResult(**item) for item in payload.get("mentions", [])],
        competitors=[ExaResult(**item) for item in payload.get("competitors", [])],
        ai_visibility_results=[ExaResult(**item) for item in payload.get("ai_visibility_results", [])],
        news=[ExaResult(**item) for item in payload.get("news", [])],
        raw_responses=payload.get("raw_responses", {}),
    )


def _from_social_payload(payload: dict | None) -> SocialData | None:
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


def _from_competitor_payload(payload: dict | None) -> CompetitorData | None:
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


def _from_context_payload(payload: dict | None) -> ContextData | None:
    if not payload:
        return None
    return ContextData(**payload)


def _load_cached(store, brand_name: str, url: str, source: str, ttl_hours: int, decoder):
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


def _store_safely(store, action: str, fn) -> None:
    if not store:
        return
    try:
        fn()
    except Exception as e:
        print(f"  Storage {action}: skipped ({e})")


def _emit_progress(progress_cb, phase: str) -> None:
    if progress_cb is None:
        return
    progress_cb(phase)


def _check_cancel(cancel_check) -> None:
    if cancel_check is not None and cancel_check():
        raise AnalysisJobCancelled("Cancelled by user")


def _confidence_status(context_data: ContextData | None) -> str:
    if not context_data or context_data.coverage < 0.3:
        return "insufficient_data"
    if context_data.confidence < 0.6:
        return "degraded"
    return "good"


def _context_confidence_summary(context_data: ContextData | None) -> dict[str, object]:
    if not context_data:
        return {
            "coverage": 0.0,
            "confidence": 0.0,
            "confidence_reason": ["context_scan_unavailable"],
            "status": "insufficient_data",
        }
    return {
        "coverage": context_data.coverage,
        "confidence": context_data.confidence,
        "confidence_reason": list(context_data.confidence_reason or []),
        "status": _confidence_status(context_data),
    }


def _dimension_confidence_summary(
    features_by_dim: dict[str, dict],
    *,
    evidence_items: list[dict[str, object]] | None = None,
    data_quality: str | None = None,
    context_data: ContextData | None = None,
) -> dict[str, dict[str, object]]:
    return dimension_confidence_from_features(
        features_by_dim,
        evidence_items=evidence_items,
        data_quality=data_quality,
        context_summary=_context_confidence_summary(context_data),
    )


def _llm_cache_summary(llm: LLMAnalyzer | None, skipped_reason: str | None = None) -> dict[str, object]:
    if llm is None:
        return {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_writes": 0,
            "skipped_reason": skipped_reason,
        }
    hits = int(getattr(llm, "cache_hits", 0) or 0)
    misses = int(getattr(llm, "cache_misses", 0) or 0)
    writes = int(getattr(llm, "cache_writes", 0) or 0)
    return {
        "cache_hits": hits,
        "cache_misses": misses,
        "cache_writes": writes,
        "skipped_reason": skipped_reason,
        "estimated_cost_saved_units": hits,
    }


def _context_evidence_items(context_data: ContextData | None) -> list[dict[str, object]]:
    if not context_data:
        return []
    base = context_data.url.rstrip("/")
    items: list[dict[str, object]] = []
    if context_data.sitemap_found:
        items.append({
            "source": "context",
            "url": f"{base}/sitemap.xml",
            "quote": f"sitemap.xml found with {context_data.sitemap_url_count} URLs",
            "feature_name": "site_structure",
            "dimension_name": "presencia",
            "confidence": 0.8,
            "freshness_days": 0,
        })
    if context_data.robots_found:
        items.append({
            "source": "context",
            "url": f"{base}/robots.txt",
            "quote": "robots.txt found",
            "feature_name": "site_structure",
            "dimension_name": "presencia",
            "confidence": 0.75,
            "freshness_days": 0,
        })
    if context_data.llms_txt_found:
        items.append({
            "source": "context",
            "url": f"{base}/llms.txt",
            "quote": "llms.txt found",
            "feature_name": "ai_discoverability",
            "dimension_name": "presencia",
            "confidence": 0.7,
            "freshness_days": 0,
        })
    if context_data.schema_types:
        items.append({
            "source": "context",
            "url": base,
            "quote": "Schema detected: " + ", ".join(context_data.schema_types[:8]),
            "feature_name": "structured_identity",
            "dimension_name": "coherencia",
            "confidence": 0.75,
            "freshness_days": 0,
        })
    found_pages = [name for name, exists in context_data.key_pages.items() if exists]
    if found_pages:
        items.append({
            "source": "context",
            "url": base,
            "quote": "Key pages found: " + ", ".join(found_pages),
            "feature_name": "content_depth",
            "dimension_name": "diferenciacion",
            "confidence": 0.65,
            "freshness_days": 0,
        })
    return items


def _score_map(snapshot: dict) -> dict[str, float]:
    return {
        item["dimension_name"]: float(item["score"])
        for item in snapshot.get("scores", [])
        if item.get("dimension_name") is not None and item.get("score") is not None
    }


def _build_experiment_summary(
    before_snapshot: dict,
    after_snapshot: dict,
    applied_results: list[dict],
) -> dict:
    before_run = before_snapshot["run"]
    after_run = after_snapshot["run"]
    before_scores = _score_map(before_snapshot)
    after_scores = _score_map(after_snapshot)

    dimensions = {}
    for dimension_name in sorted(set(before_scores) | set(after_scores)):
        before_value = before_scores.get(dimension_name)
        after_value = after_scores.get(dimension_name)
        dimensions[dimension_name] = {
            "before": before_value,
            "after": after_value,
            "delta": None if before_value is None or after_value is None else round(after_value - before_value, 1),
        }

    before_composite = before_run.get("composite_score")
    after_composite = after_run.get("composite_score")
    applied_candidate_ids = [item["candidate_id"] for item in applied_results if item.get("applied")]

    return {
        "brand_name": after_run["brand_name"],
        "url": after_run["url"],
        "before_run_id": before_run["id"],
        "after_run_id": after_run["id"],
        "candidate_ids": applied_candidate_ids,
        "composite": {
            "before": before_composite,
            "after": after_composite,
            "delta": None if before_composite is None or after_composite is None else round(after_composite - before_composite, 1),
        },
        "dimensions": dimensions,
    }


def _default_gate_config() -> dict:
    return {
        "max_composite_drop": BRAND3_PROMOTION_MAX_COMPOSITE_DROP,
        "max_dimension_drops": dict(BRAND3_PROMOTION_MAX_DIMENSION_DROPS),
    }


def _load_gate_config(store: SQLiteStore | None = None) -> dict:
    should_close = False
    if store is None:
        store = SQLiteStore(BRAND3_DB_PATH)
        should_close = True
    try:
        return store.get_gate_config() or _default_gate_config()
    finally:
        if should_close:
            store.close()


def _read_calibration_state(store: SQLiteStore | None = None) -> dict[str, object]:
        return {
            "dimensions_content": DIMENSIONS_PATH.read_text(encoding="utf-8"),
            "engine_content": ENGINE_PATH.read_text(encoding="utf-8"),
            "gate_config": _load_gate_config(store),
        }


def _restore_calibration_state(version: dict, store: SQLiteStore | None = None) -> None:
    DIMENSIONS_PATH.write_text(version["dimensions_content"], encoding="utf-8")
    ENGINE_PATH.write_text(version["engine_content"], encoding="utf-8")
    if version.get("gate_config") is not None:
        should_close = False
        if store is None:
            store = SQLiteStore(BRAND3_DB_PATH)
            should_close = True
        try:
            store.upsert_gate_config(version["gate_config"])
        finally:
            if should_close:
                store.close()


def _evaluate_promotion_gate(experiment: dict | None, gate_config: dict | None = None) -> dict:
    gate_config = gate_config or _default_gate_config()
    max_composite_drop = float(gate_config.get("max_composite_drop", BRAND3_PROMOTION_MAX_COMPOSITE_DROP))
    max_dimension_drops = dict(BRAND3_PROMOTION_MAX_DIMENSION_DROPS)
    max_dimension_drops.update(gate_config.get("max_dimension_drops", {}))
    if not experiment:
        return {
            "allowed": False,
            "reasons": ["No experiment found for this version"],
            "summary": None,
            "thresholds": {
                "max_composite_drop": max_composite_drop,
                "max_dimension_drops": max_dimension_drops,
            },
        }

    summary = experiment.get("summary", {})
    composite = summary.get("composite", {})
    reasons = []

    composite_delta = composite.get("delta")
    if composite_delta is None:
        reasons.append("Experiment is missing composite delta")
    elif composite_delta < -max_composite_drop:
        reasons.append(
            f"Composite regressed by {composite_delta:.1f} points "
            f"(limit {-max_composite_drop:.1f})"
        )

    for dimension_name, payload in summary.get("dimensions", {}).items():
        delta = payload.get("delta")
        max_drop = float(max_dimension_drops.get(dimension_name, 5.0))
        if delta is not None and delta < -max_drop:
            reasons.append(
                f"Dimension {dimension_name} regressed by {delta:.1f} points "
                f"(limit {-max_drop:.1f})"
            )

    return {
        "allowed": len(reasons) == 0,
        "reasons": reasons,
        "summary": summary,
        "experiment_id": experiment.get("id"),
        "thresholds": {
            "max_composite_drop": max_composite_drop,
            "max_dimension_drops": max_dimension_drops,
        },
    }


def _compare_summaries(target_summary: dict | None, baseline_summary: dict | None) -> dict | None:
    if not target_summary or not baseline_summary:
        return None

    target_composite = target_summary.get("composite", {}).get("after")
    baseline_composite = baseline_summary.get("composite", {}).get("after")
    dimensions = {}

    target_dimensions = target_summary.get("dimensions", {})
    baseline_dimensions = baseline_summary.get("dimensions", {})
    for dimension_name in sorted(set(target_dimensions) | set(baseline_dimensions)):
        target_after = target_dimensions.get(dimension_name, {}).get("after")
        baseline_after = baseline_dimensions.get(dimension_name, {}).get("after")
        dimensions[dimension_name] = {
            "target_after": target_after,
            "baseline_after": baseline_after,
            "delta_vs_baseline": None
            if target_after is None or baseline_after is None
            else round(target_after - baseline_after, 1),
        }

    return {
        "composite": {
            "target_after": target_composite,
            "baseline_after": baseline_composite,
            "delta_vs_baseline": None
            if target_composite is None or baseline_composite is None
            else round(target_composite - baseline_composite, 1),
        },
        "dimensions": dimensions,
    }


def _compute_scoring_state_fingerprint(
    dimensions_content: str,
    engine_content: str,
    gate_config: dict,
    calibration_profile: str,
    calibration_profile_config: dict,
) -> str:
    payload = {
        "dimensions_content": dimensions_content,
        "engine_content": engine_content,
        "gate_config": gate_config,
        "calibration_profile": calibration_profile,
        "calibration_profile_config": calibration_profile_config,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return digest[:16]


def _build_run_audit_context(
    store: SQLiteStore | None = None,
    calibration_profile: str = "base",
    niche_classification: dict | None = None,
) -> dict:
    should_close = False
    if store is None:
        store = SQLiteStore(BRAND3_DB_PATH)
        should_close = True
    try:
        gate_config = _load_gate_config(store)
        dimensions_content = DIMENSIONS_PATH.read_text(encoding="utf-8")
        engine_content = ENGINE_PATH.read_text(encoding="utf-8")
        calibration_profile_config = get_calibration_profile(calibration_profile)
        return {
            "gate_config": gate_config,
            "active_baseline": store.get_active_baseline(),
            "calibration_profile": calibration_profile,
            "calibration_profile_config": calibration_profile_config,
            "niche_classification": niche_classification,
            "scoring_state_fingerprint": _compute_scoring_state_fingerprint(
                dimensions_content=dimensions_content,
                engine_content=engine_content,
                gate_config=gate_config,
                calibration_profile=calibration_profile,
                calibration_profile_config=calibration_profile_config,
            ),
        }
    finally:
        if should_close:
            store.close()


def run(
    url: str,
    brand_name: str = None,
    use_llm: bool = True,
    use_social: bool = True,
    use_competitors: bool = True,
    calibration_profile_override: str | None = None,
    skip_visual_analysis: bool = False,
    progress_cb=None,
    cancel_check=None,
) -> dict:
    if not brand_name:
        brand_name = url.replace("https://", "").replace("http://", "").split("/")[0]

    store = None
    run_id = None
    try:
        store = SQLiteStore(BRAND3_DB_PATH)
        brand_id = store.upsert_brand(brand_name, url)
        run_id = store.create_run(brand_id, brand_name, url, use_llm, use_social)
    except Exception as e:
        print(f"  Storage: disabled ({e})")

    try:
        _check_cancel(cancel_check)
        print(f"[1/4] Collecting data for {brand_name}...")

        raw_input_cache: dict[str, str] = {}

        context_data = _load_cached(store, brand_name, url, "context", 24, _from_context_payload)
        if context_data:
            raw_input_cache["context"] = "hit"
            print(
                "  Context: cache hit"
                f" (score={context_data.context_score:.0f}, confidence={context_data.confidence:.2f})"
            )
            if run_id:
                _store_safely(store, "context cache save", lambda: store.save_raw_input(run_id, "context", context_data))
                _store_safely(
                    store,
                    "context cache evidence save",
                    lambda: store.save_evidence_items(run_id, _context_evidence_items(context_data)),
                )
        else:
            raw_input_cache["context"] = "miss"
            context_data = ContextCollector().scan(url)
            print(
                "  Context:"
                f" score={context_data.context_score:.0f}"
                f" coverage={context_data.coverage:.2f}"
                f" confidence={context_data.confidence:.2f}"
            )
            if run_id:
                _store_safely(store, "context save", lambda: store.save_raw_input(run_id, "context", context_data))
                _store_safely(
                    store,
                    "context evidence save",
                    lambda: store.save_evidence_items(run_id, _context_evidence_items(context_data)),
                )

        web_collector = WebCollector(api_key=FIRECRAWL_API_KEY)
        web_data = _load_cached(store, brand_name, url, "web", BRAND3_CACHE_TTL_HOURS, _from_web_payload)
        if web_data:
            raw_input_cache["web"] = "hit"
            print(f"  Web: cache hit ({len(web_data.markdown_content)} chars)")
            if run_id:
                _store_safely(store, "web cache save", lambda: store.save_raw_input(run_id, "web", web_data))
        else:
            raw_input_cache["web"] = "miss"
            web_data = web_collector.scrape(url)
            print(f"  Web: {len(web_data.markdown_content)} chars scraped")
            if run_id:
                _store_safely(store, "web save", lambda: store.save_raw_input(run_id, "web", web_data))
        effective_brand_url = _effective_brand_url(url, web_data)

        exa_collector = ExaCollector(api_key=EXA_API_KEY)
        exa_data = _load_cached(store, brand_name, url, "exa", BRAND3_CACHE_TTL_HOURS, _from_exa_payload)
        if exa_data:
            raw_input_cache["exa"] = "hit"
            print(f"  Exa: cache hit ({len(exa_data.mentions)} mentions, {len(exa_data.news)} news)")
            if run_id:
                _store_safely(store, "exa cache save", lambda: store.save_raw_input(run_id, "exa", exa_data))
        else:
            raw_input_cache["exa"] = "miss"
            exa_data = exa_collector.collect_brand_data(brand_name, effective_brand_url)
            print(f"  Exa: {len(exa_data.mentions)} mentions, {len(exa_data.news)} news")
            if run_id:
                _store_safely(store, "exa save", lambda: store.save_raw_input(run_id, "exa", exa_data))

        social_data = None
        if use_social:
            social_data = _load_cached(store, brand_name, url, "social", BRAND3_CACHE_TTL_HOURS, _from_social_payload)
            if social_data:
                raw_input_cache["social"] = "hit"
                print(f"  Social: cache hit ({len(social_data.platforms)} platforms, {social_data.total_followers:,} total followers)")
                if run_id:
                    _store_safely(store, "social cache save", lambda: store.save_raw_input(run_id, "social", social_data))
            else:
                raw_input_cache["social"] = "miss"
                try:
                    social_collector = SocialCollector(api_key=FIRECRAWL_API_KEY)
                    social_data = social_collector.collect(brand_name, web_data.markdown_content)
                    platforms_count = len(social_data.platforms)
                    print(f"  Social: {platforms_count} platforms, {social_data.total_followers:,} total followers")
                    if run_id:
                        _store_safely(store, "social save", lambda: store.save_raw_input(run_id, "social", social_data))
                except Exception as e:
                    print(f"  Social: error - {e}")
                    social_data = None
        else:
            raw_input_cache["social"] = "skipped"

        competitor_data = None
        if use_competitors:
            competitor_collector = CompetitorCollector(
                exa_collector=exa_collector,
                web_collector=web_collector,
                max_competitors=5,
            )
            competitor_data = _load_cached(
                store, brand_name, url, "competitors", BRAND3_CACHE_TTL_HOURS, _from_competitor_payload
            )
            if competitor_data:
                raw_input_cache["competitors"] = "hit"
                print(f"  Competitors: cache hit ({len(competitor_data.competitors)} competitors)")
                if run_id:
                    _store_safely(
                        store,
                        "competitor cache save",
                        lambda: store.save_raw_input(run_id, "competitors", competitor_data),
                    )
            else:
                raw_input_cache["competitors"] = "miss"
                competitor_data = competitor_collector.collect(
                    brand_name=brand_name,
                    brand_url=effective_brand_url,
                    brand_web=web_data,
                    exa_data=exa_data,
                )
                if run_id:
                    _store_safely(
                        store,
                        "competitor save",
                        lambda: store.save_raw_input(run_id, "competitors", competitor_data),
                    )
        else:
            raw_input_cache["competitors"] = "skipped"
            print("  Competitors: skipped (--fast mode)")

        exa_texts = []
        if exa_data:
            # Keep niche classification high-precision: full mention bodies are noisy and
            # regularly include unrelated keywords from long-form pages.
            exa_texts.extend([item.title for item in exa_data.mentions if item.title])
            exa_texts.extend([item.summary for item in exa_data.mentions if item.summary])
            for item in exa_data.mentions:
                if not item.highlights:
                    continue
                exa_texts.extend(
                    str(highlight).strip()
                    for highlight in item.highlights[:2]
                    if str(highlight).strip()
                )
            exa_texts.extend([item.title for item in exa_data.news if item.title])
        competitor_names = []
        if competitor_data:
            competitor_names = [item.name for item in competitor_data.competitors if item.name]
        niche_classification = classify_brand_niche(
            brand_name,
            url,
            web_title=web_data.title if web_data else None,
            web_content=web_data.markdown_content if web_data else None,
            exa_texts=exa_texts,
            competitor_names=competitor_names,
        )
        if calibration_profile_override:
            calibration_profile = calibration_profile_override
            profile_source = "manual"
        else:
            calibration_profile, profile_source = select_calibration_profile(
                niche_classification,
                min_confidence=BRAND3_NICHE_AUTO_APPLY_MIN_CONFIDENCE,
            )
        print(
            "  Niche:"
            f" {niche_classification['predicted_niche']}"
            f"/{niche_classification.get('predicted_subtype') or '-'}"
            f" ({niche_classification['confidence']:.2f})"
            f" -> profile {calibration_profile} [{profile_source}]"
        )
        if run_id:
            _store_safely(
                store,
                "run classification",
                lambda: store.update_run_classification(
                    run_id,
                    niche_classification,
                    calibration_profile,
                    profile_source,
                ),
            )

        llm = None
        skip_llm_for_low_context = bool(context_data and context_data.coverage < 0.3)
        llm_skipped_reason = None
        if use_llm and not skip_llm_for_low_context:
            llm = LLMAnalyzer()
            if llm.api_key:
                print(f"  LLM: {llm.model} via Nous")
            else:
                print("  LLM: disabled (no key found)")
                llm_skipped_reason = "missing_api_key"
                llm = None
        elif use_llm and skip_llm_for_low_context:
            print("  LLM: skipped (insufficient context coverage)")
            llm_skipped_reason = "insufficient_context_coverage"

        content_web, content_source, data_sources = _build_content_web(
            url,
            brand_name,
            web_data,
            exa_data,
        )
        data_quality = _compute_data_quality(exa_data, content_source)
        partial_dimensions = list(_PARTIAL_DIMENSIONS) if data_quality == "insufficient" else []
        if content_source == "exa_fallback" and content_web:
            print(
                "  Web fallback:"
                f" using {data_sources['exa_fallback_mentions_used']} Exa mentions"
                f" as content source ({len(content_web.markdown_content)} chars aggregate)"
            )
        elif content_source == "none":
            print("  Web fallback: no usable Firecrawl or Exa content available")
        print(f"  Data quality: {data_quality}")

        _emit_progress(progress_cb, "extracting")
        _check_cancel(cancel_check)
        print("[2/4] Extracting features...")

        screenshot_url = None
        if not skip_visual_analysis:
            try:
                from src.features.visual_analyzer import VisualAnalyzer
                visual = VisualAnalyzer()
                screenshot_url = visual.take_screenshot(url).get("screenshot_url")
                if screenshot_url:
                    print("  Screenshot: captured")
            except Exception as e:
                print(f"  Screenshot: skipped ({e})")
        else:
            print("  Screenshot: skipped (benchmark mode)")

        features_by_dim = {}
        presencia_ext = PresenciaExtractor()
        features_by_dim["presencia"] = presencia_ext.extract(
            web=web_data,
            exa=exa_data,
            social=social_data,
            context=context_data,
        )

        vitalidad_ext = VitalidadExtractor(llm=llm)
        features_by_dim["vitalidad"] = vitalidad_ext.extract(web=web_data, exa=exa_data, context=context_data)

        if llm:
            coherencia_ext = CoherenciaExtractor(llm=llm, skip_visual_analysis=skip_visual_analysis)
            diferenciacion_ext = DiferenciacionExtractor(llm=llm)
            percepcion_ext = PercepcionExtractor(llm=llm)
        else:
            coherencia_ext = CoherenciaExtractor(skip_visual_analysis=skip_visual_analysis)
            diferenciacion_ext = DiferenciacionExtractor()
            percepcion_ext = PercepcionExtractor()
            if use_llm:
                print("  LLM: disabled (no API key)")

        if data_quality == "insufficient":
            features_by_dim["coherencia"] = {}
            features_by_dim["diferenciacion"] = {}
        else:
            features_by_dim["coherencia"] = coherencia_ext.extract(web=content_web, exa=exa_data, context=context_data)
            features_by_dim["diferenciacion"] = diferenciacion_ext.extract(
                web=content_web, exa=exa_data, competitor_data=competitor_data, screenshot_url=screenshot_url, context=context_data
            )
        features_by_dim["percepcion"] = percepcion_ext.extract(web=web_data, exa=exa_data, context=context_data)
        _annotate_content_source(features_by_dim, content_source)

        for dim, feats in features_by_dim.items():
            llm_feats = sum(1 for f in feats.values() if f.source == "llm")
            heuristic_feats = len(feats) - llm_feats
            src_info = f"{heuristic_feats}h" + (f"+{llm_feats}llm" if llm_feats else "")
            print(f"  {dim}: {len(feats)} features ({src_info})")

        _emit_progress(progress_cb, "scoring")
        _check_cancel(cancel_check)
        print("[3/4] Scoring...")
        engine = ScoringEngine(calibration_profile=calibration_profile)
        brand_score = engine.score_brand(
            url,
            brand_name,
            features_by_dim,
            unavailable_dimensions=set(partial_dimensions),
        )
        if data_quality == "insufficient":
            brand_score.composite_score = None
        if run_id:
            _store_safely(store, "feature save", lambda: store.save_features(run_id, features_by_dim))
            _store_safely(store, "score save", lambda: store.save_scores(run_id, brand_score))

        _emit_progress(progress_cb, "finalizing")
        _check_cancel(cancel_check)
        print("[4/4] Generating report...\n")
        summary = engine.generate_summary(brand_score)
        print(summary)

        print("\n--- Feature Details ---")
        for dim_name, dim_score in brand_score.dimensions.items():
            print(f"\n[{dim_name}]")
            if dim_score.score is None:
                print("  score unavailable  reason=insufficient_data")
                continue
            for feat_name, feat in dim_score.features.items():
                conf = f"(conf: {feat.confidence:.0%})" if feat.confidence < 1 else ""
                src = f"src={feat.source}"
                print(f"  {feat_name:30s} {feat.value:6.1f}  {conf}  {src}")
                if feat.raw_value:
                    raw_str = str(feat.raw_value)
                    raw = raw_str[:120] + "..." if len(raw_str) > 120 else raw_str
                    print(f"    raw: {raw}")

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

        result = {
            "brand": brand_score.brand_name,
            "brand_profile": _build_brand_profile(brand_score.brand_name, brand_score.url, store),
            "url": brand_score.url,
            "run_id": run_id,
            "niche_classification": niche_classification,
            "calibration_profile": calibration_profile,
            "profile_source": profile_source,
            "data_quality": data_quality,
            "data_sources": {
                **data_sources,
                "raw_input_cache": raw_input_cache,
                "llm_cache": _llm_cache_summary(llm, llm_skipped_reason),
            },
            "context_readiness": _to_jsonable(context_data),
            "confidence_summary": _context_confidence_summary(context_data),
            "dimension_confidence": dimension_confidence,
            "evidence_summary": evidence_summary,
            "composite_score": brand_score.composite_score,
            "composite_reliable": data_quality != "insufficient",
            "partial_score": data_quality == "insufficient",
            "partial_dimensions": partial_dimensions,
            "dimensions": brand_score.breakdown,
            "llm_used": use_llm and llm is not None,
            "social_scraped": social_data is not None and len(social_data.platforms) > 0,
            "audit": (
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
            ),
            "timestamp": datetime.now().isoformat(),
        }
        if run_id:
            _store_safely(store, "run audit save", lambda: store.save_run_audit(run_id, result["audit"]))

        print("\n--- JSON ---")
        print(json.dumps(result, indent=2))
        output_path = _save_result(result)
        print(f"\nSaved result to: {output_path}")
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
        return result
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
    spec_file = Path(spec_path)
    spec = json.loads(spec_file.read_text(encoding="utf-8"))
    benchmark_name = spec.get("name") or spec_file.stem
    brands = spec.get("brands", [])
    if not brands:
        raise ValueError("Benchmark spec must include at least one brand")

    selected_profiles = profiles or ["base"]
    invalid_profiles = [
        profile_id
        for profile_id in selected_profiles
        if profile_id not in {item["profile_id"] for item in list_calibration_profiles()}
    ]
    if invalid_profiles:
        raise ValueError(f"Unknown calibration profiles: {', '.join(invalid_profiles)}")

    variants = []
    if include_auto:
        variants.append({"label": "auto", "profile": None, "source": "auto"})
    for profile_id in selected_profiles:
        variants.append({"label": profile_id, "profile": profile_id, "source": "manual"})

    results = []
    summary = {
        "variants": {variant["label"]: {"count": 0, "average_composite": None} for variant in variants},
        "niche_matches": {"matched": 0, "mismatched": 0, "unscored": 0},
    }
    variant_scores: dict[str, list[float]] = {variant["label"]: [] for variant in variants}

    for brand in brands:
        url = brand["url"]
        item_results = []
        for variant in variants:
            result = run(
                url,
                brand_name=brand.get("brand_name"),
                use_llm=use_llm,
                use_social=use_social,
                use_competitors=use_competitors,
                calibration_profile_override=variant["profile"],
                skip_visual_analysis=True,
            )
            expected_niche = brand.get("expected_niche")
            expected_subtype = brand.get("expected_subtype")
            predicted_niche = result.get("niche_classification", {}).get("predicted_niche")
            predicted_subtype = result.get("niche_classification", {}).get("predicted_subtype")
            niche_match = None if not expected_niche else expected_niche == predicted_niche
            subtype_match = None if not expected_subtype else expected_subtype == predicted_subtype
            if expected_niche:
                if niche_match:
                    summary["niche_matches"]["matched"] += 1
                else:
                    summary["niche_matches"]["mismatched"] += 1
            else:
                summary["niche_matches"]["unscored"] += 1
            summary.setdefault("subtype_matches", {"matched": 0, "mismatched": 0, "unscored": 0})
            if expected_subtype:
                if subtype_match:
                    summary["subtype_matches"]["matched"] += 1
                else:
                    summary["subtype_matches"]["mismatched"] += 1
            else:
                summary["subtype_matches"]["unscored"] += 1

            variant_payload = {
                "variant": variant["label"],
                "profile_source": result.get("profile_source"),
                "calibration_profile": result.get("calibration_profile"),
                "run_id": result.get("run_id"),
                "composite_score": result.get("composite_score"),
                "dimensions": result.get("dimensions"),
                "predicted_niche": predicted_niche,
                "predicted_subtype": predicted_subtype,
                "niche_confidence": result.get("niche_classification", {}).get("confidence"),
                "expected_niche": expected_niche,
                "expected_subtype": expected_subtype,
                "niche_match": niche_match,
                "subtype_match": subtype_match,
            }
            item_results.append(variant_payload)
            if variant_payload["composite_score"] is not None:
                variant_scores[variant["label"]].append(float(variant_payload["composite_score"]))

        results.append(
            {
                "brand_name": brand.get("brand_name"),
                "url": url,
                "notes": brand.get("notes"),
                "results": item_results,
            }
        )

    for variant in variants:
        label = variant["label"]
        scores = variant_scores[label]
        summary["variants"][label]["count"] = len(scores)
        summary["variants"][label]["average_composite"] = round(mean(scores), 1) if scores else None

    payload = {
        "benchmark_name": benchmark_name,
        "spec_path": str(spec_file),
        "generated_at": datetime.now().isoformat(),
        "use_llm": use_llm,
        "use_social": use_social,
        "use_competitors": use_competitors,
        "variants": variants,
        "summary": summary,
        "brands": results,
    }
    output_path = _save_benchmark_result(payload)
    payload["output_path"] = str(output_path)
    print(json.dumps(payload, indent=2))
    return payload


def compare_benchmarks(before_path: str, after_path: str) -> dict:
    before_file = Path(before_path)
    after_file = Path(after_path)
    before_payload = json.loads(before_file.read_text(encoding="utf-8"))
    after_payload = json.loads(after_file.read_text(encoding="utf-8"))

    def _brand_key(item: dict) -> tuple[str, str]:
        return (item.get("brand_name") or "", item.get("url") or "")

    def _variant_map(item: dict) -> dict[str, dict]:
        return {result["variant"]: result for result in item.get("results", [])}

    before_brands = {_brand_key(item): item for item in before_payload.get("brands", [])}
    after_brands = {_brand_key(item): item for item in after_payload.get("brands", [])}

    shared_keys = sorted(set(before_brands) & set(after_brands))
    added_keys = sorted(set(after_brands) - set(before_brands))
    removed_keys = sorted(set(before_brands) - set(after_brands))

    variant_deltas: dict[str, list[float]] = {}
    variant_match_changes: dict[str, dict[str, int]] = {}
    brand_results = []

    for key in shared_keys:
        before_brand = before_brands[key]
        after_brand = after_brands[key]
        before_variants = _variant_map(before_brand)
        after_variants = _variant_map(after_brand)
        shared_variants = sorted(set(before_variants) & set(after_variants))
        comparisons = []

        for variant in shared_variants:
            before_variant = before_variants[variant]
            after_variant = after_variants[variant]
            before_composite = before_variant.get("composite_score")
            after_composite = after_variant.get("composite_score")
            delta = None
            if before_composite is not None and after_composite is not None:
                delta = round(float(after_composite) - float(before_composite), 1)
                variant_deltas.setdefault(variant, []).append(delta)

            dimension_names = sorted(
                set((before_variant.get("dimensions") or {}).keys())
                | set((after_variant.get("dimensions") or {}).keys())
            )
            dimension_deltas = {}
            for dimension_name in dimension_names:
                before_value = (before_variant.get("dimensions") or {}).get(dimension_name)
                after_value = (after_variant.get("dimensions") or {}).get(dimension_name)
                if before_value is None or after_value is None:
                    dimension_deltas[dimension_name] = {
                        "before": before_value,
                        "after": after_value,
                        "delta": None,
                    }
                else:
                    dimension_deltas[dimension_name] = {
                        "before": before_value,
                        "after": after_value,
                        "delta": round(float(after_value) - float(before_value), 1),
                    }

            match_stats = variant_match_changes.setdefault(
                variant,
                {
                    "niche_match_improved": 0,
                    "niche_match_worsened": 0,
                    "subtype_match_improved": 0,
                    "subtype_match_worsened": 0,
                },
            )
            before_niche_match = before_variant.get("niche_match")
            after_niche_match = after_variant.get("niche_match")
            if before_niche_match is False and after_niche_match is True:
                match_stats["niche_match_improved"] += 1
            elif before_niche_match is True and after_niche_match is False:
                match_stats["niche_match_worsened"] += 1

            before_subtype_match = before_variant.get("subtype_match")
            after_subtype_match = after_variant.get("subtype_match")
            if before_subtype_match is False and after_subtype_match is True:
                match_stats["subtype_match_improved"] += 1
            elif before_subtype_match is True and after_subtype_match is False:
                match_stats["subtype_match_worsened"] += 1

            comparisons.append(
                {
                    "variant": variant,
                    "before": {
                        "composite_score": before_composite,
                        "predicted_niche": before_variant.get("predicted_niche"),
                        "predicted_subtype": before_variant.get("predicted_subtype"),
                        "niche_match": before_niche_match,
                        "subtype_match": before_subtype_match,
                    },
                    "after": {
                        "composite_score": after_composite,
                        "predicted_niche": after_variant.get("predicted_niche"),
                        "predicted_subtype": after_variant.get("predicted_subtype"),
                        "niche_match": after_niche_match,
                        "subtype_match": after_subtype_match,
                    },
                    "composite_delta": delta,
                    "dimension_deltas": dimension_deltas,
                }
            )

        brand_results.append(
            {
                "brand_name": after_brand.get("brand_name"),
                "url": after_brand.get("url"),
                "variant_comparisons": comparisons,
            }
        )

    summary = {
        "shared_brands": len(shared_keys),
        "added_brands": len(added_keys),
        "removed_brands": len(removed_keys),
        "variant_deltas": {
            variant: {
                "count": len(deltas),
                "average_composite_delta": round(mean(deltas), 1) if deltas else None,
                **variant_match_changes.get(variant, {}),
            }
            for variant, deltas in variant_deltas.items()
        },
    }

    payload = {
        "before_benchmark": before_payload.get("benchmark_name") or before_file.stem,
        "after_benchmark": after_payload.get("benchmark_name") or after_file.stem,
        "before_path": str(before_file),
        "after_path": str(after_file),
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "brands": brand_results,
        "added_brand_keys": [{"brand_name": key[0], "url": key[1]} for key in added_keys],
        "removed_brand_keys": [{"brand_name": key[0], "url": key[1]} for key in removed_keys],
    }
    output_path = _save_benchmark_comparison_result(payload)
    payload["output_path"] = str(output_path)
    print(json.dumps(payload, indent=2))
    return payload


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
        dimension_status_counts = _dimension_status_counts(dimension_confidence)
        payload = {
            "run_id": run_id,
            "data_quality": run_payload.get("data_quality") or "unknown",
            "context_readiness": context_summary,
            "evidence_summary": evidence_summary,
            "dimension_confidence": dimension_confidence,
            "dimension_status_counts": dimension_status_counts,
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
            "coverage_label": _quality_label(coverage),
            "confidence_label": _quality_label(confidence),
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


def _dimension_status_counts(dimension_confidence: dict) -> dict[str, int]:
    counts = {"good": 0, "degraded": 0, "insufficient_data": 0}
    for item in (dimension_confidence or {}).values():
        status = item.get("status") if isinstance(item, dict) else None
        if status in counts:
            counts[status] += 1
    return counts


def _quality_label(value: float) -> str:
    if value >= 0.75:
        return "alta"
    if value >= 0.45:
        return "media"
    return "baja"


def brand_report(brand_name: str, limit: int = 10) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        report = store.get_brand_report(brand_name, limit=limit)
        runs = report["runs"]
        if not runs:
            print(json.dumps(report, indent=2))
            return report

        composites = [run["composite_score"] for run in runs if run["composite_score"] is not None]
        newest = composites[0] if composites else None
        oldest = composites[-1] if composites else None
        trend = None
        if newest is not None and oldest is not None and len(composites) >= 2:
            trend = round(newest - oldest, 1)

        dimensions_summary = {}
        for dimension_name, series in report["dimension_series"].items():
            values = [item["score"] for item in series]
            dimensions_summary[dimension_name] = {
                "latest": values[0],
                "average": round(mean(values), 1),
                "trend": round(values[0] - values[-1], 1) if len(values) >= 2 else 0.0,
                "samples": len(values),
            }

        feedback_summary = {
            "count": len(report["annotations"]),
            "dimensions": {},
        }
        for annotation in report["annotations"]:
            dim = annotation.get("dimension_name") or "general"
            feedback_summary["dimensions"][dim] = feedback_summary["dimensions"].get(dim, 0) + 1

        payload = {
            "brand_name": brand_name,
            "brand_profile": report.get("brand_profile"),
            "run_count": len(runs),
            "latest_composite": newest,
            "average_composite": round(mean(composites), 1) if composites else None,
            "composite_trend": trend,
            "latest_scoring_state_fingerprint": runs[0].get("scoring_state_fingerprint"),
            "latest_predicted_niche": runs[0].get("predicted_niche"),
            "latest_predicted_subtype": runs[0].get("predicted_subtype"),
            "latest_niche_confidence": runs[0].get("niche_confidence"),
            "latest_calibration_profile": runs[0].get("calibration_profile"),
            "scoring_states": {},
            "dimensions": dimensions_summary,
            "feedback": feedback_summary,
            "recent_runs": runs,
        }
        for run_item in runs:
            fingerprint = run_item.get("scoring_state_fingerprint")
            if fingerprint:
                payload["scoring_states"][fingerprint] = payload["scoring_states"].get(fingerprint, 0) + 1
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def propose_calibration(brand_name: str, limit: int = 20, persist: bool = False) -> list[dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        report = store.get_brand_report(brand_name, limit=limit)
        analyzer = CalibrationAnalyzer()
        candidates = analyzer.propose_candidates(report, report.get("annotations", []))

        payload = []
        for candidate in candidates:
            item = {
                "scope": candidate.scope,
                "target": candidate.target,
                "proposal": candidate.proposal,
                "rationale": candidate.rationale,
                "severity": candidate.severity,
                "evidence": candidate.evidence,
            }
            if persist:
                item["candidate_id"] = store.save_calibration_candidate(
                    brand_name=brand_name,
                    scope=candidate.scope,
                    target=candidate.target,
                    proposal=candidate.proposal,
                    rationale=candidate.rationale,
                )
            payload.append(item)

        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def list_candidates(brand_name: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        candidates = store.list_calibration_candidates(brand_name=brand_name, status=status, limit=limit)
        print(json.dumps(candidates, indent=2))
        return candidates
    finally:
        store.close()


def review_candidate(candidate_id: int, status: str) -> dict:
    if status not in {"approved", "rejected", "proposed", "applied"}:
        raise ValueError("Status must be one of: proposed, approved, rejected, applied")
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        candidate = store.get_calibration_candidate(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")
        store.update_calibration_candidate_status(candidate_id, status)
        candidate["status"] = status
        print(json.dumps(candidate, indent=2))
        return candidate
    finally:
        store.close()


def apply_candidates(candidate_ids: list[int] | None = None, brand_name: str | None = None) -> list[dict]:
    dimensions_path = str(DIMENSIONS_PATH)
    engine_path = str(ENGINE_PATH)
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        if candidate_ids:
            candidates = []
            for candidate_id in candidate_ids:
                candidate = store.get_calibration_candidate(candidate_id)
                if not candidate:
                    raise ValueError(f"Candidate {candidate_id} not found")
                candidates.append(candidate)
        else:
            candidates = store.list_calibration_candidates(brand_name=brand_name, status="approved", limit=100)

        version_before_id = None
        version_after_id = None
        results = []
        for candidate in candidates:
            if candidate["status"] != "approved":
                results.append({
                    "candidate_id": candidate["id"],
                    "applied": False,
                    "reason": f"Candidate status is {candidate['status']}, not approved",
                })
                continue
            try:
                if version_before_id is None:
                    state_before = _read_calibration_state(store)
                    version_before_id = store.save_calibration_version(
                        label=f"before-apply-{datetime.now().isoformat()}",
                        dimensions_content=state_before["dimensions_content"],
                        engine_content=state_before["engine_content"],
                        gate_config=state_before["gate_config"],
                    )
                applied = apply_candidate(dimensions_path, engine_path, candidate)
                applied["candidate_id"] = candidate["id"]
                results.append(applied)
                if applied["applied"]:
                    state_after = _read_calibration_state(store)
                    version_after_id = store.save_calibration_version(
                        label=f"after-apply-{datetime.now().isoformat()}",
                        dimensions_content=state_after["dimensions_content"],
                        engine_content=state_after["engine_content"],
                        gate_config=state_after["gate_config"],
                    )
                    applied["version_before_id"] = version_before_id
                    applied["version_after_id"] = version_after_id
                    store.update_calibration_candidate_status(candidate["id"], "applied")
                    store.save_applied_calibration(candidate["id"], version_before_id, version_after_id)
            except CandidateApplyError as e:
                results.append({
                    "candidate_id": candidate["id"],
                    "applied": False,
                    "reason": str(e),
                })

        print(json.dumps(results, indent=2))
        return results
    finally:
        store.close()


def run_experiment(brand_name: str, candidate_ids: list[int] | None = None) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        before_run_id = store.get_latest_run_id(brand_name=brand_name)
        if not before_run_id:
            raise ValueError(f"No runs found for brand {brand_name}")
        before_snapshot = store.get_run_snapshot(before_run_id)
        if not before_snapshot:
            raise ValueError(f"Run {before_run_id} not found")
        baseline = before_snapshot["run"]
    finally:
        store.close()

    applied_results = apply_candidates(candidate_ids=candidate_ids, brand_name=brand_name)
    applied_candidate_ids = [item["candidate_id"] for item in applied_results if item.get("applied")]
    if not applied_candidate_ids:
        raise ValueError("No approved candidates were applied; experiment aborted")
    applied_version_before_id = next(
        (item["version_before_id"] for item in applied_results if item.get("applied") and item.get("version_before_id")),
        None,
    )
    applied_version_after_id = None
    for item in applied_results:
        if item.get("applied") and item.get("version_after_id"):
            applied_version_after_id = item["version_after_id"]

    rerun_result = run(
        baseline["url"],
        brand_name=baseline["brand_name"],
        use_llm=bool(baseline["use_llm"]),
        use_social=bool(baseline["use_social"]),
    )
    after_run_id = rerun_result.get("run_id")
    if not after_run_id:
        raise ValueError("Rerun did not produce a persisted run_id")

    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        after_snapshot = store.get_run_snapshot(after_run_id)
        if not after_snapshot:
            raise ValueError(f"Run {after_run_id} not found after rerun")

        summary = _build_experiment_summary(before_snapshot, after_snapshot, applied_results)
        experiment_id = store.save_experiment(
            brand_name=baseline["brand_name"],
            url=baseline["url"],
            before_run_id=before_run_id,
            after_run_id=after_run_id,
            candidate_ids=applied_candidate_ids,
            summary=summary,
            version_before_id=applied_version_before_id,
            version_after_id=applied_version_after_id,
            before_scoring_state_fingerprint=before_snapshot["run"].get("scoring_state_fingerprint"),
            after_scoring_state_fingerprint=after_snapshot["run"].get("scoring_state_fingerprint"),
        )
        payload = {
            "experiment_id": experiment_id,
            "apply_results": applied_results,
            "summary": summary,
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def list_experiments(brand_name: str | None = None, limit: int = 20) -> list[dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        experiments = store.list_experiments(brand_name=brand_name, limit=limit)
        print(json.dumps(experiments, indent=2))
        return experiments
    finally:
        store.close()


def list_versions(limit: int = 20) -> list[dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        versions = store.list_calibration_versions(limit=limit)
        print(json.dumps(versions, indent=2))
        return versions
    finally:
        store.close()


def rollback_version(version_id: int) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        version = store.get_calibration_version(version_id)
        if not version:
            raise ValueError(f"Calibration version {version_id} not found")
        current_state = _read_calibration_state(store)
        rollback_source_id = store.save_calibration_version(
            label=f"pre-rollback-{datetime.now().isoformat()}",
            dimensions_content=current_state["dimensions_content"],
            engine_content=current_state["engine_content"],
            gate_config=current_state["gate_config"],
        )
        _restore_calibration_state(version, store)
        restored_state = _read_calibration_state(store)
        restored_version_id = store.save_calibration_version(
            label=f"rollback-to-{version_id}",
            dimensions_content=restored_state["dimensions_content"],
            engine_content=restored_state["engine_content"],
            gate_config=restored_state["gate_config"],
        )
        payload = {
            "rolled_back": True,
            "target_version_id": version_id,
            "rollback_source_version_id": rollback_source_id,
            "restored_version_id": restored_version_id,
            "label": version["label"],
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def promote_baseline(version_id: int, label: str | None = None, force: bool = False) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        version = store.get_calibration_version(version_id)
        if not version:
            raise ValueError(f"Calibration version {version_id} not found")
        experiment = store.get_latest_experiment_for_version(version_id)
        gate = _evaluate_promotion_gate(experiment, gate_config=version.get("gate_config"))
        if not gate["allowed"] and not force:
            payload = {
                "promoted": False,
                "version_id": version_id,
                "label": label or version["label"],
                "gate": gate,
            }
            print(json.dumps(payload, indent=2))
            return payload
        if version.get("gate_config") is not None:
            store.upsert_gate_config(version["gate_config"])
        baseline_id = store.promote_baseline(version_id=version_id, label=label or version["label"])
        payload = {
            "baseline_id": baseline_id,
            "version_id": version_id,
            "label": label or version["label"],
            "promoted": True,
            "forced": force,
            "gate": gate,
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def list_baselines(limit: int = 20) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        payload = {
            "active": store.get_active_baseline(),
            "history": store.list_baselines(limit=limit),
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def get_gate_config() -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        payload = _load_gate_config(store)
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def set_gate_config(max_composite_drop: float | None = None, dimension_drops: dict | None = None) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        current = _load_gate_config(store)
        if max_composite_drop is not None:
            current["max_composite_drop"] = float(max_composite_drop)
        if dimension_drops:
            merged = dict(current.get("max_dimension_drops", {}))
            merged.update({key: float(value) for key, value in dimension_drops.items()})
            current["max_dimension_drops"] = merged
        store.upsert_gate_config(current)
        print(json.dumps(current, indent=2))
        return current
    finally:
        store.close()


def compare_version(version_id: int, brand_name: str) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        version = store.get_calibration_version(version_id)
        if not version:
            raise ValueError(f"Calibration version {version_id} not found")

        target_experiment = store.get_latest_experiment_for_version(version_id, brand_name=brand_name)
        active_baseline = store.get_active_baseline()
        baseline_experiment = None
        if active_baseline:
            baseline_experiment = store.get_latest_experiment_for_version(
                active_baseline["version_id"],
                brand_name=brand_name,
            )

        payload = {
            "brand_name": brand_name,
            "target_version": {
                "id": version["id"],
                "label": version["label"],
            },
            "target_gate": _evaluate_promotion_gate(
                target_experiment,
                gate_config=version.get("gate_config") or _load_gate_config(store),
            ),
            "target_experiment": target_experiment,
            "active_baseline": active_baseline,
            "baseline_experiment": baseline_experiment,
            "comparison": _compare_summaries(
                target_experiment.get("summary") if target_experiment else None,
                baseline_experiment.get("summary") if baseline_experiment else None,
            ),
        }
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def enqueue_analysis_job(
    url: str,
    brand_name: str | None = None,
    use_llm: bool = True,
    use_social: bool = True,
) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        job_id = store.create_analysis_job(
            url=url,
            brand_name=brand_name,
            use_llm=use_llm,
            use_social=use_social,
        )
        payload = store.get_analysis_job(job_id)
        print(json.dumps(payload, indent=2))
        return payload
    finally:
        store.close()


def get_analysis_job(job_id: int) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        job = store.get_analysis_job(job_id)
        if not job:
            raise ValueError(f"Analysis job {job_id} not found")
        print(json.dumps(job, indent=2))
        return job
    finally:
        store.close()


def list_analysis_jobs(
    brand_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        jobs = store.list_analysis_jobs(brand_name=brand_name, status=status, limit=limit)
        print(json.dumps(jobs, indent=2))
        return jobs
    finally:
        store.close()


def execute_analysis_job(job_id: int) -> dict:
    """Atomically claim a queued job by id and run it to completion."""
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        existing = store.get_analysis_job(job_id)
        if not existing:
            raise ValueError(f"Analysis job {job_id} not found")
        if existing["status"] != "queued":
            return existing
        if existing.get("cancel_requested"):
            store.cancel_analysis_job(job_id)
            cancelled = store.get_analysis_job(job_id)
            print(json.dumps(cancelled, indent=2))
            return cancelled
        claimed = store.claim_pending_job(job_id=job_id)
        if not claimed:
            return store.get_analysis_job(job_id)
    finally:
        store.close()

    return run_claimed_job(claimed)


def run_claimed_job(job: dict) -> dict:
    """Run the pipeline for a job already claimed (status='running').

    Intended for the polling worker: `claim_pending_job()` returns the claimed
    job, which is then passed here. Callers with a specific job id should use
    `execute_analysis_job(job_id)` instead — it handles the claim.
    """
    job_id = int(job["id"])

    def progress_cb(phase: str) -> None:
        progress_store = SQLiteStore(BRAND3_DB_PATH)
        try:
            progress_store.update_analysis_job_phase(job_id, phase)
        finally:
            progress_store.close()

    def cancel_check() -> bool:
        progress_store = SQLiteStore(BRAND3_DB_PATH)
        try:
            current = progress_store.get_analysis_job(job_id)
            return bool(current and (current.get("cancel_requested") or current.get("status") == "cancelled"))
        finally:
            progress_store.close()

    try:
        result = run(
            job["url"],
            brand_name=job.get("brand_name"),
            use_llm=bool(job.get("use_llm")),
            use_social=bool(job.get("use_social")),
            progress_cb=progress_cb,
            cancel_check=cancel_check,
        )
        store = SQLiteStore(BRAND3_DB_PATH)
        try:
            store.complete_analysis_job(job_id, result.get("run_id"), result)
            completed = store.get_analysis_job(job_id)
            print(json.dumps(completed, indent=2))
            return completed
        finally:
            store.close()
    except AnalysisJobCancelled as exc:
        store = SQLiteStore(BRAND3_DB_PATH)
        try:
            store.cancel_analysis_job(job_id, str(exc))
            cancelled = store.get_analysis_job(job_id)
            print(json.dumps(cancelled, indent=2))
            return cancelled
        finally:
            store.close()
    except Exception as exc:
        store = SQLiteStore(BRAND3_DB_PATH)
        try:
            store.fail_analysis_job(job_id, str(exc))
            failed = store.get_analysis_job(job_id)
            print(json.dumps(failed, indent=2))
            return failed
        finally:
            store.close()


def claim_next_job(worker_id: str | None = None) -> dict | None:
    """Claim the oldest queued job for a worker. Returns None if nothing pending."""
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        return store.claim_pending_job(worker_id=worker_id)
    finally:
        store.close()


def cancel_analysis_job(job_id: int) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        job = store.get_analysis_job(job_id)
        if not job:
            raise ValueError(f"Analysis job {job_id} not found")
        if job["status"] in {"done", "failed", "cancelled"}:
            print(json.dumps(job, indent=2))
            return job
        store.request_analysis_job_cancel(job_id)
        updated = store.get_analysis_job(job_id)
        print(json.dumps(updated, indent=2))
        return updated
    finally:
        store.close()


def retry_analysis_job(job_id: int) -> dict:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        job = store.get_analysis_job(job_id)
        if not job:
            raise ValueError(f"Analysis job {job_id} not found")
        if job["status"] not in {"failed", "cancelled"}:
            raise ValueError(f"Analysis job {job_id} is not retryable from status {job['status']}")
        store.requeue_analysis_job(job_id)
        queued = store.get_analysis_job(job_id)
        print(json.dumps(queued, indent=2))
        return queued
    finally:
        store.close()
