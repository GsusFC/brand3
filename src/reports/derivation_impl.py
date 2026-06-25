"""Facade for reports derivation implementation."""

from __future__ import annotations

from src.reports import derivation_impl_runtime as _impl

import sys

sys.modules[__name__] = _impl
