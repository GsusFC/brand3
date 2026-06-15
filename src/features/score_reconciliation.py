"""Shared helpers for reconciling LLM scalar scores with categorical verdicts."""

from __future__ import annotations


def reconcile_label_score(raw_score: float, label: str, mapping: dict[str, float]) -> float:
    """Prefer stable categorical labels when an LLM emits contradictory scores."""
    target = mapping[label]
    if label == "unclear":
        return target
    if raw_score <= 10:
        return target
    if target >= 50 and raw_score < 25:
        return target
    return raw_score
