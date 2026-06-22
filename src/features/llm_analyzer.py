"""Facade for LLM analyzer implementation.

This keeps the previous public import path (`src.features.llm_analyzer`) while
allowing tests and callers to patch helpers on the facade module. Runtime method
calls are synchronized so patched helpers are used by the actual implementation
logic.
"""

from __future__ import annotations

from typing import Any

from src.features import llm_analyzer_impl as _impl
from src.features.llm_analyzer_impl import (  # noqa: F401
    _run_gemini_http_call,
    _run_llm_http_call,
)
from src.features.llm_analyzer_impl import *  # noqa: F401,F403

__all__ = list(globals().keys())

# Keep references to the original implementation defaults so patched state can be
# reconciled back to baseline deterministically.
def _sync_runtime_overrides() -> None:
    """Propagate facade-level patches into implementation module globals."""

    _impl.BRAND3_DB_PATH = BRAND3_DB_PATH
    _impl._run_llm_http_call = _run_llm_http_call
    _impl._run_gemini_http_call = _run_gemini_http_call


class LLMAnalyzer(_impl.LLMAnalyzer):
    """Compatibility façade for the implementation LLM analyzer."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = "",
        model: str | None = None,
        timeout_seconds: int | None = None,
        use_cache: bool | None = None,
        cache_dir: str | None = None,
        **kwargs: Any,
    ) -> None:
        prompt_version = kwargs.pop("prompt_version", None)
        strict_schema = kwargs.pop("strict_schema", None)
        kwargs.pop("provider", None)
        if kwargs:
            unknown = ", ".join(sorted(kwargs))
            raise TypeError(f"Unexpected arguments: {unknown}")

        _sync_runtime_overrides()
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
        _ = prompt_version
        _ = strict_schema
        if use_cache is not None:
            self.use_cache = bool(use_cache)
        if cache_dir is not None:
            self.cache_dir = cache_dir
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds

    def _call(
        self,
        system: str,
        user: str,
        max_tokens: int = 8000,
    ) -> str:
        _sync_runtime_overrides()
        return super()._call(system, user, max_tokens=max_tokens)

    def _call_json(
        self,
        system: str,
        user: str,
        max_tokens: int = 8000,
        *,
        json_schema: dict[str, Any] | None = None,
        schema_name: str | None = None,
        strict_schema: bool = True,
        timeout_seconds: int | None = None,
    ) -> dict:
        _sync_runtime_overrides()
        return super()._call_json(
            system,
            user,
            max_tokens=max_tokens,
            json_schema=json_schema,
            schema_name=schema_name,
            strict_schema=strict_schema,
            timeout_seconds=timeout_seconds,
        )

    def _call_json_gemini_native(
        self,
        system: str,
        user: str,
        max_tokens: int = 8000,
        *,
        json_schema: dict[str, Any],
        schema_name: str | None = None,
        timeout_seconds: int | None = None,
    ) -> dict:
        _sync_runtime_overrides()
        return super()._call_json_gemini_native(
            system,
            user,
            max_tokens=max_tokens,
            json_schema=json_schema,
            schema_name=schema_name,
            timeout_seconds=timeout_seconds,
        )


def __getattr__(name: str):
    return getattr(_impl, name)
