"""Facade for magnetism client implementation.

This module preserves the legacy patching surface from the pre-``*_impl``
layout. Tests and runtime code still patch private helpers on
``src.features.magnetism.client_tldr_v2``; we forward those through to the
implementation module before each call.
"""

from __future__ import annotations

from typing import Any

from src.features.magnetism import client_tldr_v2_impl as _impl
from src.features.magnetism import client_tldr_v2_support as _support
from src.features.magnetism import client_tldr_v2_support_impl as _support_impl
from src.features.magnetism.client_tldr_v2_impl import (  # noqa: F401
    CLIENT_TLDR_V2_PROMPT_VERSION,
    CLIENT_TLDR_V2_TIMEOUT_SECONDS,
    _client_tldr_v2_model as _impl_client_tldr_v2_model,
    _compact_perceptual_hints_for_prompt as _impl_compact_perceptual_hints_for_prompt,
    _ensure_client_tldr_runtime_env_loaded as _impl_ensure_client_tldr_runtime_env_loaded,
    build_client_tldr_v2 as _impl_build_client_tldr_v2,
    _default_analyzer as _impl_default_analyzer,
)


LLMAnalyzer = _impl.LLMAnalyzer
_client_tldr_v2_model = _impl_client_tldr_v2_model
_compact_perceptual_hints_for_prompt = _impl_compact_perceptual_hints_for_prompt
_ensure_client_tldr_runtime_env_loaded = _impl_ensure_client_tldr_runtime_env_loaded
_default_analyzer = _impl_default_analyzer


def _sync_client_tldr_runtime_overrides() -> None:
    """Keep implementation internals aligned with patched facade helpers."""

    _impl._client_tldr_v2_model = _client_tldr_v2_model
    _impl._compact_perceptual_hints_for_prompt = _compact_perceptual_hints_for_prompt
    _impl._ensure_client_tldr_runtime_env_loaded = _ensure_client_tldr_runtime_env_loaded
    _impl.LLMAnalyzer = LLMAnalyzer
    _impl._default_analyzer = _default_analyzer
    _support._client_tldr_v2_model = _client_tldr_v2_model
    _support._compact_perceptual_hints_for_prompt = _compact_perceptual_hints_for_prompt
    _support._ensure_client_tldr_runtime_env_loaded = _ensure_client_tldr_runtime_env_loaded
    _support.LLMAnalyzer = LLMAnalyzer
    _support._default_analyzer = _default_analyzer
    _support_impl._client_tldr_v2_model = _client_tldr_v2_model
    _support_impl._compact_perceptual_hints_for_prompt = _compact_perceptual_hints_for_prompt
    _support_impl._ensure_client_tldr_runtime_env_loaded = _ensure_client_tldr_runtime_env_loaded
    _support_impl.LLMAnalyzer = LLMAnalyzer
    _support_impl._default_analyzer = _default_analyzer


def _default_analyzer() -> Any | None:
    _sync_client_tldr_runtime_overrides()
    try:
        analyzer = LLMAnalyzer(model=_client_tldr_v2_model())
        return analyzer if getattr(analyzer, "api_key", None) else None
    except Exception:
        return None


def build_client_tldr_v2(*args, **kwargs):
    _sync_client_tldr_runtime_overrides()
    return _impl_build_client_tldr_v2(*args, **kwargs)


def build_client_tldr_v2_prompt(*args, **kwargs):
    _sync_client_tldr_runtime_overrides()
    return _impl.build_client_tldr_v2_prompt(*args, **kwargs)


def __getattr__(name: str):
    return getattr(_impl, name)
