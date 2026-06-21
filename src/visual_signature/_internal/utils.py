"""Shared helpers for Visual Signature modules.

These utilities were previously duplicated across ~25 files. They are
intentionally dependency-free so any submodule can import them without
creating circular dependencies.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def slug(value: str, *, default: str = "capture") -> str:
    """Slugify a string: lowercase, alnum preserved, non-alnum → '-'."""
    out: list[str] = []
    for char in value.lower().strip():
        if char.isalnum():
            out.append(char)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-") or default


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp_01(value: float) -> float:
    """Clamp to [0.0, 1.0] with 3-decimal rounding."""
    return max(0.0, min(1.0, round(value, 3)))


def unique(values: list[str]) -> list[str]:
    """Return non-empty strings, preserving order, deduplicated."""
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def utc_now() -> str:
    """ISO 8601 UTC timestamp with 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def json_default(value: Any) -> str:
    """JSON serializer for non-standard types (datetime → ISO)."""
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return str(value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write pretty JSON with sorted keys, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=json_default) + "\n",
        encoding="utf-8",
    )
