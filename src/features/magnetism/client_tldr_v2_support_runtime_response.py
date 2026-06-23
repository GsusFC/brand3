"""LLM transport and raw response helpers for client TLDR v2 runtime."""

from __future__ import annotations

from typing import Any, Callable

from src.features.magnetism.client_tldr_v2_support_contract import (
    _client_tldr_v2_system_prompt,
    _coerce_client_tldr_v2_raw_json,
    _parse_plain_text_client_tldr_v2,
    _safe_raw_response_preview,
    CLIENT_TLDR_V2_TIMEOUT_SECONDS,
    client_tldr_v2_response_schema,
)


def call_client_tldr_v2_llm(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    build_prompt_fn: Callable[..., str],
    compact_hints_fn: Callable[[dict[str, Any]], dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    """Call the provider once and return normalized raw output and preview metadata."""
    perceptual_hints = compact_hints_fn(report_base)
    prompt = build_prompt_fn(
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
        perceptual_hints=perceptual_hints,
    )
    raw_payload: Any
    try:
        raw_payload = llm._call_json(
            _client_tldr_v2_system_prompt(lang),
            prompt,
            max_tokens=5000,
            json_schema=client_tldr_v2_response_schema(),
            schema_name="brand3_client_tldr_v2",
            strict_schema=False,
            timeout_seconds=CLIENT_TLDR_V2_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        return None, None, {
            "analysis_error": {
                "reason": "llm_error",
                "detail": f"The client TLDR v2 pass failed: {exc}",
            },
            "raw": {},
            "raw_response_preview": None,
        }

    raw_response_preview = _safe_raw_response_preview(llm)
    raw = _coerce_client_tldr_v2_raw_json(raw_payload)
    if not raw and raw_response_preview:
        raw = _parse_plain_text_client_tldr_v2(raw_response_preview)

    if not raw:
        failure_type = _latest_failure_type(llm)
        failure_reason = _failure_reason(failure_type)
        failure_detail = _failure_detail(failure_reason)
        return None, raw_response_preview, {
            "analysis_error": {
                "reason": failure_reason,
                "detail": failure_detail,
                "error_type": _error_code(failure_type, failure_reason),
            },
            "raw": raw_payload if isinstance(raw_payload, dict) else {},
            "raw_response_preview": raw_response_preview,
        }

    return raw, raw_response_preview, {"raw_response_preview": raw_response_preview, "raw": raw_payload}


def _latest_failure_type(llm: Any) -> str | None:
    failures = getattr(llm, "call_failures", None)
    if isinstance(failures, list) and failures:
        latest = failures[-1]
        if isinstance(latest, dict):
            return latest.get("error_type")
    return None


def _failure_reason(failure_type: str | None) -> str:
    if failure_type == "transport_error":
        return "transport_error"
    if failure_type == "schema_validation_error":
        return "schema_validation_error"
    return "llm_error"


def _failure_detail(reason: str) -> str:
    return {
        "transport_error": (
            "The client TLDR v2 pass hit a transport error before any usable provider payload was returned."
        ),
        "schema_validation_error": (
            "The client TLDR v2 pass returned JSON that did not satisfy the expected schema."
        ),
        "llm_error": "The client TLDR v2 pass did not return usable JSON.",
    }[reason]


def _error_code(failure_type: str | None, reason: str) -> str:
    if failure_type == "transport_error":
        return "transport_error"
    if failure_type == "schema_validation_error":
        return "schema_validation_error"
    return "json_parse_error"
