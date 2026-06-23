"""Facade for EvidenceGraph source helpers."""

from __future__ import annotations

from src.research import evidence_graph_sources_impl as _impl

import sys

sys.modules[__name__] = _impl
