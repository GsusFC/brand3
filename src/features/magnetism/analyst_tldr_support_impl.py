"""Facade for Analyst TLDR support implementation."""

from __future__ import annotations

import sys

from src.features.magnetism import analyst_tldr_support_runtime as _impl

sys.modules[__name__] = _impl
