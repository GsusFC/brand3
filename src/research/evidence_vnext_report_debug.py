"""Debug print helpers for evidence vNext reports."""

from __future__ import annotations

from typing import Any


def print_changed_fields(comparison: dict[str, Any]) -> None:
    for field in comparison.get("fields") or []:
        if not field.get("changed"):
            continue
        name = field.get("field")
        if name not in {"offer", "audience", "outcome", "proof_points", "founder_or_press_context", "noise_rejected"}:
            continue
        print(f"  {name}:")
        print(f"    current: {field.get('legacy_preview') or '-'}")
        print(f"    vnext  : {field.get('graph_preview') or '-'}")


def print_gate_reasons(gate: dict[str, Any]) -> None:
    review = _top_counts(gate.get("review_reason_counts") or {})
    rejected = _top_counts(gate.get("rejected_reason_counts") or {})
    if review:
        print("  review reasons:", ", ".join(f"{key}={value}" for key, value in review))
    if rejected:
        print("  rejected reasons:", ", ".join(f"{key}={value}" for key, value in rejected))


def _top_counts(counts: dict[str, Any], limit: int = 3) -> list[tuple[str, int]]:
    return sorted(((str(key), int(value or 0)) for key, value in counts.items()), key=lambda item: (-item[1], item[0]))[:limit]
