"""Shared support values for the phase zero catalog."""

from __future__ import annotations

from datetime import datetime, timezone

from src.visual_signature.phase_zero.models import (
    PHASE_ZERO_TAXONOMY_VERSION,
    UNCERTAINTY_PROFILE_SCHEMA_VERSION,
)


def now_timestamp() -> str:
    return datetime(2026, 5, 11, 10, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def uncertainty_profile(
    confidence: float,
    *,
    reasons: list[str] | None = None,
    known_unknowns: list[str] | None = None,
    reviewer_required: bool = False,
    unsupported_inference: bool = False,
) -> dict[str, object]:
    if confidence >= 0.8:
        level = "high"
    elif confidence >= 0.55:
        level = "medium"
    else:
        level = "low"
    return {
        "schema_version": UNCERTAINTY_PROFILE_SCHEMA_VERSION,
        "taxonomy_version": PHASE_ZERO_TAXONOMY_VERSION,
        "record_type": "uncertainty_profile",
        "confidence": confidence,
        "confidence_level": level,
        "known_unknowns": known_unknowns or [],
        "uncertainty_reasons": reasons or [],
        "reviewer_required": reviewer_required,
        "unsupported_inference": unsupported_inference,
    }
