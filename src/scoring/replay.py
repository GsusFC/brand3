"""Facade for scoring replay implementation."""

import sys

from src.scoring import replay_impl as _impl

sys.modules[__name__] = _impl
