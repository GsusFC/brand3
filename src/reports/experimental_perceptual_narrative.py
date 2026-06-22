"""Facade for experimental perceptual narrative utilities."""

from __future__ import annotations

from src.reports import experimental_perceptual_narrative_impl as _impl
import sys

# Keep monkeypatch and cache behavior identical to the original module by delegating
# the public module object directly to the implementation module.
sys.modules[__name__] = _impl

