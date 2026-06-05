from __future__ import annotations

from scripts.search_enrichment_lab import _render_summary_md


def test_summary_markdown_renders_promotion_gate() -> None:
    markdown = _render_summary_md(
        {
            "version": "search_enrichment_lab_v0_1",
            "created_at": "2026-06-05T00:00:00+00:00",
            "providers": ["exa-fast"],
            "case_count": 3,
            "cases": [],
            "bakeoff": {"provider_metrics": {}},
            "provider_scores": {},
            "promotion": {
                "status": "shadow_only",
                "promoted_providers": [],
                "shadow_only_providers": ["exa-fast"],
                "rejected_providers": [],
                "reasons": ["no_provider_ready_for_promotion"],
                "provider_decisions": [
                    {
                        "provider": "exa-fast",
                        "status": "shadow_only",
                        "eligible_count": 2,
                        "limited_count": 1,
                        "observed_count": 4,
                        "error_count": 0,
                        "human_review_count": 1,
                        "covered_channels": ["owned_web", "search"],
                        "average_confidence": 0.68,
                        "average_cost_estimate": 0.004,
                        "reasons": ["insufficient_eligible_observations:2<3"],
                    }
                ],
            },
        }
    )

    assert "## Promotion Gate" in markdown
    assert "- status: `shadow_only`" in markdown
    assert "| exa-fast | shadow_only | 2 | 1 | 4 | 0 | 1 | owned_web, search | 0.68 | 0.004 | insufficient_eligible_observations:2<3 |" in markdown
