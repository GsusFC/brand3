"""Facade for LLM-powered narrative generators."""

from __future__ import annotations

from src.reports import narrative_orchestration as _impl
from src.reports.narrative_support import (
    _build_findings_user_prompt,
    _build_synthesis_user_prompt,
    _build_tensions_user_prompt,
    _date_anchor_clause,
    _default_analyzer,
    _format_evidences_for_prompt,
    _unique_preserve,
    _validate_urls,
    format_perceptual_hints_for_prompt,
)

_impl._build_findings_user_prompt = _build_findings_user_prompt
_impl._build_synthesis_user_prompt = _build_synthesis_user_prompt
_impl._build_tensions_user_prompt = _build_tensions_user_prompt
_impl._date_anchor_clause = _date_anchor_clause
_impl._default_analyzer = _default_analyzer
_impl._format_evidences_for_prompt = _format_evidences_for_prompt
_impl._unique_preserve = _unique_preserve
_impl._validate_urls = _validate_urls
_impl.format_perceptual_hints_for_prompt = format_perceptual_hints_for_prompt

import sys

sys.modules[__name__] = _impl
