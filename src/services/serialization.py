"""Serialization helpers shared by service-layer payload builders."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value
