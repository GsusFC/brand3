"""Implementation bridge for web collector support."""

import sys

from src.collectors import web_collector_support_runtime as _impl

sys.modules[__name__] = _impl
