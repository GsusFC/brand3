"""Facade for Hyperbrowser collector implementation."""

import sys

from src.collectors import hyperbrowser_collector_runtime_impl as _impl

sys.modules[__name__] = _impl
