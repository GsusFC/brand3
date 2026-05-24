"""Metrics for the Visual Signature corpus expansion pilot."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.visual_signature.corpus_expansion.corpus_expansion_models import (
    CORPUS_EXPANSION_METRICS_SCHEMA_VERSION,
    CORPUS_EXPANSION_READINESS_SCHEMA_VERSION,
    CorpusExpansionMetrics,
    CorpusExpansionReadinessAssessment,
    CorpusExpansionReviewQueue,
    validate_corpus_expansion_metrics_payload,
)


READINESS_MIN_TOTAL_CAPTURES = 20
READINESS_MIN_REVIEWED_CAPTURES = 20
READINESS_MIN_CATEGORY_DEPTH = 3
READINESS_MIN_CONFIDENCE_BUCKETS = 3
READINESS_MAX_CONTRADICTION_RATE = 0.25
READINESS_MAX_UNRESOLVED_RATE = 0.25
READINESS_MIN_REVIEWER_COVERAGE = 0.4


def build_corpus_expansion_metrics(
    queue: CorpusExpansionReviewQueue,
    *,
    target_capture_count: int | None = None,
    generated_at: datetime | None = None,
) -> CorpusExpansionMetrics:
    items = queue.queue_items
    current_capture_count = len(items)
    reviewed_capture_count = sum(1 for item in items if item.queue_state == "reviewed")
    queue_state_distribution = dict(sorted(queue.queue_state_distribution.items()))
    category_distribution = _count_distribution(item.category for item in items)
    confidence_distribution = _count_distribution(item.confidence_bucket for item in items)
    confirmed_count = sum(1 for item in items if item.review_outcome == "confirmed")
    contradicted_count = sum(1 for item in items if item.review_outcome == "contradicted")
    unresolved_count = sum(1 for item in items if item.queue_state == "unresolved")
    needs_additional_evidence_count = sum(1 for item in items if item.queue_state == "needs_additional_evidence")
    contradiction_rate = _rate(contradicted_count, current_capture_count)
    unresolved_rate = _rate(unresolved_count, current_capture_count)
    reviewer_coverage = _rate(reviewed_capture_count, current_capture_count)

    return CorpusExpansionMetrics(
        schema_version=CORPUS_EXPANSION_METRICS_SCHEMA_VERSION,
        record_type="corpus_expansion_metrics",
        pilot_run_id=queue.pilot_run_id,
        generated_at=generated_at or datetime.now(timezone.utc),
        target_capture_count=target_capture_count if target_capture_count is not None else queue.target_capture_count,
        current_capture_count=current_capture_count,
        reviewed_capture_count=reviewed_capture_count,
        queued_capture_count=sum(1 for item in items if item.queue_state == "queued"),
        unresolved_capture_count=unresolved_count,
        needs_additional_evidence_count=needs_additional_evidence_count,
        confirmed_count=confirmed_count,
        contradicted_count=contradicted_count,
        category_distribution=category_distribution,
        confidence_distribution=confidence_distribution,
        queue_state_distribution=queue_state_distribution,
        contradiction_rate=contradiction_rate,
        unresolved_rate=unresolved_rate,
        reviewer_coverage=reviewer_coverage,
        readiness_scope=queue.readiness_scope,
        readiness_status=queue.readiness_status,
        insufficient_for_model_training=True,
        insufficient_for_production_scoring=True,
        evidence_only_corpus_expansion=True,
        known_limitations=[
            "Current corpus expansion state is a scaffold, not a production corpus.",
            "This bundle is insufficient for model training.",
            "This bundle is insufficient for production scoring.",
            "This bundle is evidence-only corpus expansion.",
        ],
        notes=[
            "Evidence-only corpus expansion metrics.",
            "Governance-only; no runtime enablement.",
        ],
    )


def assess_corpus_expansion_readiness(
    metrics: CorpusExpansionMetrics,
) -> CorpusExpansionReadinessAssessment:
    block_reasons: list[str] = []
    warning_reasons: list[str] = []

    reviewed_categories = [category for category, count in metrics.category_distribution.items() if count > 0]
    confidence_buckets = [bucket for bucket, count in metrics.confidence_distribution.items() if count > 0]
    min_category_depth = min(metrics.category_distribution.values()) if metrics.category_distribution else 0

    thresholds_used = {
        "minimum_total_captures": READINESS_MIN_TOTAL_CAPTURES,
        "minimum_reviewed_captures": READINESS_MIN_REVIEWED_CAPTURES,
        "minimum_category_depth": READINESS_MIN_CATEGORY_DEPTH,
        "minimum_categories": 4,
        "minimum_confidence_buckets": READINESS_MIN_CONFIDENCE_BUCKETS,
        "maximum_contradiction_rate": READINESS_MAX_CONTRADICTION_RATE,
        "maximum_unresolved_rate": READINESS_MAX_UNRESOLVED_RATE,
        "minimum_reviewer_coverage": READINESS_MIN_REVIEWER_COVERAGE,
    }

    if metrics.current_capture_count < READINESS_MIN_TOTAL_CAPTURES:
        block_reasons.append("small_sample_size")
    if metrics.reviewed_capture_count < READINESS_MIN_REVIEWED_CAPTURES:
        block_reasons.append("insufficient_reviewed_captures")
    if len(reviewed_categories) < 4:
        block_reasons.append("insufficient_category_diversity")
    if min_category_depth < READINESS_MIN_CATEGORY_DEPTH:
        block_reasons.append("insufficient_category_depth")
    if len(confidence_buckets) < READINESS_MIN_CONFIDENCE_BUCKETS:
        block_reasons.append("insufficient_confidence_spread")
    if metrics.contradiction_rate > READINESS_MAX_CONTRADICTION_RATE:
        block_reasons.append("contradiction_rate_too_high")
    if metrics.unresolved_rate > READINESS_MAX_UNRESOLVED_RATE:
        block_reasons.append("unresolved_rate_too_high")
    if metrics.reviewer_coverage < READINESS_MIN_REVIEWER_COVERAGE:
        block_reasons.append("insufficient_reviewer_coverage")

    if metrics.current_capture_count > 50:
        warning_reasons.append("pilot_exceeds_recommended_upper_bound")

    status = "ready" if not block_reasons else "not_ready"
    return CorpusExpansionReadinessAssessment(
        schema_version=CORPUS_EXPANSION_READINESS_SCHEMA_VERSION,
        record_type="corpus_expansion_readiness",
        pilot_run_id=metrics.pilot_run_id,
        checked_at=datetime.now(timezone.utc),
        readiness_scope=metrics.readiness_scope,
        readiness_status=status,
        block_reasons=block_reasons,
        warning_reasons=warning_reasons,
        thresholds_used=thresholds_used,
        current_capture_count=metrics.current_capture_count,
        reviewed_capture_count=metrics.reviewed_capture_count,
        category_coverage=reviewed_categories,
        confidence_bucket_coverage=confidence_buckets,
        contradiction_rate=metrics.contradiction_rate,
        unresolved_rate=metrics.unresolved_rate,
        reviewer_coverage=metrics.reviewer_coverage,
    )


def corpus_expansion_metrics_markdown(
    metrics: CorpusExpansionMetrics,
    assessment: CorpusExpansionReadinessAssessment | None = None,
) -> str:
    assessment = assessment or assess_corpus_expansion_readiness(metrics)
    lines = [
        "# Visual Signature Corpus Expansion Metrics",
        "",
        "Evidence-only metrics for the controlled reviewed-corpus expansion pilot.",
        "",
        "- Evidence-only: yes",
        "- Governance-only: yes",
        "- No scoring integration: yes",
        "- No runtime enablement: yes",
        "- No model-training enablement: yes",
        "",
        f"- Pilot run ID: `{metrics.pilot_run_id}`",
        f"- Readiness scope: `{metrics.readiness_scope}`",
        f"- Readiness status: `{assessment.readiness_status}`",
        f"- Target capture count: {metrics.target_capture_count}",
        f"- Current capture count: {metrics.current_capture_count}",
        f"- Reviewed capture count: {metrics.reviewed_capture_count}",
        f"- Reviewer coverage: {_pct(metrics.reviewer_coverage)}",
        f"- Contradiction rate: {_pct(metrics.contradiction_rate)}",
        f"- Unresolved rate: {_pct(metrics.unresolved_rate)}",
        "",
        "## Explicit Limitations",
        "",
        "- insufficient for model training",
        "- insufficient for production scoring",
        "- evidence-only corpus expansion",
        "",
        "## Category Distribution",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    for category, count in sorted(metrics.category_distribution.items()):
        lines.append(f"| {category} | {count} |")
    lines.extend(
        [
            "",
            "## Confidence Distribution",
            "",
            "| Bucket | Count |",
            "| --- | ---: |",
        ]
    )
    for bucket, count in sorted(metrics.confidence_distribution.items()):
        lines.append(f"| {bucket} | {count} |")
    lines.extend(
        [
            "",
            "## Readiness Thresholds",
            "",
            f"- Scope evaluated: `{assessment.readiness_scope}`",
            f"- This result applies only to `{assessment.readiness_scope}`.",
            "- It does not imply production, scoring, runtime, provider-pilot, or model-training readiness.",
        ]
    )
    if assessment.block_reasons:
        lines.extend(["", "## Block Reasons", ""])
        lines.extend(f"- {reason}" for reason in assessment.block_reasons)
    if assessment.warning_reasons:
        lines.extend(["", "## Warning Reasons", ""])
        lines.extend(f"- {reason}" for reason in assessment.warning_reasons)
    return "\n".join(lines).rstrip()


def validate_corpus_expansion_metrics(payload: dict[str, Any]) -> list[str]:
    return validate_corpus_expansion_metrics_payload(payload)


def _count_distribution(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def _pct(value: float) -> str:
    return f"{value:.0%}"
