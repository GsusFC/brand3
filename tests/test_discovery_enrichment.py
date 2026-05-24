from __future__ import annotations

from src.collectors.exa_collector import ExaData, ExaResult
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
