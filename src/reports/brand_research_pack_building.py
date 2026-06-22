"""Snapshot-to-BrandResearchPack facade."""

from __future__ import annotations

from src.reports import brand_research_pack_building_orchestration as _orchestration
import sys

sys.modules[__name__] = _orchestration
