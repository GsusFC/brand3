"""Markdown summaries for Visual Signature category baselines."""

from __future__ import annotations

from src.visual_signature.baselines.types import BrandCategoryComparison, CategoryBaseline


def category_baselines_markdown(baselines: dict[str, CategoryBaseline]) -> str:
    lines = [
        "# Visual Signature Category Baselines",
        "",
        "Evidence-only category baselines. These summaries do not affect scoring, rubric dimensions, reports, or UI.",
        "",
        "| Category | Samples | Interpretable | Coverage | Confidence | Avg whitespace | Avg palette | Avg components | Agreement |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for category, baseline in sorted(baselines.items()):
        agreement = baseline.distributions.get("dom_viewport_agreement_level") or {}
        lines.append(
            f"| {category} | {baseline.sample_count} | {baseline.interpretable_count} | "
            f"{_pct(baseline.confidence.get('coverage'))} | {_num(baseline.confidence.get('score'))} | "
            f"{_num(baseline.category_averages.get('viewport_whitespace'))} | "
            f"{_num(baseline.category_averages.get('palette_complexity'))} | "
            f"{_num(baseline.category_averages.get('component_density'))} | "
            f"{_distribution(agreement)} |"
        )
    lines.extend(["", "## Category Details", ""])
    for category, baseline in sorted(baselines.items()):
        lines.extend(
            [
                f"### {category}",
                "",
                f"- Not interpretable: {baseline.not_interpretable_count}",
                f"- Confidence limitations: {', '.join(baseline.confidence.get('limitations') or []) or '-'}",
                f"- Viewport density: {_distribution(baseline.distributions.get('viewport_density') or {})}",
                f"- Viewport composition: {_distribution(baseline.distributions.get('viewport_composition') or {})}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def brand_comparisons_markdown(comparisons: list[BrandCategoryComparison]) -> str:
    lines = [
        "# Visual Signature Category Comparisons",
        "",
        "Evidence-only brand comparisons against category baselines. These comparisons are calibration aids only.",
        "",
        "| Brand | Category | Interpretation | Confidence | Flags | Notes |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for comparison in comparisons:
        lines.append(
            f"| {comparison.brand_name} | {comparison.category} | {comparison.interpretation_status} | "
            f"{_num(comparison.confidence.get('score'))} | "
            f"{', '.join(comparison.outlier_flags) or '-'} | "
            f"{' '.join(comparison.category_relative_notes) or '-'} |"
        )
    return "\n".join(lines).rstrip()


def _distribution(values: dict[str, int]) -> str:
    if not values:
        return "-"
    return ", ".join(f"{key}:{value}" for key, value in sorted(values.items()))


def _num(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "-"


def _pct(value) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "-"
