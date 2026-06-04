from __future__ import annotations

from scripts.search_enrichment_lab import (
    LabCase,
    _classify_lab_source,
    _guard_lab_entity_boundary,
    _profiled_query,
    _provider_run_to_acquisition_step,
    _search_exa,
    _planned_run_payload,
    _provider_scores,
    _render_summary_md,
    _selected_providers,
    _source_consensus,
    run_case,
)
from src.research.brand_intelligence import BrandSourceObservation


def test_selected_providers_treat_missing_keys_as_discarded(monkeypatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "exa-test")
    monkeypatch.setenv("PARALLEL_API_KEY", "")
    monkeypatch.setenv("TAVILY_API_KEY", "your-tavily-api-key-here")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-test")

    assert _selected_providers("exa,exa-deep-lite,parallel,tavily,brave") == ["exa", "exa-deep-lite", "brave"]


def test_selected_providers_do_not_enable_exa_deep_variants_by_default(monkeypatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "exa-test")
    monkeypatch.setenv("PARALLEL_API_KEY", "")
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("LINKUP_API_KEY", "")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "")
    monkeypatch.setenv("SERPAPI_API_KEY", "")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")
    monkeypatch.setenv("TINYFISH_API_KEY", "")

    assert _selected_providers("") == ["exa"]


def test_search_exa_deep_variant_uses_direct_search_and_preserves_cost(monkeypatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "exa-test")
    calls = []

    def fake_json_post(url, payload, *, headers, timeout_seconds):
        calls.append({"url": url, "payload": payload, "headers": headers, "timeout_seconds": timeout_seconds})
        return {
            "requestId": "req_123",
            "searchType": "deep-lite",
            "results": [
                {
                    "url": "https://www.langchain.com",
                    "title": "LangChain",
                    "text": "LangChain official site",
                    "highlights": ["LangChain builds infrastructure for agents."],
                    "publishedDate": "2026-01-01",
                },
                {
                    "url": "https://example.com/langchain-review",
                    "title": "Review",
                    "highlights": ["External review"],
                },
            ],
            "output": {
                "content": {"entity_summary": "LangChain", "source_notes": ["Official source found"]},
                "grounding": [{"field": "entity_summary", "confidence": "high", "citations": []}],
            },
            "costDollars": {"total": 0.02},
        }

    monkeypatch.setattr("scripts.search_enrichment_lab._json_post", fake_json_post)

    results = _search_exa(
        "LangChain official company",
        max_results=2,
        brand_name="LangChain",
        brand_url="https://www.langchain.com",
        provider="exa-deep-lite",
        search_type="deep-lite",
        timeout_seconds=12,
    )

    assert calls
    assert calls[0]["payload"]["type"] == "deep-lite"
    assert calls[0]["payload"]["contents"]["highlights"] is True
    assert calls[0]["payload"]["outputSchema"]["required"] == ["entity_summary", "source_notes"]
    assert results[0]["cost_estimate"] == 0.01
    assert results[0]["diagnostics"]["provider_variant"] == "exa-deep-lite"
    assert results[0]["diagnostics"]["grounding_count"] == 1


def test_classify_lab_source_matches_owned_same_root_and_ambiguous_domains() -> None:
    assert _classify_lab_source(
        url="https://www.langchain.com/docs",
        brand_url="https://www.langchain.com",
        brand_name="LangChain",
    ) == ("owned", "audited_surface", "same_host_owned_surface", False)

    assert _classify_lab_source(
        url="https://langchain-tools.example.com",
        brand_url="https://www.langchain.com",
        brand_name="LangChain",
    ) == ("related_unresolved", "unresolved", "same_name_different_root_domain", True)

    assert _classify_lab_source(
        url="https://producthunt.com/products/langchain",
        brand_url="https://www.langchain.com",
        brand_name="LangChain",
    ) == ("marketplace_listing", "external", "marketplace_listing_review_gated", True)


def test_planned_run_payload_estimates_calls_without_network() -> None:
    payload = _planned_run_payload(
        [LabCase("LangChain", "https://www.langchain.com")],
        ["firecrawl", "exa", "brave"],
        max_queries=2,
    )

    assert payload["mode"] == "plan_only"
    assert payload["case_count"] == 1
    assert payload["estimated_calls_by_provider"] == {"firecrawl": 1, "exa": 2, "brave": 2}
    assert payload["estimated_provider_call_count"] == 5
    assert payload["cases"][0]["query_count"] == 2


def test_planned_run_payload_includes_rich_queries_without_network() -> None:
    payload = _planned_run_payload(
        [LabCase("Bokeroon", "https://bokeroon.com")],
        ["exa-fast", "exa-deep-lite"],
        max_queries=1,
        query_profile="rich",
    )

    query = payload["cases"][0]["queries"][0]
    assert payload["query_profile"] == "rich"
    assert payload["estimated_calls_by_provider"] == {"exa-fast": 1, "exa-deep-lite": 1}
    assert 'Research the real brand/entity identity for "Bokeroon"' in query
    assert "same-name collisions" in query


def test_profiled_query_keeps_compact_default_and_expands_rich_identity_query() -> None:
    case = LabCase("Obscure Thing", "https://example.com")

    compact = _profiled_query(
        "Obscure Thing official brand",
        profile="compact",
        intent="entity_disambiguation",
        channel="search",
        case=case,
        entity=type("Entity", (), {"resolved_name": "Obscure Thing", "resolution_status": "unresolved"})(),
    )
    rich = _profiled_query(
        "Obscure Thing official brand",
        profile="rich",
        intent="entity_disambiguation",
        channel="search",
        case=case,
        entity=type("Entity", (), {"resolved_name": "Obscure Thing", "resolution_status": "unresolved"})(),
    )

    assert compact == "Obscure Thing official brand"
    assert len(rich) > len(compact)
    assert "ambiguous same-name entity" in rich


def test_guard_lab_entity_boundary_limits_unresolved_external_candidates() -> None:
    observation = BrandSourceObservation(
        "search",
        "observed",
        "https://external.example/company",
        "exa-deep-lite",
        "External profile",
        confidence=0.74,
        evidence_eligibility="eligible",
        source_class="external",
        relation_to_entity="external",
    )
    entity = type("Entity", (), {"resolution_status": "unresolved"})()

    guarded = _guard_lab_entity_boundary(observation, entity=entity)

    assert guarded.evidence_eligibility == "limited"
    assert guarded.requires_human_review is True
    assert guarded.confidence == 0.45
    assert guarded.diagnostics["lab_guardrail"] == "unresolved_entity_external_candidate_requires_review"


def test_source_consensus_groups_same_url_across_providers() -> None:
    consensus = _source_consensus(
        [
            BrandSourceObservation("search", "observed", "https://www.langchain.com/docs", "exa", source_class="owned", evidence_eligibility="eligible"),
            BrandSourceObservation("search", "observed", "https://langchain.com/docs/", "brave", source_class="owned", evidence_eligibility="eligible"),
            BrandSourceObservation("reviews", "observed", "https://example.com/review", "tavily", source_class="external", evidence_eligibility="eligible"),
        ]
    )

    assert consensus["consensus_source_count"] == 1
    assert consensus["single_provider_source_count"] == 1
    assert consensus["consensus_sources"][0]["url"] == "https://langchain.com/docs"
    assert consensus["consensus_sources"][0]["providers"] == ["brave", "exa"]


def test_provider_scores_reward_eligible_consensus_and_penalize_noise() -> None:
    scores = _provider_scores(
        {
            "exa": {
                "eligible_count": 3,
                "ineligible_count": 1,
                "human_review_count": 0,
                "error_count": 0,
                "average_latency_ms": 500,
                "source_class_counts": {"owned": 1},
            },
            "noisy": {
                "eligible_count": 2,
                "ineligible_count": 4,
                "human_review_count": 1,
                "error_count": 0,
                "average_latency_ms": 3000,
                "source_class_counts": {"related_unresolved": 1, "marketplace_listing": 1},
            },
        },
        [
            {
                "source_consensus": {
                    "consensus_sources": [
                        {"providers": ["exa", "brave"]},
                        {"providers": ["exa", "tavily"]},
                    ]
                }
            }
        ],
    )

    assert scores["exa"]["consensus_hits"] == 2
    assert scores["exa"]["score"] > scores["noisy"]["score"]


def test_run_case_builds_inventory_from_mocked_provider(monkeypatch) -> None:
    monkeypatch.setenv("EXA_API_KEY", "exa-test")

    def fake_run_search_provider(
        provider,
        query,
        *,
        channel,
        entity,
        seed_url,
        brand,
        max_results,
        timeout_seconds,
    ):
        return [
            BrandSourceObservation(
                channel=channel,
                status="observed",
                source_url="https://example.com/story",
                provider=provider,
                title="Example story",
                freshness="2026-01-01",
                confidence=0.8,
                evidence_eligibility="eligible",
                reason="mocked_observation",
                query_intent=query,
                source_class="external",
                relation_to_entity="external_context",
            )
        ]

    monkeypatch.setattr("scripts.search_enrichment_lab._run_search_provider", fake_run_search_provider)

    payload = run_case(
        LabCase("LangChain", "https://www.langchain.com"),
        providers=["exa"],
        max_results=1,
        timeout_seconds=1,
    )

    assert payload["version"] == "search_enrichment_lab_v0_1"
    assert payload["case"]["case_id"] == "langchain"
    assert payload["providers"] == ["exa"]
    assert payload["observations"]
    assert payload["observations"][0]["provider"] == "exa"
    assert payload["observations"][0]["query_intent"]
    assert payload["observations"][0]["source_class"] == "external"
    assert payload["inventory"]["eligible_channels"]
    assert isinstance(payload["provider_runs"][0]["observations"][0], dict)
    assert payload["acquisition_steps"][0]["provider"] == "exa"
    assert payload["acquisition_steps"][0]["status"] == "ok"
    assert payload["acquisition_steps"][0]["eligible"] is True
    assert payload["acquisition_steps"][0]["cache_status"] == "n/a"


def test_provider_run_to_acquisition_step_collapses_provider_run_state() -> None:
    step = _provider_run_to_acquisition_step(
        {
            "provider": "serpapi",
            "status": "error",
            "elapsed_ms": 87,
            "error": "timeout",
            "observations": [
                {
                    "status": "error",
                    "reason": "provider_exception",
                    "diagnostics": {"provider_variant": "serpapi"},
                }
            ],
        }
    )

    assert step.provider == "serpapi"
    assert step.status == "error"
    assert step.eligible is False
    assert step.error == "timeout"
    assert step.details["elapsed_ms"] == 87
    assert step.details["observation_count"] == 1


def test_render_summary_md_includes_provider_metrics_and_errors() -> None:
    markdown = _render_summary_md(
        {
            "version": "search_enrichment_lab_v0_1",
            "created_at": "2026-01-01T00:00:00Z",
            "providers": ["exa"],
            "case_count": 1,
            "cases": [
                {
                    "case_id": "langchain",
                    "observation_count": 1,
                    "consensus_source_count": 1,
                    "single_provider_source_count": 0,
                    "eligible_channels": ["search"],
                    "missing_required_channels": [],
                    "consensus_sources": [
                        {
                            "url": "https://langchain.com/docs",
                            "providers": ["brave", "exa"],
                            "source_classes": ["owned"],
                        }
                    ],
                }
            ],
            "provider_acquisition": [
                {
                    "case_id": "langchain",
                    "provider": "exa",
                    "status": "ok",
                    "eligible": True,
                    "cache_status": "n/a",
                    "observation_count": 1,
                    "elapsed_ms": 87,
                    "error": "",
                }
            ],
            "bakeoff": {
                "provider_metrics": {
                    "exa": {
                        "observed_count": 1,
                        "eligible_count": 1,
                        "limited_count": 0,
                        "ineligible_count": 0,
                        "error_count": 0,
                        "human_review_count": 0,
                        "covered_channels": ["search"],
                        "average_latency_ms": 123,
                        "total_cost_estimate": 0.02,
                        "average_cost_estimate": 0.01,
                        "source_class_counts": {"external": 1},
                        "average_confidence": 0.8,
                    }
                },
                "results": [
                    {
                        "case_id": "langchain",
                        "inventory": {
                            "observations": [
                                {
                                    "status": "error",
                                    "provider": "serpapi",
                                    "errors": ["timeout"],
                                }
                            ]
                        },
                    }
                ],
            },
            "provider_scores": {
                "exa": {
                    "score": 10,
                    "eligible_count": 1,
                    "consensus_hits": 1,
                    "owned_hits": 1,
                    "marketplace_hits": 0,
                    "related_unresolved_hits": 0,
                    "noise_hits": 0,
                    "ineligible_count": 0,
                    "human_review_count": 0,
                    "error_count": 0,
                    "latency_penalty": 0.1,
                }
            },
        }
    )

    assert "## Provider Acquisition Steps" in markdown
    assert "| langchain | exa | ok | yes | n/a | 1 | 87 |  |" in markdown
    assert "## Provider Metrics" in markdown
    assert "| exa | 1 | 1 | 0 | 0 | 0 | 0 | 123 | 0.02 | 0.01 | search | external:1 | 0.8 |" in markdown
    assert "## Experimental Provider Score" in markdown
    assert "| exa | 10 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0.1 |" in markdown
    assert "## Consensus Sources" in markdown
    assert "| langchain | brave, exa | https://langchain.com/docs | owned |" in markdown
    assert "## Provider Errors" in markdown
    assert "| langchain | serpapi | timeout |" in markdown
