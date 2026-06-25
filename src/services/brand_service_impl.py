"""Facade for brand service implementation."""

from __future__ import annotations

from src.services import brand_service_impl_runtime as _impl

import sys

# Preserve private monkeypatch/rebinding behavior by delegating module namespace.
sys.modules[__name__] = _impl
