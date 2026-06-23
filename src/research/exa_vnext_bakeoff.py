"""Facade for EXA VNext bakeoff helpers."""

from __future__ import annotations

from src.research import exa_vnext_bakeoff_impl as _impl
import sys

sys.modules[__name__] = _impl
