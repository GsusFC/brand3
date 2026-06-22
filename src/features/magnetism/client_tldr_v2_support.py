"""Facade for client-facing TLDR v2 support helpers."""

from __future__ import annotations

from src.features.magnetism import client_tldr_v2_support_impl as _impl

globals().update({name: getattr(_impl, name) for name in dir(_impl) if not name.startswith("__")})
__all__ = [name for name in globals() if name not in {"_impl", "__all__"}]
