"""Facade for brand service runtime logic."""

from __future__ import annotations

from src.services import brand_service_impl as _impl
import sys

# Preserve private monkeypatch/rebinding behavior by delegating the public module
# object to the implementation module.
sys.modules[__name__] = _impl

