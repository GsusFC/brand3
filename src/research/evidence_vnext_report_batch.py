"""Facade for evidence vNext batch report building."""

from __future__ import annotations

from src.research import evidence_vnext_report_batch_impl as _impl
import sys

sys.modules[__name__] = _impl
