from __future__ import annotations

from src.research.search_enrichment_promotion import (
    SearchEnrichmentPromotionPolicy,
    evaluate_search_enrichment_promotion,
)


def test_promotion_rejects_when_no_provider_metrics() -> None:
    report = evaluate_search_enrichment_promotion({"case_count": 3, "provider_scores": {}})

    assert report.status == "reject"
    assert "no_provider_metrics" in report.reasons
    assert "no_provider_ready_for_promotion" in report.reasons


def test_promotion_keeps_provider_shadow_only_when_cases_are_insufficient() -> None:
    report = evaluate_search_enrichment_promotion(
        {
            "case_count": 1,
            "provider_scores": {
                "exa-deep-lite": {
                    "observed_count": 8,
                    "eligible_count": 5,
                    "limited_count": 1,
                    "error_count": 0,
                    "human_review_count": 1,
                    "covered_channels": ["owned_web", "search"],
                    "average_confidence": 0.72,
                    "average_cost_estimate": 0.003,
                }
            },
        }
    )

    decision = report.provider_decisions[0]
    assert report.status == "shadow_only"
    assert decision.status == "shadow_only"
    assert decision.provider == "exa-deep-lite"
    assert "insufficient_cases:1<3" in decision.reasons


def test_promotion_promotes_provider_only_when_policy_passes() -> None:
    report = evaluate_search_enrichment_promotion(
        {
            "case_count": 4,
            "provider_scores": {
                "exa-fast": {
                    "observed_count": 12,
                    "eligible_count": 7,
                    "limited_count": 2,
                    "error_count": 0,
                    "human_review_count": 2,
                    "covered_channels": ["owned_web", "search", "reviews"],
                    "average_confidence": 0.74,
                    "average_cost_estimate": 0.004,
                }
            },
        }
    )

    assert report.status == "promote"
    assert report.promoted_providers == ("exa-fast",)
    assert report.provider_decisions[0].reasons == ()


def test_promotion_policy_can_require_lower_case_count_for_lab_smoke() -> None:
    report = evaluate_search_enrichment_promotion(
        {
            "case_count": 1,
            "provider_scores": {
                "exa-fast": {
                    "observed_count": 4,
                    "eligible_count": 3,
                    "covered_channels": ["owned_web", "search"],
                    "average_confidence": 0.7,
                }
            },
        },
        policy=SearchEnrichmentPromotionPolicy(min_cases=1),
    )

    assert report.status == "promote"
