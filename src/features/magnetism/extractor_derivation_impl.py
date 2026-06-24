"""Compatibility facade for derivation mixin implementation."""

from __future__ import annotations

import sys

from src.features.magnetism import extractor_derivation_runtime as _impl

sys.modules[__name__] = _impl

