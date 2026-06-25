"""Facade for diferenciacion implementation."""

from __future__ import annotations

from src.features import diferenciacion_impl_runtime_impl as _impl

import sys

sys.modules[__name__] = _impl
