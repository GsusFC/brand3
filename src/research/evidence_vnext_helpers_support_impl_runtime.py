"""Compatibility shim for pre-refactor module name."""

from __future__ import annotations

from src.research import evidence_vnext_helpers_support_impl_runtime_impl as _impl
import sys

sys.modules[__name__] = _impl
