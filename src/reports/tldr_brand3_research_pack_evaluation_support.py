"""Compatibility facade for TLDR Brand3 evaluation helpers and report builders."""

from __future__ import annotations

from src.reports import tldr_brand3_research_pack_evaluation_impl as _impl

import sys

sys.modules[__name__] = _impl
