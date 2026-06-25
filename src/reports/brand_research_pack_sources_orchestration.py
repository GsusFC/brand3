"""Facade for brand research pack source orchestration."""

from __future__ import annotations

import sys

from src.reports import brand_research_pack_sources_orchestration_impl_runtime_impl as _impl

sys.modules[__name__] = _impl
