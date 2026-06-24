"""Implementation bridge for Exa collector support."""

import sys

from src.collectors import exa_collector_support_runtime as _impl

sys.modules[__name__] = _impl
