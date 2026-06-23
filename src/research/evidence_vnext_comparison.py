"""Facade for evidence vNext comparison helpers."""

from __future__ import annotations

from src.research import evidence_vnext_comparison_impl as _impl

import sys

sys.modules[__name__] = _impl
