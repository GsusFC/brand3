"""Markdown rendering for calibration readiness results."""

from __future__ import annotations

from src.visual_signature.calibration.calibration_readiness_support import pct as _pct
from src.visual_signature.calibration.readiness_models import ReadinessResult


def calibration_readiness_markdown(result: ReadinessResult) -> str:
    lines = [
        "# Visual Signature Calibration Readiness",
        "",
        "Evidence-only readiness gate for broader calibration corpus use.",
        "",
        "- Evidence-only: yes",
        "- No scoring impact: yes",
        "- No rubric impact: yes",
        "- No production UI/report impact: yes",
        "- Missing review is insufficient_review: yes",
        "- Unclear review is unresolved: yes",
        "",
        "## Bundle Metadata",
        "",
        f"- Calibration run ID: `{result.calibration_run_id}`",
        f"- Checked at: {result.checked_at.isoformat()}",
        f"- Scope evaluated: `{result.readiness_scope}`",
        f"- Status: `{result.status}`",
        f"- Bundle valid: {str(result.bundle_valid).lower()}",
        f"- Summary count consistency: {str(result.summary_count_consistency).lower()}",
        f"- Record count: {result.record_count}",
        f"- Reviewed claims: {result.reviewed_claims}",
        f"- Source corpus manifest: `{result.source_corpus_manifest_path or 'missing'}`",
        "",
        "### Thresholds Used",
        "",
        f"- Minimum total claims: {result.minimum_thresholds_used.minimum_total_claims}",
        f"- Minimum reviewed claims: {result.minimum_thresholds_used.minimum_reviewed_claims}",
        f"- Minimum categories: {result.minimum_thresholds_used.minimum_categories}",
        f"- Minimum claims per category: {result.minimum_thresholds_used.minimum_claims_per_category}",
        f"- Minimum confidence buckets: {result.minimum_thresholds_used.minimum_confidence_buckets}",
        f"- Maximum contradiction rate: {_pct(result.minimum_thresholds_used.maximum_contradiction_rate)}",
        f"- Maximum high-confidence contradictions: {result.minimum_thresholds_used.maximum_high_confidence_contradictions}",
        f"- Maximum unresolved rate: {_pct(result.minimum_thresholds_used.maximum_unresolved_rate)}",
        "",
        "### Scope Note",
        "",
        "- This `ready` / `not_ready` result applies only to the scope above.",
        "- It does not imply production readiness, scoring readiness, runtime readiness, provider-pilot readiness, or model-training readiness.",
        "- Unsupported scopes are reported via warnings and do not silently reuse broader corpus thresholds.",
        "",
        "## Summary Metrics",
        "",
        f"- Contradiction rate: {_pct(result.contradiction_rate)}",
        f"- Unresolved rate: {_pct(result.unresolved_rate)}",
        f"- Overconfidence rate: {_pct(result.overconfidence_rate)}",
        "",
        "## Block Reasons",
        "",
    ]
    if result.block_reasons:
        lines.extend(f"- {reason}" for reason in result.block_reasons)
    else:
        lines.append("- none")
    lines.extend(["", "## Warning Reasons", ""])
    if result.warning_reasons:
        lines.extend(f"- {reason}" for reason in result.warning_reasons)
    else:
        lines.append("- none")
    lines.extend(["", "## Category Coverage", "", "| Category | Claims | Reviewed | Share | Min required | Meets minimum |", "| --- | ---: | ---: | ---: | ---: | --- |"])
    for category, row in sorted(result.category_coverage.items()):
        lines.append(f"| {category} | {row.count} | {row.reviewed_count} | {_pct(row.share)} | {row.minimum_required} | {str(row.meets_minimum).lower()} |")
    lines.extend(["", "## Confidence Bucket Coverage", "", "| Bucket | Claims | Reviewed | Share | Min required | Meets minimum |", "| --- | ---: | ---: | ---: | ---: | --- |"])
    for bucket, row in sorted(result.confidence_bucket_coverage.items()):
        lines.append(f"| {bucket} | {row.count} | {row.reviewed_count} | {_pct(row.share)} | {row.minimum_required} | {str(row.meets_minimum).lower()} |")
    lines.extend(["", "## Recommendation", "", f"- {result.recommendation}", "", "## Notes", ""])
    if result.notes:
        lines.extend(f"- {note}" for note in result.notes)
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip()
