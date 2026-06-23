"""Web collector implementation façade."""

import sys

from src.collectors import web_collector_support_impl as _impl

sys.modules[__name__] = _impl
