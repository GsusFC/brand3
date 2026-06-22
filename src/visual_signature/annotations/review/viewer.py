"""Local web viewer facade for Visual Signature annotation review."""

from __future__ import annotations

import asyncio

from src.visual_signature.annotations.review import viewer_impl as _viewer_impl

globals().update((k, v) for (k, v) in vars(_viewer_impl).items() if not k.startswith("__"))

__all__ = [name for name in globals() if not name.startswith("__")]
