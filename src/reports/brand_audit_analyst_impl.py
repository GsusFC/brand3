"""Facade for Brand Audit Analyst implementation."""

from __future__ import annotations

from src.reports import brand_audit_analyst_orchestration as _orchestration
import sys

# Preserve monkeypatch and private-test behavior by exposing the implementation
# module object directly as this public module.
sys.modules[__name__] = _orchestration

