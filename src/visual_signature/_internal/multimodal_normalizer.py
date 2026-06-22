"""Helpers for normalizing multimodal vision model output."""

from __future__ import annotations

from typing import Any


def normalize_semantics_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw model fields into the Visual Signature contract."""

    visual_polish = payload.get("visual_polish")
    score = payload.get("visual_polish_score")
    rationale = payload.get("visual_polish_rationale")
    if isinstance(visual_polish, dict):
        score = visual_polish.get("score", score)
        rationale = visual_polish.get("reasoning") or visual_polish.get("rationale") or rationale

    return {
        "aesthetic_style": _non_empty_text(payload.get("aesthetic_style")),
        "visual_mood": _non_empty_text(payload.get("visual_mood")),
        "visual_polish_score": _score_or_none(score),
        "visual_polish_rationale": str(rationale or "").strip(),
        "visual_coherence": _non_empty_text(payload.get("visual_coherence")),
    }


def _non_empty_text(value: Any) -> str:
    text = str(value or "").strip()
    return text or "not_detected"


def _score_or_none(value: Any) -> int | None:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    return max(1, min(10, score))
