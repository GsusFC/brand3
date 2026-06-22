"""Offline Evidence Packet v0 builder.

This module is a thin facade over ``src.reports.evidence_packet_support`` so the
public import path stays stable.
"""

from __future__ import annotations

from src.reports import evidence_packet_support as _impl
import sys

sys.modules[__name__] = _impl
