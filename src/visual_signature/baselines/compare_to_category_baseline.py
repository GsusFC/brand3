"""Compare Visual Signature rows to evidence-only category baselines."""

from __future__ import annotations

from typing import Iterable

from src.visual_signature.baselines.build_category_baseline import NUMERIC_METRICS
from src.visual_signature.baselines.types import (
    BrandCategoryComparison,
    CategoryBaseline,
    NumericBaselineStats,
    VisualSignatureMetricRow,
)


_LOWER_IS_WEAKER = {
    "dom_viewport_agreement_score",
    "extraction_confidence",
    "vision_confidence",
    "signal_coverage",
}


def compare_records_to_baselines(
    rows: Iterable[VisualSignatureMetricRow],
    baselines: dict[str, CategoryBaseline],
) -> list[BrandCategoryComparison]:
    comparisons: list[BrandCategoryComparison] = []
    for row in rows:
        baseline = baselines.get(row.category)
        comparisons.append(compare_record_to_baseline(row, baseline))
    return comparisons


def compare_record_to_baseline(
    row: VisualSignatureMetricRow,
    baseline: CategoryBaseline | None,
) -> BrandCategoryComparison:
    flags: list[str] = []
    notes: list[str] = []
    if baseline is None:
        return _comparison(
            row,
            flags=["category_baseline_missing"],
            notes=["No category baseline is available for this payload."],
            confidence_score=0.0,
            baseline_coverage=0.0,
        )

    if not row.interpretable:
        flags.append("not_interpretable_excluded_from_baseline")
        notes.append("Payload is not interpretable and was excluded from category averages.")

    if baseline.interpretable_count < 3:
        flags.append("category_sample_small")
        notes.append("Category baseline has fewer than three interpretable payloads.")

    if row.interpretable:
        for metric in NUMERIC_METRICS:
            flag, note = _numeric_outlier(metric, getattr(row, metric), baseline.numeric_stats.get(metric))
            if flag:
                flags.append(flag)
            if note:
                notes.append(note)
        _agreement_notes(row, baseline, flags, notes)

    confidence_score = _comparison_confidence(row, baseline)
    return _comparison(
        row,
        flags=flags,
        notes=notes,
        confidence_score=confidence_score,
        baseline_coverage=float(baseline.confidence.get("coverage") or 0.0),
    )


def _numeric_outlier(
    metric: str,
    value: float | None,
    stats: NumericBaselineStats | None,
) -> tuple[str | None, str | None]:
    if value is None or stats is None or stats.count < 3 or stats.q1 is None or stats.q3 is None or stats.iqr is None:
        return None, None
    if stats.iqr <= 0:
        return None, None
    low = stats.q1 - (1.5 * stats.iqr)
    high = stats.q3 + (1.5 * stats.iqr)
    if value < low:
        return (
            f"{metric}_below_category_range",
            f"{_label(metric)} is below the category range.",
        )
    if value > high:
        return (
            f"{metric}_above_category_range",
            f"{_label(metric)} is above the category range.",
        )
    return None, None


def _agreement_notes(
    row: VisualSignatureMetricRow,
    baseline: CategoryBaseline,
    flags: list[str],
    notes: list[str],
) -> None:
    distribution = baseline.distributions.get("dom_viewport_agreement_level") or {}
    common_level = max(distribution, key=distribution.get) if distribution else "unknown"
    if row.dom_viewport_agreement_level == "low" and common_level in {"high", "medium"}:
        flags.append("dom_viewport_agreement_below_category")
        notes.append("DOM-vs-viewport agreement is weaker than the category norm.")
    if row.viewport_density != "unknown":
        density_distribution = baseline.distributions.get("viewport_density") or {}
        if density_distribution and density_distribution.get(row.viewport_density, 0) == 0:
            flags.append("viewport_density_unusual_for_category")
            notes.append("Viewport density is unusual for this category baseline.")


def _comparison_confidence(row: VisualSignatureMetricRow, baseline: CategoryBaseline) -> float:
    if not row.interpretable:
        return 0.0
    baseline_confidence = float(baseline.confidence.get("score") or 0.0)
    row_confidence_values = [
        value
        for value in (row.extraction_confidence, row.vision_confidence, row.signal_coverage)
        if value is not None
    ]
    row_confidence = sum(row_confidence_values) / len(row_confidence_values) if row_confidence_values else 0.0
    return round((baseline_confidence * 0.55) + (row_confidence * 0.45), 3)


def _comparison(
    row: VisualSignatureMetricRow,
    *,
    flags: list[str],
    notes: list[str],
    confidence_score: float,
    baseline_coverage: float,
) -> BrandCategoryComparison:
    return BrandCategoryComparison(
        category=row.category,
        brand_name=row.brand_name,
        website_url=row.website_url,
        interpretation_status=row.interpretation_status,
        outlier_flags=flags,
        category_relative_notes=notes,
        confidence={
            "score": confidence_score,
            "baseline_coverage": round(baseline_coverage, 3),
            "limitations": row.limitations,
        },
        metrics=row.to_dict(),
    )


def _label(metric: str) -> str:
    return metric.replace("_", " ")
