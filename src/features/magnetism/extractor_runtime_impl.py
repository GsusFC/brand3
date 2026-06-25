"""Facade for Magnetism extractor runtime implementation."""

from __future__ import annotations

from src.features.magnetism import extractor_runtime_impl_runtime as _impl

import sys

sys.modules[__name__] = _impl
