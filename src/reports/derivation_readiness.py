"""Facade for derivation readiness helpers."""

from __future__ import annotations

from src.reports import derivation_readiness_impl as _impl

# Preserve the previous public contract, including private helper names that are
# imported directly from this module in sibling report helpers.
globals().update({name: getattr(_impl, name) for name in dir(_impl) if not name.startswith("__")})
__all__ = [name for name in globals() if name not in {"_impl", "__all__"}]
