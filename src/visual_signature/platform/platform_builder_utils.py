"""Utility helpers for Visual Signature platform payload assembly."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .platform_builder_constants import PROJECT_ROOT


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else {"items": payload}


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _to_output_relative_path(path: str | Path, *, output_root: str | Path) -> str:
    output_root = Path(output_root)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return os.path.relpath(candidate.resolve(), output_root)


def _safe_get(payload: dict[str, Any] | None, key: str) -> Any:
    return payload.get(key) if isinstance(payload, dict) else None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part) or "unknown"


def _filesystem_summary(path: Path, *, artifact_type: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.is_dir():
        return {
            "artifact_type": artifact_type,
            "file_count": sum(1 for child in path.rglob("*") if child.is_file()),
        }
    return {
        "artifact_type": artifact_type,
        "size_bytes": path.stat().st_size,
    }


def _artifact_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    keys = (
        "schema_version",
        "record_type",
        "generated_at",
        "checked_at",
        "completed_at",
        "status",
        "readiness_status",
        "validation_status",
        "record_count",
        "total",
        "ok",
        "error",
        "capability_count",
        "policy_count",
        "pilot_status",
        "current_capture_count",
        "reviewed_capture_count",
        "target_capture_count",
    )
    return {key: payload[key] for key in keys if key in payload}
