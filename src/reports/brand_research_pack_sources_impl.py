"""Facade for Brand Research Pack source modeling implementation."""

from __future__ import annotations

from src.reports import brand_research_pack_sources_orchestration as _orchestration
import sys

# Preserve module-level compatibility while centralizing implementation in orchestration.
sys.modules[__name__] = _orchestration
