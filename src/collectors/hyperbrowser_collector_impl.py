"""Facade for Hyperbrowser collector implementation."""

from __future__ import annotations

import sys

from src.collectors import hyperbrowser_collector_runtime as _impl

sys.modules[__name__] = _impl
