"""Compatibility facade for TLDR Brand3 evaluation implementation details."""

from __future__ import annotations

from src.reports import tldr_brand3_research_pack_evaluation_impl_runtime_impl as _impl

import sys

# Preserve private module behavior and monkeypatch compatibility by delegating module
# namespace to the runtime implementation.
sys.modules[__name__] = _impl
