"""Facade for reports derivation runtime implementation."""

from __future__ import annotations

from src.reports import derivation_impl_runtime_impl as _impl

import sys

sys.modules[__name__] = _impl
