"""JSON payload helpers for SQLite persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def safe_json_loads(value: Any, *, field: str, fallback: Any) -> tuple[Any, dict[str, Any] | None]:
    if value is None:
        return fallback, None
    try:
        return json.loads(value), None
    except (TypeError, json.JSONDecodeError) as exc:
        return fallback, {
            "field": field,
            "raw_json": value,
            "error": str(exc),
        }


def to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


class MalformedJSONPayload:
    def __init__(self, *, field: str, raw_json: str, error: str):
        self.field = field
        self.raw_json = raw_json
        self.error = error
