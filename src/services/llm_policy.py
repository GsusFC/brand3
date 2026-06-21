"""LLM provider, cache, and cost-policy summaries for service payloads."""

from __future__ import annotations

from typing import Any

from src.collectors.context_collector import ContextData


def _llm_cache_summary(llm: Any | None, skipped_reason: str | None = None) -> dict[str, object]:
    if llm is None:
        return {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_writes": 0,
            "skipped_reason": skipped_reason,
            "call_failures": [],
        }
    hits = int(getattr(llm, "cache_hits", 0) or 0)
    misses = int(getattr(llm, "cache_misses", 0) or 0)
    writes = int(getattr(llm, "cache_writes", 0) or 0)
    failures = list(getattr(llm, "call_failures", []) or [])
    return {
        "cache_hits": hits,
        "cache_misses": misses,
        "cache_writes": writes,
        "skipped_reason": skipped_reason,
        "call_failures": failures,
        "estimated_cost_saved_units": hits,
    }


def _infer_llm_provider(base_url: str | None) -> str:
    normalized = (base_url or "").lower()
    if "generativelanguage.googleapis.com" in normalized:
        return "Google AI Studio / Gemini"
    if "openrouter.ai" in normalized:
        return "OpenRouter"
    if "nous" in normalized:
        return "Nous"
    return "OpenAI-compatible"


def _llm_provider_payload(llm: Any | None) -> dict[str, object] | None:
    if llm is None:
        return None
    base_url = getattr(llm, "base_url", "") or ""
    return {
        "provider": _infer_llm_provider(base_url),
        "model": getattr(llm, "model", ""),
        "base_url": base_url,
        "openai_compatible": True,
    }


def _llm_model_roles_payload(
    *,
    default_model: str,
    cheap_model: str,
    premium_model: str,
    audit_analyst_model: str,
    vision_model: str,
) -> dict[str, str]:
    return {
        "default": default_model,
        "cheap": cheap_model,
        "premium": premium_model,
        "audit_analyst": audit_analyst_model,
        "vision": vision_model,
    }


def _audit_analyst_llm(
    feature_llm: Any | None,
    *,
    analyzer_cls: type,
    audit_analyst_model: str,
) -> Any | None:
    if feature_llm is None:
        return None
    if getattr(feature_llm, "model", None) == audit_analyst_model:
        return feature_llm
    candidate = analyzer_cls(model=audit_analyst_model)
    return candidate if getattr(candidate, "api_key", None) else None


def _cost_policy_summary(
    *,
    raw_input_cache: dict[str, str],
    llm_cache: dict[str, object],
    use_llm: bool,
    use_social: bool,
    social_limitation: str | None = None,
    use_competitors: bool,
    skip_visual_analysis: bool,
    context_data: ContextData | None,
    data_quality: str,
) -> dict[str, object]:
    skipped: dict[str, str] = {}
    if not use_llm:
        skipped["llm"] = "disabled_by_request"
    elif llm_cache.get("skipped_reason"):
        skipped["llm"] = str(llm_cache["skipped_reason"])
    elif llm_cache.get("call_failures"):
        skipped["llm_feature_calls"] = "partial_timeout_or_error"
    if not use_social:
        skipped["social"] = "disabled_by_request"
    elif social_limitation:
        skipped["social"] = f"collection_{social_limitation}"
    if not use_competitors:
        skipped["competitors"] = "disabled_by_request"
    if skip_visual_analysis:
        skipped["visual_analysis"] = "disabled_by_request"
    if context_data and context_data.coverage < 0.3:
        skipped.setdefault("deep_llm_narrative", "insufficient_context_coverage")
    if data_quality == "insufficient":
        skipped.setdefault("coherencia_deep_analysis", "insufficient_primary_data")
        skipped.setdefault("diferenciacion_deep_analysis", "insufficient_primary_data")

    cache_hits = sum(1 for state in raw_input_cache.values() if state == "hit")
    cache_misses = sum(1 for state in raw_input_cache.values() if state == "miss")
    return {
        "raw_input_cache": dict(raw_input_cache),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "llm_cache_hits": int(llm_cache.get("cache_hits") or 0),
        "llm_cache_misses": int(llm_cache.get("cache_misses") or 0),
        "skipped": skipped,
        "estimated_saved_operations": cache_hits + int(llm_cache.get("cache_hits") or 0) + len(skipped),
    }
