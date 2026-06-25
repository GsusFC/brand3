"""Compatibility facade for strategic quality support implementation."""

from __future__ import annotations

import sys

from src.reports import tldr_brand3_research_pack_strategic_quality_support_runtime as _impl

sys.modules[__name__] = _impl
