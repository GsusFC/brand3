"""Load Phase One eligibility records and Phase Two human reviews."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.visual_signature.phase_zero.models import ReviewRecord


def load_phase_one_eligibility_records(phase_one_root: str | Path) -> list[dict[str, Any]]:
    phase_one_root = Path(phase_one_root)
    records_root = phase_one_root / "records"
    records: list[dict[str, Any]] = []
    if not records_root.exists():
        return records
    for path in sorted(records_root.glob("*/dataset_eligibility.json")):
        payload = _load_json(path)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def load_review_records(path: str | Path) -> list[ReviewRecord]:
    payload = _load_json(Path(path))
    rows = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    records: list[ReviewRecord] = []
    for row in rows:
        if isinstance(row, dict):
            records.append(ReviewRecord.model_validate(row))
    return records


def index_review_records(records: list[ReviewRecord]) -> dict[str, ReviewRecord]:
    return {record.capture_id: record for record in records}


def _load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
