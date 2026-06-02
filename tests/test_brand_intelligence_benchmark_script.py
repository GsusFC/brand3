from __future__ import annotations

from scripts.brand_intelligence_benchmark import _filter_cases_by_providers
from src.research.brand_intelligence_benchmark import BrandIntelligenceBenchmarkCase


def test_filter_cases_by_providers_keeps_requested_owned_web_providers() -> None:
    cases = [
        BrandIntelligenceBenchmarkCase("A", "https://a.example", owned_web_provider="firecrawl"),
        BrandIntelligenceBenchmarkCase("B", "https://b.example", owned_web_provider="playwright"),
        BrandIntelligenceBenchmarkCase("C", "https://c.example", owned_web_provider="tinyfish"),
    ]

    filtered = _filter_cases_by_providers(cases, "firecrawl, tinyfish")

    assert [case.owned_web_provider for case in filtered] == ["firecrawl", "tinyfish"]


def test_filter_cases_by_providers_returns_all_cases_without_filter() -> None:
    cases = [
        BrandIntelligenceBenchmarkCase("A", "https://a.example", owned_web_provider="firecrawl"),
        BrandIntelligenceBenchmarkCase("B", "https://b.example", owned_web_provider="playwright"),
    ]

    assert _filter_cases_by_providers(cases, "") == cases
