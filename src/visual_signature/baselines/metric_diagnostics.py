"""Calibration diagnostics for Visual Signature baseline metrics.

These diagnostics are evidence-only. They are used to inspect metric quality
and do not affect scoring, rubric dimensions, reports, or UI.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable

from src.visual_signature.baselines.build_category_baseline import NUMERIC_METRICS
from src.visual_signature.baselines.types import VisualSignatureMetricRow


def build_metric_audit(rows: Iterable[VisualSignatureMetricRow]) -> dict[str, Any]:
    row_list = list(rows)
    metric_summaries = {
        metric: _numeric_metric_summary(metric, [_get(row, metric) for row in row_list])
        for metric in NUMERIC_METRICS
    }
    categorical_summaries = {
        metric: _categorical_metric_summary(metric, [_get(row, metric) for row in row_list])
        for metric in (
            "viewport_whitespace_band",
            "viewport_density",
            "viewport_composition",
            "dom_viewport_agreement_level",
            "dom_viewport_disagreement_severity",
        )
    }
    category_sensitivity = _category_sensitivity(row_list)
    ranked = sorted(metric_summaries.values(), key=lambda item: item["diagnostic_score"], reverse=True)
    saturated = [item["metric"] for item in metric_summaries.values() if item["saturation_detected"]]
    noisy = [item["metric"] for item in metric_summaries.values() if item["noise_risk"] in {"medium", "high"}]
    return {
        "version": "visual-signature-metric-audit-1",
        "row_count": len(row_list),
        "metric_summaries": metric_summaries,
        "categorical_summaries": categorical_summaries,
        "strongest_metrics": [item["metric"] for item in ranked[:6]],
        "weakest_metrics": [item["metric"] for item in ranked[-6:]],
        "saturated_metrics": saturated,
        "noisy_metrics": noisy,
        "category_sensitive_metrics": [
            metric for metric, summary in category_sensitivity.items() if summary["category_sensitivity"] >= 0.18
        ],
        "category_insensitive_metrics": [
            metric for metric, summary in category_sensitivity.items() if summary["category_sensitivity"] < 0.08
        ],
        "category_sensitivity": category_sensitivity,
        "notes": [
            "Availability, usability, and discriminability are separated for calibration only.",
            "Saturation detection means the metric is present but currently weak for ranking brands.",
            "No multimodal semantic interpretation is used in this audit.",
        ],
    }


def metric_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Metric Audit",
        "",
        "Calibration diagnostics only. This report does not affect scoring, rubric dimensions, reports, or UI.",
        "",
        f"- Rows: {audit.get('row_count', 0)}",
        f"- Strongest metrics: {', '.join(audit.get('strongest_metrics') or []) or '-'}",
        f"- Weakest metrics: {', '.join(audit.get('weakest_metrics') or []) or '-'}",
        f"- Saturated metrics: {', '.join(audit.get('saturated_metrics') or []) or '-'}",
        f"- Noisy metrics: {', '.join(audit.get('noisy_metrics') or []) or '-'}",
        f"- Category-sensitive metrics: {', '.join(audit.get('category_sensitive_metrics') or []) or '-'}",
        f"- Category-insensitive metrics: {', '.join(audit.get('category_insensitive_metrics') or []) or '-'}",
        "",
        "## Numeric Metrics",
        "",
        "| Metric | Available | Median | P10 | P90 | IQR | Entropy | Saturated | Noise | Diagnostic |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    for metric, summary in sorted((audit.get("metric_summaries") or {}).items()):
        lines.append(
            f"| {metric} | {_pct(summary.get('availability_rate'))} | {_num(summary.get('median'))} | "
            f"{_num(summary.get('p10'))} | {_num(summary.get('p90'))} | {_num(summary.get('iqr'))} | "
            f"{_num(summary.get('entropy'))} | {summary.get('saturation_detected')} | "
            f"{summary.get('noise_risk')} | {_num(summary.get('diagnostic_score'))} |"
        )
    lines.extend(["", "## Categorical Metrics", ""])
    lines.extend(["| Metric | Entropy | Top value | Distribution |", "| --- | ---: | --- | --- |"])
    for metric, summary in sorted((audit.get("categorical_summaries") or {}).items()):
        lines.append(
            f"| {metric} | {_num(summary.get('entropy'))} | {summary.get('top_value') or '-'} | "
            f"{_distribution(summary.get('distribution') or {})} |"
        )
    return "\n".join(lines).rstrip()


def _numeric_metric_summary(metric: str, values: list[Any]) -> dict[str, Any]:
    numbers = sorted(value for value in (_float_or_none(value) for value in values) if value is not None)
    total = len(values)
    availability = len(numbers) / total if total else 0.0
    if not numbers:
        return {
            "metric": metric,
            "availability_rate": 0.0,
            "median": None,
            "p10": None,
            "p90": None,
            "iqr": None,
            "entropy": 0.0,
            "saturation_detected": True,
            "noise_risk": "high",
            "diagnostic_score": 0.0,
        }
    q1 = _percentile(numbers, 0.25)
    q3 = _percentile(numbers, 0.75)
    iqr = q3 - q1
    spread = max(numbers) - min(numbers)
    entropy = _numeric_entropy(numbers)
    saturation = _saturated(numbers, spread, entropy)
    noise_risk = _noise_risk(numbers, iqr, spread, availability)
    diagnostic = (availability * 0.25) + (min(1.0, spread) * 0.30) + (entropy * 0.30) + ((0.0 if saturation else 1.0) * 0.15)
    return {
        "metric": metric,
        "availability_rate": round(availability, 3),
        "min": round(min(numbers), 3),
        "max": round(max(numbers), 3),
        "median": round(_percentile(numbers, 0.5), 3),
        "p10": round(_percentile(numbers, 0.1), 3),
        "p90": round(_percentile(numbers, 0.9), 3),
        "q1": round(q1, 3),
        "q3": round(q3, 3),
        "iqr": round(iqr, 3),
        "entropy": round(entropy, 3),
        "saturation_detected": saturation,
        "noise_risk": noise_risk,
        "diagnostic_score": round(diagnostic, 3),
    }


def _categorical_metric_summary(metric: str, values: list[Any]) -> dict[str, Any]:
    filtered = [str(value or "unknown") for value in values]
    counts = Counter(filtered)
    top_value, top_count = counts.most_common(1)[0] if counts else ("unknown", 0)
    entropy = _categorical_entropy(counts)
    return {
        "metric": metric,
        "distribution": dict(sorted(counts.items())),
        "top_value": top_value,
        "top_share": round(top_count / len(filtered), 3) if filtered else 0.0,
        "entropy": entropy,
    }


def _category_sensitivity(rows: list[VisualSignatureMetricRow]) -> dict[str, Any]:
    grouped: dict[str, list[VisualSignatureMetricRow]] = defaultdict(list)
    for row in rows:
        grouped[row.category].append(row)
    summaries: dict[str, Any] = {}
    for metric in NUMERIC_METRICS:
        category_medians: list[float] = []
        all_values: list[float] = []
        for category_rows in grouped.values():
            values = sorted(
                value
                for value in (_float_or_none(_get(row, metric)) for row in category_rows)
                if value is not None
            )
            if values:
                category_medians.append(_percentile(values, 0.5))
                all_values.extend(values)
        if not all_values or len(category_medians) < 2:
            sensitivity = 0.0
        else:
            sensitivity = (max(category_medians) - min(category_medians)) / max(1.0, max(all_values) - min(all_values), 0.001)
        summaries[metric] = {
            "category_sensitivity": round(min(1.0, sensitivity), 3),
            "category_median_min": round(min(category_medians), 3) if category_medians else None,
            "category_median_max": round(max(category_medians), 3) if category_medians else None,
        }
    return summaries


def _saturated(numbers: list[float], spread: float, entropy: float) -> bool:
    if len(numbers) < 2:
        return True
    dominant_share = Counter(round(value, 2) for value in numbers).most_common(1)[0][1] / len(numbers)
    return spread < 0.08 or entropy < 0.18 or dominant_share >= 0.85


def _noise_risk(numbers: list[float], iqr: float, spread: float, availability: float) -> str:
    if availability < 0.75:
        return "high"
    if spread > 0 and iqr / spread < 0.08:
        return "medium"
    if len({round(value, 3) for value in numbers}) <= 2:
        return "medium"
    return "low"


def _numeric_entropy(numbers: list[float]) -> float:
    if not numbers:
        return 0.0
    bins = Counter(min(9, max(0, int(value * 10))) for value in numbers)
    return _categorical_entropy(bins)


def _categorical_entropy(counts: Counter[Any]) -> float:
    total = sum(counts.values())
    if total <= 0 or len(counts) <= 1:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        ratio = count / total
        entropy -= ratio * math.log(ratio, 2)
    return round(entropy / math.log(len(counts), 2), 3)


def _percentile(numbers: list[float], percentile: float) -> float:
    if len(numbers) == 1:
        return numbers[0]
    position = (len(numbers) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(numbers) - 1)
    weight = position - lower
    return numbers[lower] * (1 - weight) + numbers[upper] * weight


def _get(row: VisualSignatureMetricRow, metric: str) -> Any:
    return getattr(row, metric, None)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _num(value: Any) -> str:
    number = _float_or_none(value)
    return f"{number:.2f}" if number is not None else "-"


def _pct(value: Any) -> str:
    number = _float_or_none(value)
    return f"{number:.0%}" if number is not None else "-"


def _distribution(values: dict[str, int]) -> str:
    return ", ".join(f"{key}:{value}" for key, value in sorted(values.items())) or "-"
