from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from src.collectors.exa_collector import ExaCollector


class _FakeExaClient:
    def __init__(self):
        self.calls: list[dict] = []

    def search(self, query: str, **kwargs):
        self.calls.append({"query": query, "kwargs": kwargs})
        if "competitors" in query:
            raise RuntimeError("fixture competitor failure")
        if "news" in query or "announcement launch funding partnership product" in query:
            return SimpleNamespace(results=[])
        return SimpleNamespace(
            results=[
                SimpleNamespace(
                    url="https://brand.io/post",
                    title="Brand mention",
                    text="Brand appears in an external source",
                    highlights=[],
                    summary="",
                    score=None,
                    published_date="2026-05-15",
                )
            ]
        )


def test_search_uses_news_profile_with_freshness_window():
    collector = ExaCollector(api_key="test")
    fake = _FakeExaClient()
    collector._client = fake

    collector.search(
        '"Brand" "brand.com" news',
        intent="news",
        brand_name="Brand",
        brand_url="https://brand.com",
    )

    assert fake.calls
    call = fake.calls[0]
    assert call["kwargs"]["type"] == "fast"
    assert call["kwargs"]["category"] == "news"
    assert call["kwargs"]["num_results"] == 10
    assert "start_published_date" in call["kwargs"]


def test_collect_brand_data_emits_structured_diagnostics_for_failed_and_empty_intents():
    collector = ExaCollector(api_key="test")
    fake = _FakeExaClient()
    collector._client = fake

    data = collector.collect_brand_data("Brand", "https://brand.com")
    diagnostics = data.diagnostics

    assert diagnostics["status"] == "degraded"
    assert "competitors" in diagnostics["failed_intents"]
    assert "news" in diagnostics["no_result_intents"]
    assert diagnostics["intent_results"]["competitors"]["status"] == "search_failed"
    assert diagnostics["intent_results"]["news"]["status"] == "no_results"
    assert diagnostics["latency_buckets_by_intent"]
    assert "search_events" in data.raw_responses
    competitor_call = next(call for call in fake.calls if "competitors" in call["query"])
    assert "exclude_domains" not in competitor_call["kwargs"]
    stripped = diagnostics["intent_results"]["competitors"]["stripped_filters"]
    assert any(item.get("param") == "exclude_domains" for item in stripped)


def test_collect_brand_data_uses_precision_exa_queries_in_production():
    collector = ExaCollector(api_key="test")
    fake = _FakeExaClient()
    collector._client = fake

    data = collector.collect_brand_data("Brand", "https://brand.com")
    queries = [call["query"] for call in fake.calls]

    assert any("official website product company about" in query for query in queries)
    assert any("review case study customer integration" in query for query in queries)
    assert any("announcement launch funding partnership product" in query for query in queries)
    assert any("AI recommendation alternatives best tools" in query for query in queries)
    assert any("alternatives competitors similar to Brand brand.com category" in query for query in queries)

    owned_call = next(call for call in fake.calls if "official website product company about" in call["query"])
    external_call = next(call for call in fake.calls if "review case study customer integration" in call["query"])
    assert owned_call["kwargs"]["include_domains"] == ["brand.com"]
    assert external_call["kwargs"]["exclude_domains"] == ["brand.com"]
    assert len(data.mentions) == 2
    assert "owned_confirmation" in data.diagnostics["intent_results"]
    assert "external_mentions" in data.diagnostics["intent_results"]


def test_collect_brand_data_runs_independent_intents_concurrently():
    class SlowCollector(ExaCollector):
        def __init__(self):
            super().__init__(api_key="test")
            self.active = 0
            self.max_active = 0
            self.lock = threading.Lock()

        def search(self, query: str, num_results: int | None = None, *, intent: str = "default", **kwargs):
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                time.sleep(0.03)
                self._record_event(
                    {
                        "intent": intent,
                        "query": query,
                        "status": "no_results",
                        "result_count": 0,
                        "elapsed_ms": 30,
                        "latency_bucket": "sub_1s",
                    }
                )
                return []
            finally:
                with self.lock:
                    self.active -= 1

    collector = SlowCollector()

    data = collector.collect_brand_data("Brand", "https://brand.com")

    assert collector.max_active > 1
    assert data.mentions == []
    assert data.competitors == []
    assert data.news == []
    assert data.ai_visibility_results == []


def test_same_name_different_root_is_related_unresolved():
    collector = ExaCollector(api_key="test")
    fake = _FakeExaClient()
    collector._client = fake

    results = collector.search(
        "brand query",
        intent="mentions",
        brand_name="Brand",
        brand_url="https://brand.com",
    )

    assert len(results) == 1
    item = results[0]
    assert item.source_class == "related_unresolved"
    assert item.relation == "unresolved"
    assert item.requires_human_review is True
    assert item.classification_reason == "same_name_different_root_domain"


def test_search_filters_url_results_without_content_body():
    class EmptyContentClient:
        def search(self, query: str, **kwargs):
            return SimpleNamespace(
                results=[
                    SimpleNamespace(
                        url="https://press.example.com/title-only",
                        title="Title is not enough",
                        text="",
                        highlights=[],
                        summary="",
                        score=0.1,
                        published_date="2026-05-15",
                    ),
                    SimpleNamespace(
                        url="https://press.example.com/body",
                        title="Body exists",
                        text="Independent body content",
                        highlights=[],
                        summary="",
                        score=0.2,
                        published_date="2026-05-15",
                    ),
                ]
            )

    collector = ExaCollector(api_key="test")
    collector._client = EmptyContentClient()

    results = collector.search(
        "brand query",
        intent="external_mentions",
        brand_name="Brand",
        brand_url="https://brand.com",
    )

    assert [item.url for item in results] == ["https://press.example.com/body"]
    diagnostics = collector._build_diagnostics()
    assert diagnostics["intent_results"]["external_mentions"]["filtered_empty_content_count"] == 1


def test_company_category_strips_unsupported_date_filters():
    collector = ExaCollector(api_key="test")
    fake = _FakeExaClient()
    collector._client = fake

    collector.search(
        "competitors similar to brand brand.com",
        intent="competitors",
        brand_name="Brand",
        brand_url="https://brand.com",
        start_crawl_date="2026-01-01",
        start_published_date="2026-01-01",
        exclude_domains=["brand.com"],
    )

    call = fake.calls[0]
    assert call["kwargs"]["category"] == "company"
    assert "start_crawl_date" not in call["kwargs"]
    assert "start_published_date" not in call["kwargs"]
    assert "exclude_domains" not in call["kwargs"]


def test_deep_reasoning_experiment_is_opt_in(monkeypatch):
    monkeypatch.setenv("BRAND3_EXA_ENABLE_DEEP_REASONING", "1")
    monkeypatch.setenv("BRAND3_EXA_DEEP_REASONING_INTENTS", "competitors,ai_visibility")
    collector = ExaCollector(api_key="test")
    fake = _FakeExaClient()
    collector._client = fake

    collector.search(
        "competitors similar to brand brand.com",
        intent="competitors",
        brand_name="Brand",
        brand_url="https://brand.com",
    )
    collector.search(
        '"Brand" "brand.com" news',
        intent="news",
        brand_name="Brand",
        brand_url="https://brand.com",
    )

    competitor_call = next(call for call in fake.calls if "competitors" in call["query"])
    news_call = next(call for call in fake.calls if "news" in call["query"])
    assert competitor_call["kwargs"]["type"] == "deep-reasoning"
    assert news_call["kwargs"]["type"] == "fast"
