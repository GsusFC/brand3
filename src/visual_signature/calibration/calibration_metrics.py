"""Metrics and summaries for Visual Signature calibration evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from src.visual_signature.calibration.calibration_models import (
    AgreementState,
    CalibrationRecord,
    CalibrationSummary,
    ConfidenceBucket,
    UncertaintyAlignment,
)


def build_calibration_summary(
    records: Iterable[CalibrationRecord],
    *,
    calibration_run_id: str,
    source_phase_one_root: str,
    source_phase_two_root: str,
    source_capture_manifest_path: str | None = None,
    source_dismissal_audit_path: str | None = None,
    source_brand_catalog_path: str | None = None,
    source_artifact_refs: list[str] | None = None,
    source_artifact_hashes: dict[str, str] | None = None,
    schema_versions: dict[str, str] | None = None,
    generated_at: datetime | None = None,
) -> CalibrationSummary:
    rows = list(records)
    total = len(rows)
    reviewed = [record for record in rows if record.review_outcome is not None]
    agreement_counts = Counter(record.agreement_state for record in rows)
    confidence_counts = Counter(record.confidence_bucket for record in rows)
    review_status_counts = Counter(
        record.review_outcome.review_status for record in rows if record.review_outcome is not None
    )
    high_confidence_contradictions = sum(
        1
        for record in rows
        if record.agreement_state == "contradicted" and record.confidence_bucket == "high"
    )
    uncertainty_counts = Counter(record.uncertainty_alignment for record in rows)
    category_breakdown = _group_breakdown(rows, key=lambda record: record.category)
    claim_kind_breakdown = _group_breakdown(rows, key=lambda record: record.claim.claim_kind)
    source_breakdown = _source_breakdown(rows)

    return CalibrationSummary(
        schema_version="visual-signature-calibration-summary-1",
        taxonomy_version="phase-zero-taxonomy-1",
        record_type="calibration_summary",
        calibration_run_id=calibration_run_id,
        generated_at=generated_at or datetime.now(timezone.utc),
        source_phase_one_root=source_phase_one_root,
        source_phase_two_root=source_phase_two_root,
        source_capture_manifest_path=source_capture_manifest_path,
        source_dismissal_audit_path=source_dismissal_audit_path,
        source_brand_catalog_path=source_brand_catalog_path,
        source_artifact_refs=source_artifact_refs or [],
        source_artifact_hashes=source_artifact_hashes or {},
        record_count=total,
        summary_count_consistency=True,
        schema_versions=schema_versions or {},
        total_claims=total,
        reviewed_claims=len(reviewed),
        confirmed_count=agreement_counts["confirmed"],
        confirmed_rate=_rate(agreement_counts["confirmed"], total),
        contradicted_count=agreement_counts["contradicted"],
        contradicted_rate=_rate(agreement_counts["contradicted"], total),
        unresolved_count=agreement_counts["unresolved"],
        unresolved_rate=_rate(agreement_counts["unresolved"], total),
        insufficient_review_count=agreement_counts["insufficient_review"],
        insufficient_review_rate=_rate(agreement_counts["insufficient_review"], total),
        high_confidence_contradiction_count=high_confidence_contradictions,
        overconfidence_rate=_rate(sum(1 for record in rows if record.uncertainty_alignment == "overconfident"), total),
        uncertainty_accepted_count=uncertainty_counts["uncertainty_accepted"],
        uncertainty_accepted_rate=_rate(uncertainty_counts["uncertainty_accepted"], total),
        agreement_distribution=dict(sorted(agreement_counts.items())),
        confidence_bucket_distribution=dict(sorted(confidence_counts.items())),
        category_breakdown=category_breakdown,
        claim_kind_breakdown=claim_kind_breakdown,
        source_breakdown=source_breakdown,
        review_status_distribution=dict(sorted(review_status_counts.items())),
        notes=[
            "Calibration is evidence-only.",
            "Missing review is marked as insufficient_review, not contradicted.",
            "Unclear review is marked as unresolved, not contradicted.",
            "No scoring, rubric dimensions, production reports, or UI are modified.",
        ],
    )


def calibration_summary_markdown(summary: CalibrationSummary) -> str:
    lines = [
        "# Visual Signature Calibration Summary",
        "",
        "Evidence-only calibration output comparing machine claims against reviewed outcomes.",
        "",
        "## Bundle Metadata",
        "",
        f"- Calibration run ID: `{summary.calibration_run_id}`",
        f"- Generated at: {summary.generated_at.isoformat()}",
        f"- Record count: {summary.record_count}",
        f"- Summary count consistency: {str(summary.summary_count_consistency).lower()}",
        f"- Evidence-only: yes",
        f"- No scoring impact: yes",
        f"- No rubric impact: yes",
        f"- No production UI/report impact: yes",
        f"- Missing review is insufficient_review: yes",
        f"- Unclear review is unresolved: yes",
        "",
        "### Source Artifacts",
        "",
        *(
            [
                f"- `{ref}` -> `{summary.source_artifact_hashes.get(ref, 'not-hashed')}`"
                for ref in summary.source_artifact_refs
            ]
            if summary.source_artifact_refs
            else ["- none"]
        ),
        "",
        f"- Total claims: {summary.total_claims}",
        f"- Reviewed claims: {summary.reviewed_claims}",
        f"- Confirmed: {summary.confirmed_count} ({_pct(summary.confirmed_rate)})",
        f"- Contradicted: {summary.contradicted_count} ({_pct(summary.contradicted_rate)})",
        f"- Unresolved: {summary.unresolved_count} ({_pct(summary.unresolved_rate)})",
        f"- Insufficient review: {summary.insufficient_review_count} ({_pct(summary.insufficient_review_rate)})",
        f"- High-confidence contradictions: {summary.high_confidence_contradiction_count}",
        f"- Overconfidence rate: {_pct(summary.overconfidence_rate)}",
        f"- Uncertainty accepted: {summary.uncertainty_accepted_count} ({_pct(summary.uncertainty_accepted_rate)})",
        "",
        "## Category Breakdown",
        "",
        "| Category | Claims | Reviewed | Confirmed | Contradicted | Unresolved | Insufficient review | High-conf contradiction | Overconfidence | Uncertainty accepted |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category, row in sorted(summary.category_breakdown.items()):
        lines.append(
            f"| {category} | {row['total_claims']} | {row['reviewed_claims']} | {row['confirmed_count']} | "
            f"{row['contradicted_count']} | {row['unresolved_count']} | {row['insufficient_review_count']} | "
            f"{row['high_confidence_contradiction_count']} | {_pct(row['overconfidence_rate'])} | "
            f"{row['uncertainty_accepted_count']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Kind Breakdown",
            "",
            "| Claim Kind | Claims | Reviewed | Confirmed | Contradicted | Unresolved | Insufficient review | High-conf contradiction | Overconfidence | Uncertainty accepted |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for claim_kind, row in sorted(summary.claim_kind_breakdown.items()):
        lines.append(
            f"| {claim_kind} | {row['total_claims']} | {row['reviewed_claims']} | {row['confirmed_count']} | "
            f"{row['contradicted_count']} | {row['unresolved_count']} | {row['insufficient_review_count']} | "
            f"{row['high_confidence_contradiction_count']} | {_pct(row['overconfidence_rate'])} | "
            f"{row['uncertainty_accepted_count']} |"
        )
    lines.extend(
        [
            "",
            "## Source Breakdown",
            "",
        ]
    )
    for source, row in sorted(summary.source_breakdown.items()):
        lines.append(f"- `{source}`: {row['count']} (avg per claim: {row['average_per_claim']:.2f})")
    lines.extend(
        [
            "",
            "## Agreement Distribution",
            "",
            f"- {', '.join(f'{key}:{value}' for key, value in sorted(summary.agreement_distribution.items())) or '-'}",
            "",
            "## Confidence Buckets",
            "",
            f"- {', '.join(f'{key}:{value}' for key, value in sorted(summary.confidence_bucket_distribution.items())) or '-'}",
        ]
    )
    return "\n".join(lines).rstrip()


def _group_breakdown(
    records: list[CalibrationRecord],
    *,
    key,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[CalibrationRecord]] = defaultdict(list)
    for record in records:
        grouped[str(key(record) or "uncategorized")].append(record)
    return {
        group_key: _summary_row(group_records)
        for group_key, group_records in sorted(grouped.items())
    }


def _summary_row(records: list[CalibrationRecord]) -> dict[str, Any]:
    total = len(records)
    reviewed = [record for record in records if record.review_outcome is not None]
    agreement_counts = Counter(record.agreement_state for record in records)
    uncertainty_counts = Counter(record.uncertainty_alignment for record in records)
    return {
        "total_claims": total,
        "reviewed_claims": len(reviewed),
        "confirmed_count": agreement_counts["confirmed"],
        "confirmed_rate": _rate(agreement_counts["confirmed"], total),
        "contradicted_count": agreement_counts["contradicted"],
        "contradicted_rate": _rate(agreement_counts["contradicted"], total),
        "unresolved_count": agreement_counts["unresolved"],
        "unresolved_rate": _rate(agreement_counts["unresolved"], total),
        "insufficient_review_count": agreement_counts["insufficient_review"],
        "insufficient_review_rate": _rate(agreement_counts["insufficient_review"], total),
        "high_confidence_contradiction_count": sum(
            1 for record in records if record.agreement_state == "contradicted" and record.confidence_bucket == "high"
        ),
        "overconfidence_rate": _rate(sum(1 for record in records if record.uncertainty_alignment == "overconfident"), total),
        "uncertainty_accepted_count": uncertainty_counts["uncertainty_accepted"],
        "uncertainty_accepted_rate": _rate(uncertainty_counts["uncertainty_accepted"], total),
        "agreement_distribution": dict(sorted(agreement_counts.items())),
        "confidence_bucket_distribution": dict(sorted(Counter(record.confidence_bucket for record in records).items())),
    }


def _source_breakdown(records: list[CalibrationRecord]) -> dict[str, dict[str, Any]]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update({key: int(value) for key, value in record.source_breakdown.items() if int(value) > 0})
    total = len(records)
    return {
        key: {
            "count": value,
            "average_per_claim": _rate(value, total),
        }
        for key, value in sorted(counts.items())
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def _pct(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "-"
