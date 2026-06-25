"""Facade for Analyst TDLR support helpers."""

from __future__ import annotations

from src.features.magnetism import analyst_tldr_support_runtime as _impl

import sys

sys.modules[__name__] = _impl
