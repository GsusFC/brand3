"""Promotion gate for Search Enrichment Lab observations.

The Lab can compare online providers, but production integration must remain an
explicit decision. This module is pure and does not write raw inputs, evidence,
or scoring artifacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


PromotionStatus = Literal["promote", "shadow_only", "reject"]


@dataclass(frozen=True)
class SearchProviderPromotionDecision:
    provider: str
    status: PromotionStatus
    eligible_count: int
    limited_count: int
    observed_count: int
    error_count: int
    human_review_count: int
    covered_channels: tuple[str, ...] = ()
    average_confidence: float = 0.0
    average_cost_estimate: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SearchEnrichmentPromotionReport:
    version: str = "search_enrichment_promotion_v0_1"
    status: PromotionStatus = "reject"
    provider_decisions: tuple[SearchProviderPromotionDecision, ...] = ()
    promoted_providers: tuple[str, ...] = ()
    shadow_only_providers: tuple[str, ...] = ()
    rejected_providers: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SearchEnrichmentPromotionPolicy:
    min_cases: int = 3
    min_eligible_observations: int = 3
    min_covered_channels: int = 2
    min_average_confidence: float = 0.6
    max_error_rate: float = 0.25
    max_human_review_rate: float = 0.5
    max_average_cost_estimate: float = 0.02
    required_channels: tuple[str, ...] = ("owned_web", "search")


def evaluate_search_enrichment_promotion(
    summary: dict[str, Any],
    *,
    policy: SearchEnrichmentPromotionPolicy | None = None,
) -> SearchEnrichmentPromotionReport:
    """Evaluate whether Lab provider evidence is ready for production promotion."""
    policy = policy or SearchEnrichmentPromotionPolicy()
    case_count = int(summary.get("case_count") or 0)
    provider_metrics = summary.get("provider_metrics") or summary.get("provider_scores") or {}
    report_reasons: list[str] = []
    if case_count < policy.min_cases:
        report_reasons.append(f"insufficient_cases:{case_count}<{policy.min_cases}")

    decisions = tuple(
        _provider_decision(str(provider), metrics, case_count=case_count, policy=policy)
        for provider, metrics in sorted(provider_metrics.items())
        if isinstance(metrics, dict)
    )
    promoted = tuple(item.provider for item in decisions if item.status == "promote")
    shadow_only = tuple(item.provider for item in decisions if item.status == "shadow_only")
    rejected = tuple(item.provider for item in decisions if item.status == "reject")
    if not decisions:
        report_reasons.append("no_provider_metrics")
    if not promoted:
        report_reasons.append("no_provider_ready_for_promotion")

    status: PromotionStatus
    if promoted and case_count >= policy.min_cases:
        status = "promote"
    elif shadow_only or promoted:
        status = "shadow_only"
    else:
        status = "reject"

    return SearchEnrichmentPromotionReport(
        status=status,
        provider_decisions=decisions,
        promoted_providers=promoted,
        shadow_only_providers=shadow_only,
        rejected_providers=rejected,
        reasons=tuple(report_reasons),
    )


def _provider_decision(
    provider: str,
    metrics: dict[str, Any],
    *,
    case_count: int,
    policy: SearchEnrichmentPromotionPolicy,
) -> SearchProviderPromotionDecision:
    observed_count = int(metrics.get("observed_count") or metrics.get("observation_count") or 0)
    eligible_count = int(metrics.get("eligible_count") or 0)
    limited_count = int(metrics.get("limited_count") or 0)
    error_count = int(metrics.get("error_count") or 0)
    human_review_count = int(metrics.get("human_review_count") or 0)
    covered_channels = tuple(str(item) for item in metrics.get("covered_channels") or ())
    average_confidence = float(metrics.get("average_confidence") or 0.0)
    average_cost = float(metrics.get("average_cost_estimate") or 0.0)

    reasons: list[str] = []
    if case_count < policy.min_cases:
        reasons.append(f"insufficient_cases:{case_count}<{policy.min_cases}")
    if eligible_count < policy.min_eligible_observations:
        reasons.append(
            f"insufficient_eligible_observations:{eligible_count}<{policy.min_eligible_observations}"
        )
    if len(covered_channels) < policy.min_covered_channels:
        reasons.append(f"insufficient_channel_coverage:{len(covered_channels)}<{policy.min_covered_channels}")
    missing_required = [channel for channel in policy.required_channels if channel not in covered_channels]
    if missing_required:
        reasons.append(f"missing_required_channels:{','.join(missing_required)}")
    if average_confidence < policy.min_average_confidence:
        reasons.append(f"low_average_confidence:{average_confidence:.2f}<{policy.min_average_confidence:.2f}")
    if _rate(error_count, observed_count + error_count) > policy.max_error_rate:
        reasons.append("high_error_rate")
    if _rate(human_review_count, observed_count) > policy.max_human_review_rate:
        reasons.append("high_human_review_rate")
    if average_cost > policy.max_average_cost_estimate:
        reasons.append(f"cost_above_threshold:{average_cost:.4f}>{policy.max_average_cost_estimate:.4f}")

    status: PromotionStatus
    if not reasons:
        status = "promote"
    elif eligible_count > 0 and observed_count > 0 and average_confidence >= policy.min_average_confidence:
        status = "shadow_only"
    else:
        status = "reject"

    return SearchProviderPromotionDecision(
        provider=provider,
        status=status,
        eligible_count=eligible_count,
        limited_count=limited_count,
        observed_count=observed_count,
        error_count=error_count,
        human_review_count=human_review_count,
        covered_channels=covered_channels,
        average_confidence=average_confidence,
        average_cost_estimate=average_cost,
        reasons=tuple(reasons),
    )


def _rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return count / total
