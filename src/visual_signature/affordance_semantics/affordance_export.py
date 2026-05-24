"""Export helpers for affordance semantics records."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.affordance_semantics.affordance_models import (
    AFFORDANCE_EXPORT_SCHEMA_VERSION,
    AffordanceClassification,
    AffordanceExport,
    AffordanceEvidence,
)


def build_affordance_export(
    records: list[AffordanceClassification | dict[str, Any]],
    *,
    source: str | None = None,
) -> AffordanceExport:
    normalized = [_normalize_record(record) for record in records]
    return AffordanceExport(
        schema_version=AFFORDANCE_EXPORT_SCHEMA_VERSION,
        record_type="affordance_export",
        created_at=datetime.now(timezone.utc),
        source=source,
        records=normalized,
        status_counts=_status_counts(normalized),
        policy_counts=_policy_counts(normalized),
        category_counts=_category_counts(normalized),
    )


def export_affordance_json(
    path: str | Path,
    records: list[AffordanceClassification | dict[str, Any]],
    *,
    source: str | None = None,
) -> dict[str, Any]:
    export = build_affordance_export(records, source=source)
    payload = export.to_dict()
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _status_counts(records: list[AffordanceClassification]) -> dict[str, int]:
    counts = Counter()
    for record in records:
        counts["annotated"] += 1
        if record.review_required:
            counts["requires_review"] += 1
    return dict(sorted(counts.items()))


def _policy_counts(records: list[AffordanceClassification]) -> dict[str, int]:
    counts = Counter(record.policy for record in records)
    return dict(sorted(counts.items()))


def _category_counts(records: list[AffordanceClassification]) -> dict[str, int]:
    counts = Counter(record.category for record in records)
    return dict(sorted(counts.items()))


def _normalize_record(record: AffordanceClassification | dict[str, Any]) -> AffordanceClassification:
    if isinstance(record, AffordanceClassification):
        return record
    payload = dict(record)
    evidence = payload.get("evidence")
    if isinstance(evidence, dict):
        payload["evidence"] = AffordanceEvidence.from_mapping(evidence)
    return AffordanceClassification(**payload)
