"""Implementation façade for client TLDR v2.

The heavy LLM orchestration and prompt/normalization logic now lives in
``client_tldr_v2_support``. This module preserves the legacy patching
surface and routes calls through the support module while keeping behavior
compatible with existing callers.
"""

from __future__ import annotations

from typing import Any

from src.features.magnetism import client_tldr_v2_support as _support

# Re-export public constants through this module so existing imports continue.
CLIENT_TLDR_V2_PROMPT_VERSION = _support.CLIENT_TLDR_V2_PROMPT_VERSION
CLIENT_TLDR_V2_TIMEOUT_SECONDS = _support.CLIENT_TLDR_V2_TIMEOUT_SECONDS

# Re-export runtime hook points used by tests and sync patching.
_client_tldr_v2_model = _support._client_tldr_v2_model
_compact_perceptual_hints_for_prompt = _support._compact_perceptual_hints_for_prompt
_ensure_client_tldr_runtime_env_loaded = _support._ensure_client_tldr_runtime_env_loaded
_default_analyzer = _support._default_analyzer
LLMAnalyzer = _support.LLMAnalyzer


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
    return _support.build_client_tldr_v2(
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


def __getattr__(name: str) -> Any:
    return getattr(_support, name)
