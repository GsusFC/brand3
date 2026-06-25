"""Evidence packet readiness support helpers facade."""

from __future__ import annotations

from src.reports import evidence_packet_readiness_support_impl_runtime as _impl

import sys

# Preserve private module behavior and monkeypatch compatibility by delegating module
# namespace to the runtime implementation.
sys.modules[__name__] = _impl
