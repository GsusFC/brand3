"""Compatibility facade for derivation readiness implementation."""

from __future__ import annotations

from src.reports import derivation_readiness_impl_impl as _impl

import sys

sys.modules[__name__] = _impl
