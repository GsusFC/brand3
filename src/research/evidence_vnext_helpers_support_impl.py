"""Private helper functions for evidence vNext filtering and comparison (implementation facade)."""

from __future__ import annotations

from src.research import evidence_vnext_helpers_support_impl_runtime as _impl

import sys

# Preserve private module behavior and monkeypatch compatibility by delegating module
# namespace to the runtime implementation.
sys.modules[__name__] = _impl
