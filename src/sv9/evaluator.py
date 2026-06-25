"""Facade for SV9 evaluator logic."""

from __future__ import annotations

from src.sv9 import evaluator_impl_impl as _impl

globals().update({name: getattr(_impl, name) for name in dir(_impl) if not name.startswith("__")})
__all__ = [name for name in globals() if name not in {"_impl", "__all__"}]
