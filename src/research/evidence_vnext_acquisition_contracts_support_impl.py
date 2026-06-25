"""Facade for evidence-vnext acquisition contracts helpers."""

from __future__ import annotations

from src.research import evidence_vnext_acquisition_contracts_support_impl_runtime as _impl

import sys

# Preserve private module behavior and monkeypatch compatibility by delegating module
# namespace to the runtime implementation.
sys.modules[__name__] = _impl
