"""Input loaders for visual signature calibration joins."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.visual_signature.phase_zero.models import ReviewRecord


@dataclass(slots=True)
class PhaseOneCaptureSource:
    capture_id: str
    brand_name: str
    website_url: str
    state_record: dict[str, Any] | None
    eligibility_record: dict[str, Any] | None
    transition_records: list[dict[str, Any]]
    mutation_audit_record: dict[str, Any] | None
    record_paths: list[str]


def load_phase_one_capture_sources(phase_one_root: str | Path) -> list[PhaseOneCaptureSource]:
    root = Path(phase_one_root) / "records"
    if not root.exists():
        return []
    sources: list[PhaseOneCaptureSource] = []
    for brand_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        state_record = load_json(brand_dir / "state.json")
        eligibility_record = load_json(brand_dir / "dataset_eligibility.json")
        mutation_audit_record = load_json(brand_dir / "mutation_audit.json")
        transition_records = []
        for transition_path in sorted(brand_dir.glob("transition_*.json")):
            transition_record = load_json(transition_path)
            if isinstance(transition_record, dict):
                transition_records.append(transition_record)
        brand_name = str((state_record or eligibility_record or {}).get("brand_name") or brand_dir.name.replace("-", " ").title())
        website_url = str((state_record or eligibility_record or {}).get("website_url") or "")
        record_paths = [str(path) for path in sorted(brand_dir.glob("*.json"))]
        sources.append(
            PhaseOneCaptureSource(
                capture_id=brand_dir.name,
                brand_name=brand_name,
                website_url=website_url,
                state_record=state_record if isinstance(state_record, dict) else None,
                eligibility_record=eligibility_record if isinstance(eligibility_record, dict) else None,
                transition_records=transition_records,
                mutation_audit_record=mutation_audit_record if isinstance(mutation_audit_record, dict) else None,
                record_paths=record_paths,
            )
        )
    return sources


def load_phase_two_review_index(phase_two_root: str | Path) -> dict[str, ReviewRecord]:
    path = Path(phase_two_root) / "reviews" / "review_records.json"
    payload = load_json(path)
    rows = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    reviews: dict[str, ReviewRecord] = {}
    for row in rows:
        if isinstance(row, dict):
            review = ReviewRecord.model_validate(row)
            reviews[review.capture_id] = review
    return reviews


def load_brand_category_map(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    payload = load_json(Path(path))
    rows = payload.get("brands") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    mapping: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        category = str(row.get("expected_category") or "uncategorized")
        brand_name = str(row.get("brand_name") or "").strip()
        website_url = str(row.get("website_url") or "").strip()
        if brand_name:
            mapping[brand_name.lower()] = category
        if website_url:
            mapping[website_url.lower()] = category
    return mapping


def load_capture_manifest_index(path: str | Path | None) -> dict[str, dict[str, Any]]:
    return _load_row_index(path)


def load_dismissal_audit_index(path: str | Path | None) -> dict[str, dict[str, Any]]:
    return _load_row_index(path)


def _load_row_index(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    payload = load_json(Path(path))
    rows = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict):
            key = str(row.get("capture_id") or row.get("brand_name") or "").lower()
            if key:
                index[key] = row
                brand_key = str(row.get("brand_name") or "").lower()
                if brand_key:
                    index[brand_key] = row
    return index


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
