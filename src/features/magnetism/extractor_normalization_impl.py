"""Facade for extractor normalization implementation."""

from __future__ import annotations

from src.features.magnetism import extractor_normalization_impl_runtime_impl as _impl

import sys

sys.modules[__name__] = _impl
