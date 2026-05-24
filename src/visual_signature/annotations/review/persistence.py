"""Persistence helpers for offline annotation review records."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.visual_signature.annotations.review.types import (
    ReviewBatch,
    ReviewRecord,
    ReviewSampleItem,
    TargetReviewDecision,
)


def save_review_batch(path: str | Path, batch: ReviewBatch) -> None:
    _write_json(Path(path), batch.to_dict())


def load_review_batch(path: str | Path) -> ReviewBatch:
    payload = _load_json(Path(path))
    return ReviewBatch(
        version=str(payload.get("version") or "visual-signature-review-batch-1"),
        sample_strategy=str(payload.get("sample_strategy") or "unknown"),
        source_dir=str(payload.get("source_dir") or ""),
        notes=[str(item) for item in payload.get("notes") or []],
        items=[
            ReviewSampleItem(
                annotation_id=str(item.get("annotation_id") or ""),
                brand_name=str(item.get("brand_name") or ""),
                website_url=str(item.get("website_url") or ""),
                expected_category=str(item.get("expected_category") or ""),
                annotation_path=str(item.get("annotation_path") or ""),
                sampling_reasons=[str(reason) for reason in item.get("sampling_reasons") or []],
                annotation_status=str(item.get("annotation_status") or ""),
                annotation_confidence=_float_or_none(item.get("annotation_confidence")),
                disagreement_level=str(item.get("disagreement_level") or ""),
                disagreement_flags=[str(flag) for flag in item.get("disagreement_flags") or []],
                target_labels={str(key): str(value) for key, value in (item.get("target_labels") or {}).items()},
            )
            for item in payload.get("items") or []
            if isinstance(item, dict)
        ],
    )


def save_review_records(path: str | Path, records: list[ReviewRecord]) -> None:
    payload = {
        "version": "visual-signature-review-records-1",
        "generated_at": datetime.now().isoformat(),
        "records": [record.to_dict() for record in records],
    }
    _write_json(Path(path), payload)


def load_review_records(path: str | Path) -> list[ReviewRecord]:
    payload = _load_json(Path(path))
    rows = payload.get("records") if isinstance(payload.get("records"), list) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a review record list or records object")
    return [_record_from_dict(row) for row in rows if isinstance(row, dict)]


def validate_review_record(record: ReviewRecord) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not record.reviewer_id:
        errors.append("reviewer_id_missing")
    if not record.annotation_id:
        errors.append("annotation_id_missing")
    if not record.target_reviews:
        errors.append("target_reviews_missing")
    for target, review in record.target_reviews.items():
        if review.decision not in {"agree", "disagree", "uncertain", "not_applicable"}:
            errors.append(f"{target}:decision_invalid")
        if review.usefulness < 1 or review.usefulness > 5:
            errors.append(f"{target}:usefulness_out_of_range")
        if review.uncertainty not in {"none", "low", "medium", "high"}:
            errors.append(f"{target}:uncertainty_invalid")
        if review.hallucination and review.decision == "agree":
            warnings.append(f"{target}:hallucination_marked_on_agree")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def _record_from_dict(row: dict[str, Any]) -> ReviewRecord:
    reviews: dict[str, TargetReviewDecision] = {}
    for target, payload in (row.get("target_reviews") or {}).items():
        if not isinstance(payload, dict):
            continue
        reviews[str(target)] = TargetReviewDecision(
            target=str(payload.get("target") or target),
            decision=str(payload.get("decision") or "uncertain"),  # type: ignore[arg-type]
            usefulness=int(payload.get("usefulness") or 1),
            hallucination=bool(payload.get("hallucination")),
            uncertainty=str(payload.get("uncertainty") or "none"),  # type: ignore[arg-type]
            corrected_label=str(payload.get("corrected_label")) if payload.get("corrected_label") else None,
            notes=str(payload.get("notes") or ""),
        )
    return ReviewRecord(
        reviewer_id=str(row.get("reviewer_id") or ""),
        annotation_id=str(row.get("annotation_id") or ""),
        brand_name=str(row.get("brand_name") or ""),
        website_url=str(row.get("website_url") or ""),
        expected_category=str(row.get("expected_category") or ""),
        annotation_path=str(row.get("annotation_path") or ""),
        target_reviews=reviews,
        overall_usefulness=int(row["overall_usefulness"]) if row.get("overall_usefulness") is not None else None,
        overall_notes=str(row.get("overall_notes") or ""),
        reviewed_at=str(row.get("reviewed_at") or "") or None,
    )


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
