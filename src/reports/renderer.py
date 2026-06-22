"""Facade for the HTML report renderer."""

from __future__ import annotations

from src.reports import renderer_impl as _impl
import sys

sys.modules[__name__] = _impl
