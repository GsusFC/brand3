from __future__ import annotations

from src.research.brand_intelligence_benchmark import (
    BrandIntelligenceBenchmarkCase,
    render_brand_intelligence_benchmark_markdown,
    summarize_brand_intelligence_benchmark,
)


def test_benchmark_summary_aggregates_cases_and_provider_metrics() -> None:
    cases = [
        BrandIntelligenceBenchmarkCase("ChatGPT", "https://chatgpt.com", label="chatgpt-firecrawl", owned_web_provider="firecrawl"),
        BrandIntelligenceBenchmarkCase("lab.naturaumana.ai", "https://lab.naturaumana.ai", label="lab-playwright", owned_web_provider="playwright"),
    ]
    payloads = [
        {
            "input": {"brand": "ChatGPT", "url": "https://chatgpt.com", "owned_web_provider": "firecrawl"},
            "raw_counts": {"web_chars": 120, "owned_web_provider": "firecrawl"},
            "entity": {"resolution_status": "resolved"},
            "plan": {"interpretation_ready": True},
            "inventory": {
                "eligible_channels": ["owned_web", "reviews"],
                "missing_required_channels": [],
                "duplicate_source_urls": [],
                "conflicting_source_urls": [],
            },
            "evidence_graph": {"summary": {"evidence_count": 4, "rejected_count": 0}, "warnings": []},
            "observations": [
                {"provider": "exa", "status": "observed", "evidence_eligibility": "eligible", "channel": "reviews", "confidence": 0.74},
                {"provider": "firecrawl", "status": "observed", "evidence_eligibility": "limited", "channel": "owned_web", "confidence": 0.62},
            ],
        },
        {
            "input": {"brand": "lab.naturaumana.ai", "url": "https://lab.naturaumana.ai", "owned_web_provider": "playwright"},
            "raw_counts": {"web_chars": 240, "owned_web_provider": "playwright"},
            "entity": {"resolution_status": "provisional"},
            "plan": {"interpretation_ready": False},
            "inventory": {
                "eligible_channels": ["owned_web"],
                "missing_required_channels": ["search", "visual"],
                "duplicate_source_urls": ["https://lab.naturaumana.ai"],
                "conflicting_source_urls": [],
            },
            "evidence_graph": {"summary": {"evidence_count": 2, "rejected_count": 1}, "warnings": ["duplicate_source_observations"]},
            "observations": [
                {"provider": "exa", "status": "observed", "evidence_eligibility": "eligible", "channel": "reviews", "confidence": 0.7},
                {"provider": "playwright", "status": "observed", "evidence_eligibility": "eligible", "channel": "owned_web", "confidence": 0.88},
            ],
        },
    ]

    summary = summarize_brand_intelligence_benchmark(payloads, cases=cases)

    assert summary["version"] == "brand_intelligence_benchmark_v0_1"
    assert summary["case_count"] == 2
    assert summary["inventory_ready_count"] == 1
    assert summary["supported_inventory_ready_count"] == 1
    assert summary["provisional_case_count"] == 1
    assert summary["provider_metrics"]["exa"]["observation_count"] == 2
    assert summary["provider_metrics"]["firecrawl"]["covered_channels"] == ["owned_web"]
    assert summary["provider_metrics"]["playwright"]["covered_channels"] == ["owned_web"]
    assert summary["provider_metrics"]["firecrawl"]["average_owned_web_chars"] == 120.0
    assert summary["provider_metrics"]["playwright"]["average_owned_web_chars"] == 240.0
    assert summary["channel_coverage"]["owned_web"] == 2
    assert summary["most_common_missing_channels"][0][0] == "search"
    assert summary["unsupported_missing_channels"][0][0] == "visual"


def test_benchmark_markdown_renders_case_and_provider_tables() -> None:
    summary = {
        "case_count": 1,
        "inventory_ready_count": 1,
        "supported_inventory_ready_count": 1,
        "provisional_case_count": 0,
        "unresolved_case_count": 0,
        "cases": [
            {
                "brand": "ChatGPT",
                "owned_web_provider": "firecrawl",
                "resolution_status": "resolved",
                "inventory_ready": False,
                "supported_inventory_ready": True,
                "eligible_channels": ["owned_web", "reviews"],
                "missing_required_channels": ["search"],
                "evidence_count": 4,
                "warnings": ["missing_required_sources"],
            }
        ],
        "provider_metrics": {
            "exa": {"observed_count": 3, "eligible_count": 2, "limited_count": 1, "ineligible_count": 0, "error_count": 0, "covered_channels": ["reviews"], "average_owned_web_chars": 0},
            "firecrawl": {"observed_count": 1, "eligible_count": 0, "limited_count": 1, "ineligible_count": 0, "error_count": 0, "covered_channels": ["owned_web"], "average_owned_web_chars": 128.5},
            "playwright": {"observed_count": 1, "eligible_count": 1, "limited_count": 0, "ineligible_count": 0, "error_count": 0, "covered_channels": ["owned_web"], "average_owned_web_chars": 256.0},
        },
        "most_common_missing_channels": [("search", 1)],
    }

    markdown = render_brand_intelligence_benchmark_markdown(summary)

    assert "# Brand Intelligence Acquisition Benchmark" in markdown
    assert "| Brand | Web Provider | Status | Ready | Supported Ready | Eligible | Missing | Evidence | Warnings |" in markdown
    assert "| Provider | Observed | Eligible | Limited | Ineligible | Errors | Owned Web Chars Avg | Covered Channels |" in markdown
    assert "ChatGPT" in markdown
    assert "exa" in markdown
    assert "firecrawl" in markdown
    assert "playwright" in markdown


def test_supported_inventory_ready_ignores_only_unsupported_missing_channels() -> None:
    supported_gap_payload = {
        "input": {"brand": "LangChain", "url": "https://www.langchain.com", "owned_web_provider": "firecrawl"},
        "entity": {"resolution_status": "resolved"},
        "plan": {"interpretation_ready": True},
        "inventory": {"eligible_channels": ["owned_web", "search", "reviews"], "missing_required_channels": ["visual"]},
        "evidence_graph": {"summary": {"evidence_count": 3, "rejected_count": 0}, "warnings": ["missing_required_sources"]},
        "observations": [],
    }
    supported_provider_gap_payload = {
        "input": {"brand": "ChatGPT", "url": "https://chatgpt.com", "owned_web_provider": "tinyfish"},
        "entity": {"resolution_status": "resolved"},
        "plan": {"interpretation_ready": True},
        "inventory": {"eligible_channels": ["parent_owned_web", "reviews"], "missing_required_channels": ["owned_web", "search", "visual"]},
        "evidence_graph": {"summary": {"evidence_count": 3, "rejected_count": 1}, "warnings": ["missing_required_sources"]},
        "observations": [],
    }

    summary = summarize_brand_intelligence_benchmark([supported_gap_payload, supported_provider_gap_payload])

    assert summary["inventory_ready_count"] == 0
    assert summary["supported_inventory_ready_count"] == 1
    assert summary["cases"][0]["supported_inventory_ready"] is True
    assert summary["cases"][1]["supported_inventory_ready"] is False
