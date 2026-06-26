"""Data loading and persistence helpers for the Visual Signature review viewer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none


def _safe_path_under_root(path_value: str | Path, root: Path) -> Path | None:
    candidate = Path(path_value)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def _screenshot_root(sample_path: str | Path) -> Path:
    return Path(sample_path).resolve().parent


@dataclass(frozen=True)
class ReviewViewerCase:
    annotation_id: str
    index: int
    total: int
    brand_name: str
    website_url: str
    expected_category: str
    sampling_reasons: list[str]
    annotation_path: str
    screenshot_path: str | None
    annotation_status: str
    annotation_confidence: float | None
    targets: dict[str, dict[str, Any]]


def load_review_cases(sample_path: str | Path) -> list[ReviewViewerCase]:
    sample = _load_json(Path(sample_path))
    items = sample.get("items")
    if not isinstance(items, list):
        raise ValueError("review_sample.json must contain an items list")
    cases: list[ReviewViewerCase] = []
    total = len(items)
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        annotation_root = Path(sample_path).resolve().parent
        annotation_path = _safe_path_under_root(str(item.get("annotation_path") or ""), annotation_root)
        if annotation_path is None:
            continue
        payload = _load_json(annotation_path)
        annotations = payload.get("annotations") if isinstance(payload.get("annotations"), dict) else {}
        targets = annotations.get("targets") if isinstance(annotations.get("targets"), dict) else {}
        screenshot_path = _screenshot_path(payload)
        cases.append(
            ReviewViewerCase(
                annotation_id=str(item.get("annotation_id") or annotation_path.stem),
                index=index,
                total=total,
                brand_name=str(item.get("brand_name") or payload.get("brand_name") or ""),
                website_url=str(item.get("website_url") or payload.get("website_url") or ""),
                expected_category=str(item.get("expected_category") or _expected_category(payload) or ""),
                sampling_reasons=[str(reason) for reason in item.get("sampling_reasons") or []],
                annotation_path=str(annotation_path),
                screenshot_path=screenshot_path,
                annotation_status=str(annotations.get("status") or item.get("annotation_status") or ""),
                annotation_confidence=_float_or_none(
                    (annotations.get("overall_confidence") or {}).get("score")
                    if isinstance(annotations.get("overall_confidence"), dict)
                    else item.get("annotation_confidence")
                ),
                targets={str(key): dict(value) for key, value in targets.items() if isinstance(value, dict)},
            )
        )
    return cases


def load_viewer_review_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    payload = _load_json(source)
    rows = payload.get("viewer_records") or payload.get("records") or []
    return [dict(row) for row in rows if isinstance(row, dict)]


def latest_review_for_case(path: str | Path, annotation_id: str) -> dict[str, Any] | None:
    matches = [record for record in load_viewer_review_records(path) if record.get("annotation_id") == annotation_id]
    return matches[-1] if matches else None


def build_viewer_review_record(
    case: ReviewViewerCase,
    *,
    reviewer_id: str,
    visually_supported: str,
    useful: str,
    hallucination_or_overreach: str,
    most_reliable_target: str,
    most_confusing_target: str,
    adds_value_beyond_heuristics: str,
    reviewer_notes: str,
) -> dict[str, Any]:
    _validate_choice(visually_supported, {"yes", "partial", "no"}, "visually_supported")
    _validate_choice(useful, {"useful", "neutral", "not_useful"}, "useful")
    _validate_choice(hallucination_or_overreach, {"no", "yes"}, "hallucination_or_overreach")
    _validate_choice(adds_value_beyond_heuristics, {"yes", "no", "unsure"}, "adds_value_beyond_heuristics")
    return {
        "schema_version": "visual-signature-viewer-review-record-1",
        "reviewer_id": reviewer_id.strip() or "local_reviewer",
        "annotation_id": case.annotation_id,
        "brand_name": case.brand_name,
        "website_url": case.website_url,
        "expected_category": case.expected_category,
        "annotation_path": case.annotation_path,
        "screenshot_path": case.screenshot_path,
        "reviewed_at": datetime.now().isoformat(),
        "visually_supported": visually_supported,
        "useful": useful,
        "hallucination_or_overreach": hallucination_or_overreach,
        "most_reliable_target": most_reliable_target,
        "most_confusing_target": most_confusing_target,
        "adds_value_beyond_heuristics": adds_value_beyond_heuristics,
        "reviewer_notes": reviewer_notes.strip(),
    }


def append_viewer_review_record(path: str | Path, record: dict[str, Any]) -> None:
    destination = Path(path)
    rows = load_viewer_review_records(destination)
    rows.append(record)
    payload = {
        "schema_version": "visual-signature-viewer-review-records-1",
        "updated_at": datetime.now().isoformat(),
        "viewer_records": rows,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _case_by_id(cases: list[ReviewViewerCase], annotation_id: str) -> ReviewViewerCase | None:
    return next((case for case in cases if case.annotation_id == annotation_id), None)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _screenshot_path(payload: dict[str, Any]) -> str | None:
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision.get("screenshot"), dict) else {}
    path = screenshot.get("path")
    return str(path) if path else None


def _expected_category(payload: dict[str, Any]) -> str | None:
    calibration = payload.get("calibration") if isinstance(payload.get("calibration"), dict) else {}
    value = calibration.get("expected_category") or payload.get("category")
    return str(value) if value else None


def _validate_choice(value: str, allowed: set[str], field: str) -> None:
    if value not in allowed:
        raise ValueError(f"{field} must be one of {sorted(allowed)}")


__all__ = [
    "ReviewViewerCase",
    "_case_by_id",
    "_safe_path_under_root",
    "_screenshot_root",
    "append_viewer_review_record",
    "build_viewer_review_record",
    "latest_review_for_case",
    "load_review_cases",
    "load_viewer_review_records",
]
