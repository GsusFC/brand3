"""Support helpers for calibration readiness evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.visual_signature.calibration.calibration_models import (
    CalibrationManifest,
    CalibrationRecordsFile,
    CalibrationSummary,
)
from src.visual_signature.calibration.readiness_models import (
    CoverageStats,
    ReadinessScope,
    ReadinessThresholds,
)


def load_bundle(root: Path) -> tuple[CalibrationManifest | None, CalibrationRecordsFile | None, CalibrationSummary | None]:
    manifest = load_model(root / "calibration_manifest.json", CalibrationManifest)
    records_file = load_model(root / "calibration_records.json", CalibrationRecordsFile)
    summary = load_model(root / "calibration_summary.json", CalibrationSummary)
    return manifest, records_file, summary


def load_model(path: Path, model) -> Any | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return model.model_validate(payload)


def load_corpus_manifest(path: str | Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None:
        default_path = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "calibration_corpus" / "corpus_manifest.json"
        if not default_path.exists():
            return None, None
        path = default_path
    corpus_path = Path(path)
    if not corpus_path.exists():
        return None, display_path(corpus_path)
    payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None, display_path(corpus_path)


def category_coverage(
    summary: CalibrationSummary | None,
    records_file: CalibrationRecordsFile | None,
    minimum_required: int,
) -> dict[str, CoverageStats]:
    if summary is not None:
        source = summary.category_breakdown
    elif records_file is not None:
        source = category_counts_from_records(records_file)
    else:
        source = {}
    total = sum(row.get("total_claims", 0) for row in source.values())
    if total <= 0:
        return {}
    coverage: dict[str, CoverageStats] = {}
    for category, row in sorted(source.items()):
        count = int(row.get("total_claims", 0))
        reviewed_count = int(row.get("reviewed_claims", 0))
        coverage[category] = CoverageStats(
            count=count,
            share=round(count / total, 3) if total else 0.0,
            meets_minimum=count >= minimum_required,
            minimum_required=minimum_required,
            reviewed_count=reviewed_count,
        )
    return coverage


def category_counts_from_records(records_file: CalibrationRecordsFile) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for record in records_file.records:
        row = counts.setdefault(record.category, {"total_claims": 0, "reviewed_claims": 0})
        row["total_claims"] += 1
        if record.review_outcome is not None:
            row["reviewed_claims"] += 1
    return counts


def confidence_bucket_coverage(
    records_file: CalibrationRecordsFile | None,
    minimum_required: int,
    standard_buckets: tuple[str, ...],
) -> dict[str, CoverageStats]:
    counts = {bucket: 0 for bucket in standard_buckets}
    reviewed_counts = {bucket: 0 for bucket in standard_buckets}
    if records_file is not None:
        total = len(records_file.records)
        for record in records_file.records:
            bucket = str(record.confidence_bucket or "unknown")
            if bucket not in counts:
                counts[bucket] = 0
                reviewed_counts[bucket] = 0
            counts[bucket] += 1
            if record.review_outcome is not None:
                reviewed_counts[bucket] += 1
    else:
        total = 0
    total = total or sum(counts.values())
    if total <= 0:
        total = 1
    return {
        bucket: CoverageStats(
            count=count,
            share=round(count / total, 3) if total else 0.0,
            meets_minimum=count >= 1,
            minimum_required=minimum_required,
            reviewed_count=reviewed_counts.get(bucket, 0),
        )
        for bucket, count in sorted(counts.items())
    }


def reviewed_claims(records_file: CalibrationRecordsFile | None) -> int:
    if records_file is None:
        return 0
    return sum(1 for record in records_file.records if record.review_outcome is not None)


def readiness_notes(
    validation_errors: list[str],
    corpus_manifest: dict[str, Any] | None,
    category_count: int,
    confidence_bucket_count: int,
    readiness_scope: ReadinessScope,
) -> list[str]:
    notes = [
        "Evidence-only readiness gate.",
        "No scoring, rubric dimensions, production reports, or UI are modified.",
        f"Scope evaluated: {readiness_scope}",
        "Bundle validation must pass before readiness can be positive.",
        f"Observed categories: {category_count}",
        f"Observed confidence buckets: {confidence_bucket_count}",
        f"Validation errors: {len(validation_errors)}",
    ]
    if corpus_manifest is not None:
        corpus_categories = corpus_manifest.get("categories")
        if isinstance(corpus_categories, list):
            notes.append(f"Corpus manifest categories: {len(corpus_categories)}")
        corpus_minimums = corpus_manifest.get("minimums")
        if isinstance(corpus_minimums, dict) and corpus_minimums.get("broader_calibration_interpretable_records") is not None:
            notes.append("Corpus manifest broader calibration target: " f"{corpus_minimums.get('broader_calibration_interpretable_records')}")
    notes.append("Thresholds are conservative and intended to block broader corpus use until sample size and spread improve.")
    return notes


def thresholds_for_scope(scope: ReadinessScope, thresholds: ReadinessThresholds, default_scope: ReadinessScope) -> ReadinessThresholds:
    if scope != default_scope:
        return thresholds
    return thresholds


def display_path(path: Path) -> str:
    project_root = Path(__file__).resolve().parents[3]
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def pct(value: float) -> str:
    return f"{value:.0%}"
