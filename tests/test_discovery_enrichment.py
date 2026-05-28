from __future__ import annotations

from src.collectors.exa_collector import ExaData, ExaResult
from src.collectors.web_collector import WebData
from src.discovery.enrichment import build_discovery_enrichment


class _FakeExaCollector:
    def __init__(self):
        self.calls: list[dict] = []

    def search(self, query: str, num_results: int = 5, intent: str = "default", **kwargs):
        self.calls.append(
            {"query": query, "num_results": num_results, "intent": intent, "kwargs": kwargs}
        )
        suffix = len(self.calls)
        return [
            ExaResult(
                url=f"https://external{suffix}.example.com",
                title=f"Result {suffix}",
                text=f"Evidence {suffix}",
            )
        ]


def test_discovery_enrichment_applies_intent_and_provenance_with_cap_diagnostics():
    queries = [f"query-{idx}" for idx in range(20)]
    search_plan = {"owned_urls": ["https://brand.com"], "queries": queries}
    evidence_preview = {"recommended_to_use_for_scoring": True}
    exa = ExaData(brand_name="Brand", mentions=[])
    exa_collector = _FakeExaCollector()

    result = build_discovery_enrichment(
        search_plan,
        evidence_preview,
        exa_data=exa,
        web_data=None,
        exa_collector=exa_collector,
        web_collector=None,
    )

    assert result.payload["applied"] is True
    assert result.payload["diagnostics"]["applied_cap"] is True
    assert result.payload["diagnostics"]["cap"] == 15
    assert result.payload["diagnostics"]["truncated"] == 5
    assert result.exa_data is not None
    assert len(result.exa_data.mentions) == 15
    assert result.exa_data.diagnostics["enrichment_insertions"] == 15

    inserted = result.exa_data.mentions[0]
    assert inserted.metadata["enrichment_inserted"] is True
    assert inserted.metadata["enrichment_rationale"] == "discovery_search_plan_query_match"
    assert inserted.metadata["enrichment_query"].startswith("query-")
    assert all(call["intent"] == "enrichment" for call in exa_collector.calls)


class _FakeWebCollector:
    def __init__(self):
        self.calls: list[list[str]] = []

    def scrape_multiple(self, urls: list[str]):
        self.calls.append(urls)
        return [
            WebData(url=url, markdown_content=f"Evidence from {url}")
            for url in urls
            if not url.endswith("/security")
        ]


def test_discovery_enrichment_uses_entity_research_owned_surfaces_without_exa_preview():
    entity_research_packet = {
        "owned_surfaces": [
            {"url": "https://lab.naturaumana.ai", "role": "audited_surface"},
            {"url": "https://www.naturaumana.ai/mission", "role": "mission_about"},
            {"url": "https://www.naturaumana.ai/natureos", "role": "product_system"},
            {"url": "https://www.naturaumana.ai/privacy-policy", "role": "policy_security"},
            {"url": "https://www.naturaumana.ai/blog", "role": "blog_feed"},
        ]
    }
    web_collector = _FakeWebCollector()
    exa_collector = _FakeExaCollector()

    result = build_discovery_enrichment(
        {"owned_urls": [], "queries": ["should not run"]},
        {"recommended_to_use_for_scoring": False},
        web_data=WebData(url="https://lab.naturaumana.ai", markdown_content="Lab evidence"),
        web_collector=web_collector,
        exa_collector=exa_collector,
        entity_research_packet=entity_research_packet,
    )

    assert result.payload["applied"] is True
    assert result.payload["entity_research_applied"] is True
    assert result.payload["queries_used"] == []
    assert exa_collector.calls == []
    assert web_collector.calls == [[
        "https://lab.naturaumana.ai",
        "https://www.naturaumana.ai/mission",
        "https://www.naturaumana.ai/natureos",
        "https://www.naturaumana.ai/privacy-policy",
    ]]
    assert result.web_data is not None
    assert "## Subpage: https://www.naturaumana.ai/mission" in result.web_data.markdown_content
    assert "## Subpage: https://www.naturaumana.ai/natureos" in result.web_data.markdown_content
    assert "https://www.naturaumana.ai/blog" not in result.payload["urls_used"]
    assert result.web_data.owned_fallback_urls == [
        "https://lab.naturaumana.ai",
        "https://www.naturaumana.ai/mission",
        "https://www.naturaumana.ai/natureos",
        "https://www.naturaumana.ai/privacy-policy",
    ]


def test_discovery_enrichment_deduplicates_search_plan_and_entity_urls():
    entity_research_packet = {
        "owned_surfaces": [
            {"url": "https://brand.com/about", "role": "mission_about"},
        ]
    }
    web_collector = _FakeWebCollector()

    result = build_discovery_enrichment(
        {"owned_urls": ["https://brand.com/about", "https://brand.com/pricing"], "queries": []},
        {"recommended_to_use_for_scoring": True},
        web_collector=web_collector,
        entity_research_packet=entity_research_packet,
    )

    assert result.payload["urls_used"] == ["https://brand.com/about", "https://brand.com/pricing"]
    assert web_collector.calls == [["https://brand.com/about", "https://brand.com/pricing"]]
