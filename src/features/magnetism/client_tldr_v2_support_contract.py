"""Facade for client TLDR v2 contract helpers."""

from __future__ import annotations

import sys

from src.features.magnetism import client_tldr_v2_support_contract_impl_runtime_impl as _impl

sys.modules[__name__] = _impl
