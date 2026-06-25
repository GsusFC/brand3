"""Facade for Exa collector runtime support."""

from __future__ import annotations

import sys

from src.collectors import exa_collector_support_runtime_impl as _impl

sys.modules[__name__] = _impl
