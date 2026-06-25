"""Facade for llm_analyzer implementation."""

from __future__ import annotations

from src.features import llm_analyzer_impl_runtime as _impl

import sys

sys.modules[__name__] = _impl
