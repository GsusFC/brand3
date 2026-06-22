"""Compatibility facade for TLDR Brand3 evaluation helpers and report builders."""

from src.reports.tldr_brand3_research_pack_evaluation_impl import *  # noqa: F401,F403
from src.reports.tldr_brand3_research_pack_evaluation_impl import (
    _avg_metric,
    _delta_metric,
    _load_json,
    _render_table,
    _truncate,
)
