"""Facade for visual signature platform builder."""

from __future__ import annotations

from src.visual_signature.platform import platform_builder_impl as _impl

globals().update({name: getattr(_impl, name) for name in dir(_impl) if not name.startswith("__")})
__all__ = [name for name in globals() if name not in {"_impl", "__all__"}]

