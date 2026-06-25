"""Facade for client TLDR v2 contract helper implementation."""

from __future__ import annotations

from src.features.magnetism import client_tldr_v2_support_contract_impl_runtime as _impl

import sys

sys.modules[__name__] = _impl
