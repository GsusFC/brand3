"""Audit-aware TLDR v2 helpers.

This module does not replace the current Analyst TLDR path. It wraps existing
TLDR block payloads with provenance-aware score state so downstream consumers
can distinguish computed, reviewed, blocked, limited-confidence, and fallback
states without mutating legacy artifacts.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def build_audit_aware_tldr_v2(
    *,
    score_provenance: dict[str, Any],
    current_tldr: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provenance = deepcopy(score_provenance or {})
    current = deepcopy(current_tldr or {})

    replay_integrity = provenance.get("replay_integrity") or {}
    replay_status = str(replay_integrity.get("status") or "unverifiable")
    display_score_source = str(provenance.get("display_score_source") or "blocked")
    recommended_display_score = provenance.get("recommended_display_score")
    reviewed_score = provenance.get("reviewed_score")

    score_state = {
        "computed_composite_score": provenance.get("computed_composite_score"),
        "reviewed_composite_score": (
            reviewed_score.get("reviewed_composite_score")
            if isinstance(reviewed_score, dict)
            else None
        ),
        "display_score_source": display_score_source,
        "display_score_status": _display_score_status(replay_status, display_score_source),
        "display_score_blocked": display_score_source == "blocked",
        "limited_confidence": replay_status == "unverifiable",
        "drift_type": replay_integrity.get("drift_type"),
        "score_values_match_persisted_data": replay_integrity.get("score_values_match_persisted_data"),
        "blocked_score": None if display_score_source == "blocked" else recommended_display_score,
        "recommended_display_score": recommended_display_score,
        "score_integrity": replay_status,
        "replay_integrity": replay_integrity,
        "confidence_summary": provenance.get("confidence_summary") or {},
        "fallback_flags": provenance.get("fallback_flags") or {},
        "rules_applied": provenance.get("rules_applied") or [],
        "warnings": provenance.get("warnings") or [],
        "recommended_action": provenance.get("recommended_action"),
        "evidence_refs": provenance.get("evidence_refs") or [],
    }

    return {
        "tldr_generation_mode": "audit_aware_v2",
        "tldr_brand3_v2": current,
        "score_state": score_state,
        "reviewed_score": reviewed_score,
        "score_provenance": provenance,
    }


def _display_score_status(replay_status: str, display_score_source: str) -> str:
    if display_score_source == "blocked":
        return "blocked"
    if replay_status == "unverifiable":
        return "limited_confidence"
    if display_score_source == "reviewed":
        return "reviewed"
    return "computed"
