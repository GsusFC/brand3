"""Facade for Hyperbrowser collector runtime implementation."""

from __future__ import annotations

import sys

from src.collectors import hyperbrowser_collector_runtime_impl_impl as _impl

sys.modules[__name__] = _impl
