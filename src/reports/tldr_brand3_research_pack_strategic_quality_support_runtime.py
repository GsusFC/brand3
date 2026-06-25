"""Compatibility facade for strategic quality support implementation."""

from __future__ import annotations

from src.reports import tldr_brand3_research_pack_strategic_quality_support_runtime_runtime as _impl

import sys

# Preserve private module behavior and monkeypatch compatibility by delegating module
# namespace to the runtime implementation.
sys.modules[__name__] = _impl
