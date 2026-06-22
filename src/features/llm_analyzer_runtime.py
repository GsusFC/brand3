"""Runtime primitives for LLM analyzer orchestration internals."""

from __future__ import annotations

import os
from typing import Any

from src.config import LLM_BASE_URL, LLM_MODEL
from src.features import llm_analyzer_support as _llm_support

PROMPT_VERSION = _llm_support.PROMPT_VERSION
LLM_CALL_TIMEOUT_SECONDS = _llm_support.LLM_CALL_TIMEOUT_SECONDS


def _safe_excerpt(value: str | None, max_chars: int = 500) -> str:
    text = "" if value is None else str(value)
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1]}…"


def _current_impl_module():
    from src.features import llm_analyzer_impl

    return llm_analyzer_impl


def llm_failure_reason(llm, default: str) -> str:
    reason = getattr(llm, "last_failure_reason", None)
    if reason in {
        "llm_timeout",
        "llm_error",
        "transport_error",
        "schema_validation_error",
        "provider_http_error",
    }:
        return reason
    return default


class _LLMAnalyzerRuntime:
    """Low-level LLM analyzer methods split out from the monolithic implementation."""

    @staticmethod
    def _resolve_api_key(api_key: str | None) -> str:
        if api_key:
            return api_key
        return (
            os.environ.get("BRAND3_LLM_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY", "")
        )

    @staticmethod
    def _resolve_base_url(base_url: str | None) -> str:
        if base_url:
            return base_url
        return os.environ.get("BRAND3_LLM_BASE_URL", LLM_BASE_URL)

    @staticmethod
    def _resolve_model(model: str | None) -> str:
        if model:
            return model
        return os.environ.get("BRAND3_LLM_MODEL", LLM_MODEL)

    def _record_failure(
        self,
        reason: str,
        error: str,
        *,
        error_type: str | None = None,
        response_empty: bool = False,
        json_parse_error: bool = False,
    ) -> None:
        self.last_failure_reason = reason
        provider_payload = _llm_support._provider_error_payload(error)
        self.call_failures.append(
            {
                "reason": reason,
                "error": error[:200],
                "error_type": error_type or _llm_support._llm_error_type(reason, error),
                "http_status": provider_payload["http_status"],
                "provider_error_code": provider_payload["provider_error_code"],
                "provider_error_message": provider_payload["provider_error_message"],
                "response_empty": bool(response_empty),
                "json_parse_error": bool(json_parse_error),
                "model": self.model,
                "base_url": self.base_url,
            }
        )

    def _clear_failure(self) -> None:
        self.last_failure_reason = None

    def _cache_key(
        self,
        response_type: str,
        system: str,
        user: str,
        max_tokens: int,
        *,
        schema_name: str | None = None,
    ) -> str:
        payload = {
            "prompt_version": PROMPT_VERSION,
            "model": self.model,
            "response_type": response_type,
            "schema_name": schema_name or "",
            "system": system,
            "user": user,
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        return _llm_support._llm_cache_digest(payload)

    def _cache_get(self, cache_key: str, response_type: str):
        if not self.use_cache:
            return None
        try:
            from src.storage.sqlite_store import SQLiteStore

            store = SQLiteStore(_current_impl_module().BRAND3_DB_PATH)
            try:
                cached = store.get_llm_cache(cache_key)
            finally:
                store.close()
        except Exception:
            return None
        if not cached or cached.get("response_type") != response_type:
            return None
        self.cache_hits += 1
        if response_type == "json":
            return cached.get("response_json") or {}
        return cached.get("response_text") or ""

    def _cache_save(self, cache_key: str, response_type: str, value) -> None:
        if not self.use_cache:
            return
        if value in ("", None, {}):
            return
        try:
            from src.storage.sqlite_store import SQLiteStore

            store = SQLiteStore(_current_impl_module().BRAND3_DB_PATH)
            try:
                store.save_llm_cache(
                    cache_key=cache_key,
                    prompt_version=PROMPT_VERSION,
                    model=self.model,
                    response_type=response_type,
                    response_json=value if response_type == "json" else None,
                    response_text=value if response_type == "text" else None,
                )
            finally:
                store.close()
            self.cache_writes += 1
        except Exception:
            return
