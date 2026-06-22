"""Analyst Pass for TLDR Brand3.

This module coordinates LLM calls and delegates prompt/schema/normalization
logic to the dedicated support module.
"""

from __future__ import annotations

from typing import Any

from src.features.magnetism.tldr_guardrails import validate_analyst_tldr
from src.features.magnetism.analyst_tldr_support import (
    ANALYST_TLDR_PROMPT_VERSION,
    ANALYST_TLDR_SOURCE_RULES,
    ANALYST_TLDR_NEGATIVE_EXAMPLES,
    ANALYST_BLOCK_QUESTIONS,
    ANALYST_TLDR_SYSTEM_PROMPT,
    ANALYST_TLDR_TIMEOUT_SECONDS,
    SYSTEM_READING_PROMPT_VERSION,
    SYSTEM_READING_TIMEOUT_SECONDS,
    TLDR_KEYS,
    _analyst_tldr_timeout_seconds,
    _coerce_analyst_raw_json,
    _coerce_system_reading_raw_json,
    _fallback_payload,
    _normalize_scoring_context,
    build_analyst_tldr_prompt,
    _system_reading_system_prompt,
    system_reading_response_schema,
    build_system_reading_prompt,
    normalize_system_reading,
    _system_reading_timeout_seconds,
    analyst_tldr_response_schema,
    normalize_analyst_response,
)


def maybe_build_analyst_tldr(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    research_pack: Any,
    current_tldr: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Run the Analyst Pass and return a normalized TLDR payload.

    On LLM failure the function returns the current TLDR, if present, together
    with a controlled ``analysis_error`` field so the caller can keep the existing
    reading.
    """
    if llm is None or not getattr(llm, "api_key", None):
        return None

    result = run_analyst_tldr_pass(
        llm=llm,
        brand_name=brand_name,
        url=url,
        research_pack=research_pack,
        current_tldr=current_tldr,
    )
    if result.get("analysis_error"):
        validated = result.get("validated")
        if isinstance(validated, dict):
            payload = dict(validated)
        else:
            payload = _fallback_payload(
                current_tldr=current_tldr,
                reason=str(result["analysis_error"].get("reason") or "llm_error"),
                detail=str(result["analysis_error"].get("detail") or "The analyst pass failed."),
            )
        payload["analysis_error"] = result["analysis_error"]
        if "raw" in result:
            payload["analysis_raw"] = result.get("raw") or {}
        return payload
    validated = result.get("validated")
    if not isinstance(validated, dict) or not validated.get("tldr_brand3"):
        return _fallback_payload(
            current_tldr=current_tldr,
            reason="empty_tldr",
            detail="The analyst pass returned no usable TLDR blocks.",
        )
    return validated


def maybe_build_system_reading(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    tldr: dict[str, Any],
    layers: dict[str, Any],
    metrics: dict[str, Any],
    evidence_packet_summary: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Run the LLM system-reading pass and return normalized output.

    The extractor treats missing/invalid responses as a non-fatal condition and
    falls back to deterministic heuristics.
    """
    if llm is None or not getattr(llm, "api_key", None):
        return None

    result = run_system_reading_pass(
        llm=llm,
        brand_name=brand_name,
        url=url,
        tldr=tldr,
        layers=layers,
        metrics=metrics,
        evidence_packet_summary=evidence_packet_summary,
    )
    if result.get("analysis_error"):
        return None
    validated = result.get("validated")
    if not isinstance(validated, dict) or not validated.get("strategic_tensions"):
        return None
    return validated


def run_system_reading_pass(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    tldr: dict[str, Any],
    layers: dict[str, Any],
    metrics: dict[str, Any],
    evidence_packet_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the LLM once and return raw + validated system reading payload."""
    if llm is None or not getattr(llm, "api_key", None):
        return {
            "analysis_error": {
                "reason": "llm_unavailable",
                "detail": "No LLM API key is available for system reading.",
            },
        }

    prompt = build_system_reading_prompt(
        brand_name=brand_name,
        url=url,
        tldr=tldr,
        layers=layers,
        metrics=metrics,
        evidence_packet_summary=evidence_packet_summary,
    )
    raw_response = None
    try:
        try:
            raw_response = llm._call_json(
                _system_reading_system_prompt(),
                prompt,
                max_tokens=3000,
                json_schema=system_reading_response_schema(),
                schema_name="brand3_system_reading",
                timeout_seconds=_system_reading_timeout_seconds(),
            )
        except TypeError:
            raw_response = llm._call_json(
                _system_reading_system_prompt(),
                prompt,
                max_tokens=3000,
            )
    except Exception:
        raw_response = None
    if raw_response is None:
        try:
            raw_response = llm._call_json(
                _system_reading_system_prompt(),
                prompt,
            )
        except Exception:
            raw_response = None
    if raw_response is None:
        return {
            "analysis_error": {
                "reason": "llm_error",
                "detail": "Unable to call the LLM system reading endpoint.",
            },
        }
    raw = _coerce_system_reading_raw_json(raw_response)
    if not isinstance(raw, dict) or not raw:
        failure = _latest_llm_failure(llm)
        reason = str(failure.get("reason") or "llm_error")
        detail = str(failure.get("error") or "The system reading pass did not return usable JSON.")
        return {
            "analysis_error": {
                "reason": reason,
                "detail": detail,
                "error_type": failure.get("error_type"),
                "model": failure.get("model"),
            },
            "raw": raw_response if isinstance(raw_response, dict) else {},
        }

    validated = normalize_system_reading(raw)
    return {
        "raw": raw,
        "validated": validated,
    }


def run_analyst_tldr_pass(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    research_pack: Any,
    current_tldr: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the analyst LLM once and return raw, normalized, and validated payloads."""
    if llm is None or not getattr(llm, "api_key", None):
        return {
            "analysis_error": {
                "reason": "llm_unavailable",
                "detail": "No LLM API key is available for the Analyst Pass.",
            },
            "validated": _fallback_payload(
                current_tldr=current_tldr,
                reason="llm_unavailable",
                detail="No LLM API key is available for the Analyst Pass.",
            ),
        }

    prompt = build_analyst_tldr_prompt(
        brand_name=brand_name,
        url=url,
        research_pack=research_pack,
        current_tldr=current_tldr,
    )
    raw_response = llm._call_json(
        ANALYST_TLDR_SYSTEM_PROMPT,
        prompt,
        max_tokens=9000,
        json_schema=analyst_tldr_response_schema(),
        schema_name="brand3_analyst_tldr",
        timeout_seconds=_analyst_tldr_timeout_seconds(),
    )
    raw = _coerce_analyst_raw_json(raw_response)
    if not raw and str(_latest_llm_failure(llm).get("reason") or "") == "schema_validation_error":
        raw = _coerce_analyst_raw_json(getattr(llm, "last_raw_response", None))
    if not isinstance(raw, dict) or not raw:
        failure = _latest_llm_failure(llm)
        reason = str(failure.get("reason") or "llm_error")
        detail = str(failure.get("error") or "The analyst pass did not return usable JSON.")
        return {
            "analysis_error": {
                "reason": reason,
                "detail": detail,
                "error_type": failure.get("error_type"),
                "model": failure.get("model"),
            },
            "raw": raw_response if isinstance(raw_response, dict) else {},
            "validated": _fallback_payload(
                current_tldr=current_tldr,
                reason=reason,
                detail=detail,
            ),
        }

    normalized = normalize_analyst_response(raw, current_tldr=current_tldr, research_pack=research_pack)
    validated = validate_analyst_tldr(normalized, research_pack)
    return {
        "raw": raw,
        "normalized": normalized,
        "validated": validated,
    }


def _latest_llm_failure(llm: Any) -> dict[str, Any]:
    failures = getattr(llm, "call_failures", None)
    if isinstance(failures, list) and failures:
        latest = failures[-1]
        if isinstance(latest, dict):
            return latest
    reason = getattr(llm, "last_failure_reason", None)
    if reason:
        return {"reason": str(reason)}
    return {}


__all__ = [
    "ANALYST_TLDR_PROMPT_VERSION",
    "ANALYST_TLDR_SOURCE_RULES",
    "ANALYST_TLDR_NEGATIVE_EXAMPLES",
    "ANALYST_BLOCK_QUESTIONS",
    "ANALYST_TLDR_SYSTEM_PROMPT",
    "ANALYST_TLDR_TIMEOUT_SECONDS",
    "SYSTEM_READING_PROMPT_VERSION",
    "SYSTEM_READING_TIMEOUT_SECONDS",
    "TLDR_KEYS",
    "maybe_build_analyst_tldr",
    "maybe_build_system_reading",
    "run_system_reading_pass",
    "run_analyst_tldr_pass",
    "system_reading_response_schema",
    "build_system_reading_prompt",
    "normalize_system_reading",
    "build_analyst_tldr_prompt",
    "analyst_tldr_response_schema",
    "normalize_analyst_response",
]

