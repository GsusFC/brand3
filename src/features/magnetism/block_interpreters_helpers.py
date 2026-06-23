"""Facade for TLDR block interpreter helpers."""

from __future__ import annotations

from src.features.magnetism import block_interpreters_helpers_impl as _impl

import sys

sys.modules[__name__] = _impl
