"""Shared analysis exceptions."""

from __future__ import annotations


class AnalysisJobCancelled(Exception):
    """Raised when a background analysis job is cancelled."""
