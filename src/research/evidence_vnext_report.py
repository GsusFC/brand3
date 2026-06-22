"""Facade for Evidence VNext report generation."""

from __future__ import annotations

from src.research import evidence_vnext_report_impl as _impl
from src.research.evidence_vnext_report_rendering import render_batch_report_markdown

_impl.render_batch_report_markdown = render_batch_report_markdown

import sys

sys.modules[__name__] = _impl
