"""Projection queue, contract, and triage helpers for evidence vNext reports (facade)."""

from __future__ import annotations

from src.research import evidence_vnext_report_projection_queue_impl_runtime_impl as _impl

import sys

# Preserve private module behavior and monkeypatch compatibility by delegating module
# namespace to the runtime implementation.
sys.modules[__name__] = _impl
