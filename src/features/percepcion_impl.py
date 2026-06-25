"""Facade for Percepción implementation."""

from __future__ import annotations

from src.features import percepcion_impl_runtime as _impl

import sys

sys.modules[__name__] = _impl
