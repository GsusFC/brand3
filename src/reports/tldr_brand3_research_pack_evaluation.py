"""Facade for TLDR Brand3 evaluation report generation."""

from __future__ import annotations

from src.reports import tldr_brand3_research_pack_evaluation_runtime as _impl

import sys

# Preserve private module behavior and ensure stable imports for monkeypatching.
sys.modules[__name__] = _impl
