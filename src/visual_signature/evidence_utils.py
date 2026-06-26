"""Shared helpers for Visual Signature evidence contracts."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none
from src.visual_signature._internal.utils import unique as _unique


def component_types(components: dict[str, Any]) -> list[str]:
    rows = components.get("components")
    if not isinstance(rows, list):
        return []
    values = []
    for row in rows:
        if isinstance(row, dict) and row.get("type"):
            values.append(str(row["type"]))
    return _unique(values)


def distinctiveness_proxy(payload: dict[str, Any]) -> float:
    from src.visual_signature._internal.utils import dict_or_empty as _dict

    colors = _dict(payload.get("colors"))
    typography = _dict(payload.get("typography"))
    layout = _dict(payload.get("layout"))
    score = 0.35
    if colors.get("palette_complexity") in {"medium", "high"}:
        score += 0.12
    if string_list(colors.get("accent_candidates")):
        score += 0.1
    if typography.get("heading_scale") in {"expressive", "strong"}:
        score += 0.14
    if string_list(layout.get("layout_patterns")):
        score += 0.08
    return round(min(score, 0.86), 3)


def score01(value: Any) -> float:
    number = _float_or_none(value)
    if number is None:
        return 0.0
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))


def string_list(value: Any) -> list[str]:
    return [str(item) for item in value if item not in (None, "")] if isinstance(value, list) else []


def optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
