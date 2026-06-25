"""Facade for derivation runtime implementation."""

from __future__ import annotations

from src.features.magnetism import extractor_derivation_runtime_impl_runtime_impl as _impl

import sys

sys.modules[__name__] = _impl
