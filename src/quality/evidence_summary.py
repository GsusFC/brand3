"""Evidence summary helpers.

These helpers count support material for transparency only. They do not affect
brand scores or confidence formulas.
"""

from __future__ import annotations

import ast
import json
from typing import Any

from src.dimensions import DIMENSIONS

_EVIDENCE_KEYS = ("evidence", "quotes", "examples", "messaging_gaps", "tone_examples")


def summarize_evidence_from_features(
    features_by_dim: dict[str, dict[str, Any]],
    *,
    evidence_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for dimension_name, features in (features_by_dim or {}).items():
        for feature_name, feature in (features or {}).items():
            records.append({
                "dimension_name": dimension_name,
                "feature_name": feature_name,
                "raw_value": getattr(feature, "raw_value", None),
                "source": getattr(feature, "source", ""),
            })
    return summarize_evidence_records(records, evidence_items=evidence_items)


def summarize_evidence_records(
    feature_records: list[dict[str, Any]],
    *,
    evidence_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    by_dimension = {dimension_name: 0 for dimension_name in DIMENSIONS}
    by_source: dict[str, int] = {}
    by_quality = {"direct": 0, "indirect": 0, "weak": 0}

    total = 0
    for record in feature_records or []:
        dimension_name = record.get("dimension_name")
        if dimension_name not in by_dimension:
            continue
        count, quality_counts = _feature_evidence_counts(record.get("raw_value"))
        if count <= 0:
            continue
        by_dimension[dimension_name] += count
        source = record.get("source") or "unknown"
        by_source[source] = by_source.get(source, 0) + count
        for quality, quality_count in quality_counts.items():
            by_quality[quality] += quality_count
        total += count

    for item in evidence_items or []:
        dimension_name = item.get("dimension_name")
        if dimension_name not in by_dimension:
            continue
        if not (item.get("quote") or item.get("url")):
            continue
        by_dimension[dimension_name] += 1
        source = item.get("source") or "unknown"
        by_source[source] = by_source.get(source, 0) + 1
        by_quality[_evidence_item_quality(item)] += 1
        total += 1

    return {
        "total": total,
        "by_dimension": by_dimension,
        "by_source": dict(sorted(by_source.items())),
        "by_quality": {key: value for key, value in by_quality.items() if value > 0},
        "dimensions_without_evidence": [
            dimension_name
            for dimension_name, count in by_dimension.items()
            if count == 0
        ],
    }


def _feature_evidence_count(raw_value: Any) -> int:
    count, _ = _feature_evidence_counts(raw_value)
    return count


def _feature_evidence_counts(raw_value: Any) -> tuple[int, dict[str, int]]:
    raw = _parse_raw(raw_value)
    if not isinstance(raw, dict):
        return 0, {"direct": 0, "indirect": 0, "weak": 0}

    count = 0
    by_quality = {"direct": 0, "indirect": 0, "weak": 0}
    for key in _EVIDENCE_KEYS:
        items = raw.get(key)
        if isinstance(items, list):
            for item in items:
                if not _item_has_evidence(item):
                    continue
                count += 1
                by_quality[_raw_item_quality(item)] += 1

    if raw.get("evidence_url"):
        count += 1
        by_quality["direct"] += 1
    if raw.get("evidence_snippet"):
        count += 1
        by_quality["weak"] += 1

    snippets = raw.get("evidence_snippets")
    if isinstance(snippets, list):
        snippet_count = sum(1 for item in snippets if isinstance(item, str) and item.strip())
        count += snippet_count
        by_quality["weak"] += snippet_count

    insights = raw.get("evidence_insights")
    if isinstance(insights, list):
        insight_count = sum(1 for item in insights if isinstance(item, str) and item.strip())
        count += insight_count
        by_quality["indirect"] += insight_count

    return count, by_quality


def _item_has_evidence(item: Any) -> bool:
    if isinstance(item, str):
        return bool(item.strip())
    if not isinstance(item, dict):
        return False
    return bool(
        item.get("quote")
        or item.get("example")
        or item.get("text")
        or item.get("snippet")
        or item.get("source_url")
        or item.get("url")
    )


def _raw_item_quality(item: Any) -> str:
    if isinstance(item, str):
        return "weak"
    if not isinstance(item, dict):
        return "weak"
    if item.get("source_url") or item.get("url"):
        return "direct"
    if item.get("quote") or item.get("text") or item.get("snippet"):
        return "indirect"
    return "weak"


def _evidence_item_quality(item: dict[str, Any]) -> str:
    if item.get("url"):
        return "direct"
    if item.get("quote"):
        return "indirect"
    return "weak"


def _parse_raw(raw_value: Any) -> Any:
    if isinstance(raw_value, (dict, list)):
        return raw_value
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    try:
        return json.loads(raw_value)
    except Exception:
        pass
    try:
        return ast.literal_eval(raw_value)
    except Exception:
        return raw_value
