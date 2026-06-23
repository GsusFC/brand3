"""Facade for Exa collector implementation."""

import sys

from src.collectors import exa_collector_support_impl as _impl

sys.modules[__name__] = _impl
