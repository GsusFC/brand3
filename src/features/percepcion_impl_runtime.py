"""Facade for percepcion implementation."""

from __future__ import annotations

from src.features import percepcion_impl_runtime_runtime as _impl

import sys

# Preserve private module behavior and monkeypatch compatibility by delegating module
# namespace to the runtime implementation.
sys.modules[__name__] = _impl
