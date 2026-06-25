"""Facade for Presencia extractor implementation."""

from __future__ import annotations

from src.features import presencia_impl_runtime as _impl

import sys

sys.modules[__name__] = _impl
