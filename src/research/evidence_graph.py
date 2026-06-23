"""Facade for evidence graph implementation."""

from __future__ import annotations

from src.research import evidence_graph_impl as _impl

import sys

sys.modules[__name__] = _impl
