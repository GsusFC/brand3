"""Facade for report dossier assembly."""

from __future__ import annotations

from src.reports import dossier_impl as _impl
import sys

sys.modules[__name__] = _impl
