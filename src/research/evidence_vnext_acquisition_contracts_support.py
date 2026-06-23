"""Facade for evidence-vnext acquisition contracts helpers."""

from __future__ import annotations

from src.research import evidence_vnext_acquisition_contracts_support_impl as _impl

import sys

sys.modules[__name__] = _impl
