"""Sampling helpers for human review of annotation overlays."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.visual_signature.annotations.review.types import ReviewBatch, ReviewSampleItem


def load_annotated_payloads(annotation_dir: str | Path) -> list[tuple[Path, dict[str, Any]]]:
    root = Path(annotation_dir)
    payloads: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*.json")):
        if path.name in {"manifest.json", "annotation_audit.json"}:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("annotations"), dict):
            payloads.append((path, payload))
    return payloads


def build_review_sample(
    *,
    annotation_dir: str | Path,
    output_size: int = 36,
    high_confidence_count: int = 8,
    low_confidence_count: int = 8,
    disagreement_heavy_count: int = 10,
    category_diverse_count: int = 12,
) -> ReviewBatch:
    payloads = load_annotated_payloads(annotation_dir)
    selected: dict[str, ReviewSampleItem] = {}
    _add_items(
        selected,
        _high_confidence(payloads, high_confidence_count),
        "high_confidence_annotation",
    )
    _add_items(
        selected,
        _low_confidence(payloads, low_confidence_count),
        "low_confidence_annotation",
    )
    _add_items(
        selected,
        _disagreement_heavy(payloads, disagreement_heavy_count),
        "disagreement_heavy_case",
    )
    _add_items(
        selected,
        _category_diverse(payloads, category_diverse_count),
        "category_diverse_sample",
    )
    if len(selected) < output_size:
        _add_items(selected, payloads[: output_size - len(selected)], "filler_deterministic")
    items = list(selected.values())[:output_size]
    return ReviewBatch(
        version="visual-signature-review-batch-1",
        sample_strategy="high_low_disagreement_category_diverse",
        source_dir=str(annotation_dir),
        items=items,
        notes=[
            "Offline human review calibration sample.",
            "Review decisions are evidence-only and do not affect scoring.",
        ],
    )


def _add_items(
    selected: dict[str, ReviewSampleItem],
    rows: list[tuple[Path, dict[str, Any]]],
    reason: str,
) -> None:
    for path, payload in rows:
        item = _sample_item(path, payload)
        existing = selected.get(item.annotation_id)
        if existing:
            if reason not in existing.sampling_reasons:
                existing.sampling_reasons.append(reason)
        else:
            item.sampling_reasons.append(reason)
            selected[item.annotation_id] = item


def _sample_item(path: Path, payload: dict[str, Any]) -> ReviewSampleItem:
    annotations = payload.get("annotations") or {}
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    agreement = vision.get("agreement") if isinstance(vision.get("agreement"), dict) else {}
    targets = annotations.get("targets") if isinstance(annotations.get("targets"), dict) else {}
    return ReviewSampleItem(
        annotation_id=path.stem,
        brand_name=str(payload.get("brand_name") or ""),
        website_url=str(payload.get("website_url") or ""),
        expected_category=_category(payload),
        annotation_path=str(path),
        annotation_status=str(annotations.get("status") or ""),
        annotation_confidence=_confidence(payload),
        disagreement_level=str(agreement.get("agreement_level") or ""),
        disagreement_flags=[str(flag) for flag in agreement.get("disagreement_flags") or []],
        target_labels={
            target: str(value.get("label") or "unknown")
            for target, value in targets.items()
            if isinstance(value, dict)
        },
    )


def _high_confidence(payloads: list[tuple[Path, dict[str, Any]]], limit: int) -> list[tuple[Path, dict[str, Any]]]:
    return sorted(payloads, key=lambda row: (_confidence(row[1]), row[0].name), reverse=True)[:limit]


def _low_confidence(payloads: list[tuple[Path, dict[str, Any]]], limit: int) -> list[tuple[Path, dict[str, Any]]]:
    return sorted(payloads, key=lambda row: (_confidence(row[1]), row[0].name))[:limit]


def _disagreement_heavy(payloads: list[tuple[Path, dict[str, Any]]], limit: int) -> list[tuple[Path, dict[str, Any]]]:
    return sorted(payloads, key=lambda row: (_disagreement_score(row[1]), row[0].name), reverse=True)[:limit]


def _category_diverse(payloads: list[tuple[Path, dict[str, Any]]], limit: int) -> list[tuple[Path, dict[str, Any]]]:
    by_category: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for row in payloads:
        by_category.setdefault(_category(row[1]), []).append(row)
    rows: list[tuple[Path, dict[str, Any]]] = []
    for category in sorted(by_category):
        candidates = sorted(by_category[category], key=lambda row: row[0].name)
        if candidates:
            rows.append(candidates[0])
    return rows[:limit]


def _confidence(payload: dict[str, Any]) -> float:
    annotations = payload.get("annotations") if isinstance(payload.get("annotations"), dict) else {}
    overall = annotations.get("overall_confidence") if isinstance(annotations.get("overall_confidence"), dict) else {}
    try:
        return float(overall.get("score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _disagreement_score(payload: dict[str, Any]) -> float:
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    agreement = vision.get("agreement") if isinstance(vision.get("agreement"), dict) else {}
    flags = agreement.get("disagreement_flags") if isinstance(agreement.get("disagreement_flags"), list) else []
    severity = agreement.get("disagreement_severity_score")
    try:
        severity_score = float(severity)
    except (TypeError, ValueError):
        severity_score = 0.0
    return severity_score + (len(flags) * 0.25)


def _category(payload: dict[str, Any]) -> str:
    calibration = payload.get("calibration") if isinstance(payload.get("calibration"), dict) else {}
    return str(calibration.get("expected_category") or payload.get("category") or "uncategorized")
