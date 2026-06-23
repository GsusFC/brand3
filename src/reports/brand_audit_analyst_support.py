"""Private helpers for brand_audit_analyst."""

from __future__ import annotations

import json
from dataclasses import is_dataclass
from typing import Any


AUDIT_DIMENSIONS = [
    "coherencia",
    "diferenciacion",
    "presencia",
    "percepcion",
    "vitalidad",
]


def _score_fallback_diagnosis(key: str, score: Any) -> str:
    if isinstance(score, (int, float)):
        return f"{key} has a stored score of {score:.0f}/100, but no executive analyst reading is available."
    return f"{key} has no executive analyst reading available."


def _coerce_raw_json(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], dict):
        return raw[0]
    return {}


def _compact_features(features_by_dim: dict[str, dict[str, Any]]) -> dict[str, Any]:
    compact: dict[str, Any] = {}

    for dimension in AUDIT_DIMENSIONS:
        features = features_by_dim.get(dimension) or {}
        compact[dimension] = {
            str(name): {
                "value": payload.get("value") if isinstance(payload, dict) else None,
                "confidence": payload.get("confidence") if isinstance(payload, dict) else None,
                "source": payload.get("source") if isinstance(payload, dict) else None,
                "raw_value": _truncate(payload.get("raw_value"), 900) if isinstance(payload, dict) else None,
            }
            for name, payload in list(features.items())[:12]
        }
    return compact


def _compact_research_pack(pack: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "version",
        "entity",
        "entity_resolution",
        "product_summary",
        "promotable_signals",
        "evidence_context",
        "source_map",
        "confidence_notes",
    )
    compact = {key: pack.get(key) for key in keys if key in pack}
    if isinstance(compact.get("promotable_signals"), list):
        compact["promotable_signals"] = compact["promotable_signals"][:24]
    if isinstance(compact.get("evidence_context"), list):
        compact["evidence_context"] = compact["evidence_context"][:24]
    if isinstance(compact.get("source_map"), dict):
        compact["source_map"] = dict(list(compact["source_map"].items())[:24])
    return compact


def _research_pack_dict(research_pack: Any) -> dict[str, Any]:
    if research_pack is None:
        return {}
    if isinstance(research_pack, dict):
        return research_pack
    if is_dataclass(research_pack):
        return research_pack.to_dict()
    if hasattr(research_pack, "to_dict") and callable(research_pack.to_dict):
        payload = research_pack.to_dict()
        return payload if isinstance(payload, dict) else {}
    return {}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    return _unique_texts(_clean_text(item) for item in value)


def _unique_texts(values: Any) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _normalize_choice(value: Any, allowed: set[str], *, fallback: str) -> str:
    text = _clean_text(value).lower()
    return text if text in allowed else fallback


def _truncate(value: Any, limit: int) -> str:
    text = _clean_text(value)
    return text[:limit]
