"""Facade for narrative orchestration logic."""

from __future__ import annotations

from src.reports import narrative_orchestration as _orchestration
import sys

# Preserve monkeypatch and cache behavior expected by callers by delegating the public
# module object to the implementation module.
sys.modules[__name__] = _orchestration

