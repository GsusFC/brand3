"""Facade for screenshot runtime helpers."""

from __future__ import annotations

import sys

from src.services import screenshot_runtime_impl as _impl

sys.modules[__name__] = _impl
