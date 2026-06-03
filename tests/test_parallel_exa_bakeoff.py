from __future__ import annotations

from scripts.parallel_exa_bakeoff import (
    BakeoffCase,
    _parallel_search_queries,
    annotate_provider_entity_boundary,
    render_markdown,
    summarize_bakeoff,
)


def test_parallel_search_queries_use_multiple_entity_anchored_queries() -> None:
    case = BakeoffCase("Parallel", "https://docs.parallel.ai/getting-started/overview")

    queries = _parallel_search_queries(case, "news")

    assert len(queries) == 3
    assert all("Parallel" in query for query in queries)
    assert all("docs.parallel.ai" in query for query in queries)
    assert any("funding" in query for query in queries)


def test_provider_entity_boundary_annotation_blocks_near_entity_collisions() -> None:
    case = BakeoffCase("SigmaOS", "https://sigmaos.com")
    payload = {
        "status": "ok",
        "provider": "parallel",
        "results": [
            {
                "url": "https://www.ycombinator.com/companies/sigmaos",
                "title": "SigmaOS: The new home for your internet",
                "excerpt": "SigmaOS is a MacOS web browser designed for faster work with workspaces and vertical tabs.",
                "score": 0.86,
            },
            {
                "url": "https://sigma.software/about/media/sigma-software-and-near-ai",
                "title": "Sigma Software and NEAR AI partner on infrastructure",
                "excerpt": "Sigma Software Group announced secure AI infrastructure for enterprise workloads.",
                "score": 0.88,
            },
        ],
    }

    annotated = annotate_provider_entity_boundary(payload, case=case)

    assert annotated["entity_boundary"]["eligible_count"] == 1
    assert annotated["entity_boundary"]["ineligible_count"] == 1
    assert annotated["results"][0]["brand3_evidence_eligibility"] == "eligible"
    assert annotated["results"][1]["brand3_evidence_eligibility"] == "ineligible"
    assert annotated["results"][1]["brand3_boundary_reason"] == "external_result_entity_boundary_collision"


def test_parallel_exa_bakeoff_summary_renders_boundary_blocked_column() -> None:
    summary = summarize_bakeoff(
        [
            {
                "case": {"brand": "SigmaOS", "domain": "sigmaos.com"},
                "outputs": {
                    "mentions": {
                        "exa": {
                            "status": "ok",
                            "result_count": 1,
                            "elapsed_ms": 10,
                            "unique_domains": ["sigmaos.com"],
                            "entity_boundary": {"ineligible_count": 0},
                            "results": [{"url": "https://sigmaos.com", "title": "SigmaOS"}],
                        },
                        "parallel": {
                            "status": "ok",
                            "result_count": 1,
                            "elapsed_ms": 12,
                            "unique_domains": ["sigma.software"],
                            "entity_boundary": {"ineligible_count": 1},
                            "results": [{"url": "https://sigma.software", "title": "Sigma Software"}],
                        },
                        "comparison": {
                            "url_overlap_count": 0,
                            "domain_overlap_count": 0,
                            "parallel_only_domains": ["sigma.software"],
                        },
                    }
                },
            }
        ]
    )

    markdown = render_markdown(summary)

    assert "Boundary blocked" in markdown
    assert "| SigmaOS | mentions | ok/1 (10ms) | ok/1 (12ms) | 1 |" in markdown
