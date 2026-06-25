"""Facade for magnetism client implementation.

This module preserves the legacy patching surface from the pre-``*_impl``
layout. Tests and runtime code still patch private helpers on
``src.features.magnetism.client_tldr_v2``; we forward those through to the
implementation module before each call.
"""

from __future__ import annotations

from typing import Any

from src.features.magnetism import client_tldr_v2_support as _support

from src.features.magnetism.client_tldr_v2_support import (  # noqa: F401
    CLIENT_TLDR_V2_PROMPT_VERSION,
    CLIENT_TLDR_V2_TIMEOUT_SECONDS,
    _client_tldr_v2_model as _impl_client_tldr_v2_model,
    _compact_perceptual_hints_for_prompt as _impl_compact_perceptual_hints_for_prompt,
    _ensure_client_tldr_runtime_env_loaded as _impl_ensure_client_tldr_runtime_env_loaded,
    build_client_tldr_v2 as _impl_build_client_tldr_v2,
    _default_analyzer as _impl_default_analyzer,
)

LLMAnalyzer = _support.LLMAnalyzer
_client_tldr_v2_model = _impl_client_tldr_v2_model
_compact_perceptual_hints_for_prompt = _impl_compact_perceptual_hints_for_prompt
_ensure_client_tldr_runtime_env_loaded = _impl_ensure_client_tldr_runtime_env_loaded
_default_analyzer = _impl_default_analyzer


def _sync_client_tldr_runtime_overrides() -> None:
    """Keep implementation internals aligned with patched facade helpers."""

    _support._client_tldr_v2_model = _client_tldr_v2_model
    _support._compact_perceptual_hints_for_prompt = _compact_perceptual_hints_for_prompt
    _support._ensure_client_tldr_runtime_env_loaded = _ensure_client_tldr_runtime_env_loaded
    _support.LLMAnalyzer = LLMAnalyzer
    _support._default_analyzer = _default_analyzer


def _default_analyzer() -> Any | None:
    _sync_client_tldr_runtime_overrides()
    try:
        analyzer = LLMAnalyzer(model=_client_tldr_v2_model())
        return analyzer if getattr(analyzer, "api_key", None) else None
    except Exception:
        return None


def build_client_tldr_v2(
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any] | None,
    score_provenance: dict[str, Any] | None = None,
    report_base: dict[str, Any] | None = None,
    lang: str = "es",
    analyzer: Any | None = None,
    scanner_display_score: Any | None = None,
) -> dict[str, Any]:
    _sync_client_tldr_runtime_overrides()
    return _impl_build_client_tldr_v2(
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
        analyzer=analyzer,
        scanner_display_score=scanner_display_score,
    )


def run_client_tldr_v2_pass(
    *,
    llm: Any,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
) -> dict[str, Any]:
    _sync_client_tldr_runtime_overrides()
    return _support.run_client_tldr_v2_pass(
        llm=llm,
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
    )


def build_client_tldr_v2_prompt(
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    perceptual_hints: dict[str, Any] | None = None,
    lang: str,
) -> str:
    _sync_client_tldr_runtime_overrides()
    return _support.build_client_tldr_v2_prompt(
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        perceptual_hints=perceptual_hints,
        lang=lang,
    )


def client_tldr_v2_response_schema() -> dict[str, Any]:
    _sync_client_tldr_runtime_overrides()
    return _support.client_tldr_v2_response_schema()


def normalize_client_tldr_v2_response(
    raw: dict[str, Any],
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    perceptual_guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _sync_client_tldr_runtime_overrides()
    return _support.normalize_client_tldr_v2_response(
        raw,
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
        perceptual_guidance=perceptual_guidance,
    )


def __getattr__(name: str):
    return getattr(_support, name)
