"""Compatibility shim for pre-refactor module name."""

from __future__ import annotations

from src.reports import brand_research_pack_sources_orchestration_impl_runtime_impl as _impl
import sys

sys.modules[__name__] = _impl
