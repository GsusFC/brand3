"""Facade for Exa collector runtime support."""

from __future__ import annotations

from src.collectors import exa_collector_support_runtime_impl as _impl

import sys

sys.modules[__name__] = _impl
