"""Facade for visual analyzer implementation."""

from __future__ import annotations

from src.features import visual_analyzer_impl as _impl

import sys

sys.modules[__name__] = _impl
