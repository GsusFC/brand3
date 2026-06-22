"""Facade for Analyst TLDR support implementation."""

from __future__ import annotations

from src.features.magnetism.analyst_tldr_support_runtime import *  # noqa: F401,F403

# Preserve compatibility with existing import style (including private helpers).
from src.features.magnetism.analyst_tldr_support_runtime import (
    ANALYST_BLOCK_QUESTIONS,
    ANALYST_TLDR_NEGATIVE_EXAMPLES,
    ANALYST_TLDR_PROMPT_VERSION,
    ANALYST_TLDR_SOURCE_RULES,
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
    _system_reading_system_prompt,
    _system_reading_timeout_seconds,
    _unique_texts,
    _normalize_block,
    _compact_current_tldr,
    _compact_evidence_basis,
    _compact_evidence_list,
    _compact_list,
    _compact_research_pack_for_prompt,
    _clean_list,
    _clean_text,
    _compact_source_map,
    _normalize_choice,
    _normalize_evidence_sources,
    _source_index,
    _research_pack_dict,
    _safe_len,
    _to_non_negative_int,
    _truncate_text,
    build_analyst_tldr_prompt,
    build_system_reading_prompt,
    analyst_tldr_response_schema,
    normalize_analyst_response,
    normalize_system_reading,
    system_reading_response_schema,
)
