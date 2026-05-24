"""Build evidence-only Visual Signature category baselines."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Iterable

from src.visual_signature.baselines.types import (
    CategoryBaseline,
    NumericBaselineStats,
    VisualSignatureMetricRow,
)


NUMERIC_METRICS = (
    "viewport_whitespace",
    "viewport_density_score",
    "composition_stability",
    "palette_complexity",
    "dom_viewport_agreement_score",
    "dom_viewport_disagreement_severity_score",
    "structural_agreement_score",
    "density_agreement_score",
    "composition_agreement_score",
    "palette_agreement_score",
    "cta_density",
    "visible_cta_weight",
    "component_density",
    "typography_complexity",
    "extraction_confidence",
    "vision_confidence",
    "signal_availability",
    "signal_usability",
    "signal_coverage",
)

CATEGORICAL_METRICS = (
    "viewport_whitespace_band",
    "viewport_density",
    "viewport_composition",
    "dom_viewport_agreement_level",
    "dom_viewport_disagreement_severity",
    "interpretation_status",
)


def build_category_baselines(rows: Iterable[VisualSignatureMetricRow]) -> dict[str, CategoryBaseline]:
    grouped: dict[str, list[VisualSignatureMetricRow]] = defaultdict(list)
    for row in rows:
        grouped[row.category].append(row)

    return {
        category: _build_one(category, category_rows)
        for category, category_rows in sorted(grouped.items())
    }


def _build_one(category: str, rows: list[VisualSignatureMetricRow]) -> CategoryBaseline:
    interpretable = [row for row in rows if row.interpretable]
    numeric_stats = {
        metric: _numeric_stats([getattr(row, metric) for row in interpretable])
        for metric in NUMERIC_METRICS
    }
    category_averages = {
        metric: stats.average
        for metric, stats in numeric_stats.items()
    }
    distributions = {
        metric: dict(sorted(Counter(str(getattr(row, metric) or "unknown") for row in rows).items()))
        for metric in CATEGORICAL_METRICS
    }
    coverage = len(interpretable) / len(rows) if rows else 0.0
    metric_fill = _metric_fill(interpretable)
    sample_adequacy = min(1.0, len(interpretable) / 20)
    metric_discriminability = _metric_discriminability(interpretable)
    confidence_score = round(
        (coverage * 0.35)
        + (metric_fill * 0.20)
        + (sample_adequacy * 0.25)
        + (metric_discriminability * 0.20),
        3,
    )
    limitations: list[str] = []
    if len(interpretable) < 3:
        limitations.append("small_interpretable_sample")
    elif len(interpretable) < 20:
        limitations.append("sample_below_deeper_analysis_target")
    if coverage < 0.6:
        limitations.append("many_not_interpretable_payloads")
    if metric_fill < 0.6:
        limitations.append("low_metric_coverage")
    if metric_discriminability < 0.25:
        limitations.append("low_metric_discriminability")

    return CategoryBaseline(
        category=category,
        sample_count=len(rows),
        interpretable_count=len(interpretable),
        not_interpretable_count=len(rows) - len(interpretable),
        category_averages=category_averages,
        numeric_stats=numeric_stats,
        distributions=distributions,
        confidence={
            "score": confidence_score,
            "coverage": round(coverage, 3),
            "metric_fill": metric_fill,
            "sample_adequacy": round(sample_adequacy, 3),
            "metric_discriminability": metric_discriminability,
            "limitations": limitations,
        },
    )


def _numeric_stats(values: list[float | None]) -> NumericBaselineStats:
    numbers = sorted(value for value in values if value is not None)
    if not numbers:
        return NumericBaselineStats(
            average=None,
            median=None,
            q1=None,
            q3=None,
            iqr=None,
            count=0,
        )
    q1 = _percentile(numbers, 0.25)
    q3 = _percentile(numbers, 0.75)
    return NumericBaselineStats(
        average=round(sum(numbers) / len(numbers), 3),
        median=round(float(median(numbers)), 3),
        q1=round(q1, 3),
        q3=round(q3, 3),
        iqr=round(q3 - q1, 3),
        count=len(numbers),
    )


def _percentile(numbers: list[float], percentile: float) -> float:
    if len(numbers) == 1:
        return numbers[0]
    position = (len(numbers) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(numbers) - 1)
    weight = position - lower
    return numbers[lower] * (1 - weight) + numbers[upper] * weight


def _metric_fill(rows: list[VisualSignatureMetricRow]) -> float:
    if not rows:
        return 0.0
    possible = len(rows) * len(NUMERIC_METRICS)
    present = 0
    for row in rows:
        for metric in NUMERIC_METRICS:
            if getattr(row, metric) is not None:
                present += 1
    return round(present / possible, 3) if possible else 0.0


def _metric_discriminability(rows: list[VisualSignatureMetricRow]) -> float:
    if len(rows) < 2:
        return 0.0
    metric_scores: list[float] = []
    for metric in NUMERIC_METRICS:
        values = [getattr(row, metric) for row in rows]
        numbers = [value for value in values if value is not None]
        if len(numbers) < 2:
            continue
        spread = max(numbers) - min(numbers)
        unique_ratio = len({round(value, 3) for value in numbers}) / len(numbers)
        metric_scores.append(min(1.0, (spread * 0.65) + (unique_ratio * 0.35)))
    if not metric_scores:
        return 0.0
    return round(sum(metric_scores) / len(metric_scores), 3)
