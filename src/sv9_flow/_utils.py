"""Small shared helpers for SV9 Flow workers."""

from __future__ import annotations

from typing import Any


def feature_confidence(value: Any) -> str:
    candidate = str(value or "").lower()
    if candidate in {"low", "medium", "high"}:
        return candidate
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "medium"
    if numeric >= 0.75:
        return "high"
    if numeric >= 0.4:
        return "medium"
    return "low"


def truthy_detected(payload: dict[str, Any]) -> bool:
    if payload.get("detected") is True:
        return True
    if payload.get("present") is True:
        return True
    if payload.get("detected") is False or payload.get("present") is False:
        return False
    return bool(str(payload.get("content") or payload.get("answer") or "").strip())


def first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
