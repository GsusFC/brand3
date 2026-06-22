"""Heuristics and candidate-building helpers for strategic evidence packets."""

from __future__ import annotations

from src.reports import strategic_evidence_packet_helpers_support as _impl
import sys

sys.modules[__name__] = _impl
