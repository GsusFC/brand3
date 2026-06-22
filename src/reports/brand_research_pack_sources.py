"""Research pack source modeling and extraction facade."""

from __future__ import annotations

from src.reports import brand_research_pack_sources_orchestration as _orchestration
import sys

sys.modules[__name__] = _orchestration
