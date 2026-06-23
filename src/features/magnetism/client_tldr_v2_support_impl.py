"""Client-facing TLDR v2 helpers.

This module builds an experimental client-safe TLDR preview from the existing
TLDR blocks plus score provenance and report context. It does not mutate the
legacy TLDR artifact and it does not change scoring.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.client_tldr_v2_support_contract import (
    CLIENT_TLDR_V2_PROMPT_VERSION,
    CLIENT_TLDR_V2_TIMEOUT_SECONDS,
    _compact_perceptual_hints_for_prompt,
    build_client_tldr_v2_prompt as _build_client_tldr_v2_prompt,
)
from src.features.magnetism.client_tldr_v2_support_runtime import (
    _client_tldr_v2_model,
    _default_analyzer,
    _ensure_client_tldr_runtime_env_loaded,
    _log_client_tldr_v2_runtime_context,
    run_client_tldr_v2_pass as _runtime_run_client_tldr_v2_pass,
)
from src.features.magnetism.client_tldr_v2_support_normalization import (
    _client_score_provenance,
    _normalize_tldr_blocks,
    normalize_client_tldr_v2_response,
)
from src.features.magnetism.client_tldr_v2_support_normalization_system import (
    _fallback_payload,
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
    perceptual_payload = (
        _compact_perceptual_hints_for_prompt(report_base)
        if perceptual_hints is None
        else perceptual_hints
    )
    return _build_client_tldr_v2_prompt(
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        perceptual_hints=perceptual_payload,
        lang=lang,
    )


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
    """Build an experimental client-safe TLDR v2 payload."""
    _ensure_client_tldr_runtime_env_loaded()
    language = "en" if lang == "en" else "es"
    provenance = _client_score_provenance(
        score_provenance or {},
        scanner_display_score=scanner_display_score,
    )
    base = deepcopy(report_base or {})
    current_blocks = _normalize_tldr_blocks(current_tldr)

    llm = analyzer or _default_analyzer()
    _log_client_tldr_v2_runtime_context(llm)
    if llm is not None and getattr(llm, "api_key", None):
        result = run_client_tldr_v2_pass(
            llm=llm,
            brand_name=brand_name,
            url=url,
            current_tldr=current_blocks,
            score_provenance=provenance,
            report_base=base,
            lang=language,
        )
        if result.get("analysis_error"):
            fallback = _fallback_payload(
                brand_name=brand_name,
                url=url,
                current_tldr=current_blocks,
                score_provenance=provenance,
                report_base=base,
                lang=language,
            )
            fallback["analysis_error"] = result["analysis_error"]
            if result.get("raw_response_preview"):
                fallback["analysis_error"]["raw_response_preview"] = result["raw_response_preview"]
            return fallback
        validated = result.get("validated") if isinstance(result.get("validated"), dict) else {}
        if validated:
            return validated

    return _fallback_payload(
        brand_name=brand_name,
        url=url,
        current_tldr=current_blocks,
        score_provenance=provenance,
        report_base=base,
        lang=language,
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
    """Call the LLM once and normalize the client TLDR v2 response."""
    return _runtime_run_client_tldr_v2_pass(
        llm=llm,
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
        build_prompt_fn=build_client_tldr_v2_prompt,
        compact_hints_fn=_compact_perceptual_hints_for_prompt,
        normalize_response_fn=normalize_client_tldr_v2_response,
    )
