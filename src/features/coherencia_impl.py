"""Facade for coherencia implementation."""

from __future__ import annotations

from src.features import coherencia_impl_runtime_runtime as _impl

import sys

sys.modules[__name__] = _impl
