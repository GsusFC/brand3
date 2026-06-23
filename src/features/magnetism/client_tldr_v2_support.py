"""Facade for client-facing TLDR v2 support helpers."""

from __future__ import annotations

from src.features.magnetism import client_tldr_v2_support_impl as _impl

import sys

sys.modules[__name__] = _impl
