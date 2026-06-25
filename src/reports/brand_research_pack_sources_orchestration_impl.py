"""Facade for brand research pack source orchestration."""

from __future__ import annotations

from src.reports import brand_research_pack_sources_orchestration_impl_runtime as _impl

import sys

sys.modules[__name__] = _impl
