"""Facade for magnetism extractor derivation runtime."""

from __future__ import annotations

import sys

from src.features.magnetism import extractor_derivation_runtime_impl_runtime_impl as _impl

sys.modules[__name__] = _impl
