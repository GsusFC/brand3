"""Facade for web collector implementation."""

import sys

from src.collectors import web_collector_impl as _impl

sys.modules[__name__] = _impl
