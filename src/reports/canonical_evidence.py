"""Facade for Canonical Evidence implementation."""

from __future__ import annotations

from src.reports import canonical_evidence_impl_impl as _impl

import sys

sys.modules[__name__] = _impl
