"""Section renderers for Evidence vNext batch reports."""

from __future__ import annotations

from typing import Any


def _summary_lines(report: dict[str, Any]) -> list[str]:
    totals = report.get("totals") or {}
    recommendation = report.get("recommendation") or {}
    return [
        "# Evidence vNext Batch Report",
        "",
        "## Summary",
        "",
        f"- Runs: `{totals.get('run_count', 0)}`",
        f"- Status: `{recommendation.get('status', 'unknown')}`",
        f"- Accepted: `{totals.get('accepted', 0)}`",
        f"- Review required: `{totals.get('review_required', 0)}`",
        f"- Rejected: `{totals.get('rejected', 0)}`",
        f"- Reclassified to noise: `{totals.get('reclassified_to_noise', 0)}`",
        f"- Material lost fields: `{totals.get('material_lost_fields', 0)}`",
        "",
    ]


def _acquisition_matrix_lines(report: dict[str, Any]) -> list[str]:
    acquisition = report.get("acquisition_matrix") or {}
    provider_rows = acquisition.get("provider_rows") or []
    lines = ["## Acquisition Matrix", ""]
    if provider_rows:
        lines.extend(["| Provider | Accepted | Review | Rejected | Top reasons |", "| --- | ---: | ---: | ---: | --- |"])
        for row in provider_rows:
            reasons = ", ".join(f"{key}={value}" for key, value in (row.get("reason_counts") or {}).items())
            lines.append(
                "| {provider} | {accepted} | {review} | {rejected} | {reasons} |".format(
                    provider=row.get("provider") or "unknown_provider",
                    accepted=row.get("accepted") or 0,
                    review=row.get("review_required") or 0,
                    rejected=row.get("rejected") or 0,
                    reasons=reasons or "-",
                )
            )
    else:
        lines.append("- None")
    return lines


def _semantic_evidence_lines(report: dict[str, Any]) -> list[str]:
    semantic = report.get("semantic_evidence") or {}
    lines = ["", "## Semantic Evidence Shadow", ""]
    lines.append(f"- Classifier: `{semantic.get('classifier') or 'none'}`")
    lines.append(f"- Accepted material: `{semantic.get('accepted_material', 0)}`")
    lines.append(f"- Accepted weak: `{semantic.get('accepted_weak', 0)}`")
    class_counts = semantic.get("semantic_class_counts") or {}
    if class_counts:
        lines.extend(["", "| Semantic class | Count |", "| --- | ---: |"])
        for key, value in class_counts.items():
            lines.append(f"| {key} | {value} |")
    weak_examples = semantic.get("weak_examples") or []
    if weak_examples:
        lines.extend(["", "Weak accepted examples:"])
        for item in weak_examples[:10]:
            lines.append(
                "- run `{run_id}` `{brand_name}` · `{semantic_class}` `{url}`: {text_preview}".format(
                    run_id=item.get("run_id"),
                    brand_name=item.get("brand_name") or "",
                    semantic_class=item.get("semantic_class") or "",
                    url=item.get("url") or "-",
                    text_preview=item.get("text_preview") or "-",
                )
            )
    return lines


def _semantic_llm_lines(report: dict[str, Any]) -> list[str]:
    semantic_llm = report.get("semantic_llm") or {}
    lines = ["", "## Semantic LLM Shadow", ""]
    lines.append(f"- Status counts: `{semantic_llm.get('status_counts') or {}}`")
    lines.append(f"- Models: `{semantic_llm.get('models') or {}}`")
    lines.append(
        f"- Semantic class disagreements: `{semantic_llm.get('semantic_class_disagreement_count', 0)}`"
    )
    lines.append(
        f"- Materiality disagreements: `{semantic_llm.get('materiality_disagreement_count', 0)}`"
    )
    for item in (semantic_llm.get("rows") or [])[:10]:
        lines.append(
            "- run `{run_id}` `{brand_name}` · status `{status}` · model `{model}` · class_delta `{class_delta}` · materiality_delta `{materiality_delta}`".format(
                run_id=item.get("run_id"),
                brand_name=item.get("brand_name") or "",
                status=item.get("status") or "",
                model=item.get("model") or "",
                class_delta=item.get("semantic_class_disagreement_count") or 0,
                materiality_delta=item.get("materiality_disagreement_count") or 0,
            )
        )
    return lines


def _recommendation_lines(report: dict[str, Any]) -> list[str]:
    recommendation = report.get("recommendation") or {}
    lines = ["", "## Recommendation", ""]
    for reason in recommendation.get("reason_codes") or []:
        lines.append(f"- `{reason}`")
    return lines
