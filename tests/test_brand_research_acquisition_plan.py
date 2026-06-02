from src.collectors.web_collector import WebData
from src.research.acquisition_plan import build_brand_research_acquisition_plan
from src.research.acquisition_trace import (
    build_brand_research_acquisition_quality_summary,
    build_brand_research_acquisition_trace,
)


def test_product_seed_expands_to_parent_and_product_fetch_sources() -> None:
    plan = build_brand_research_acquisition_plan(
        seed_url="https://chatgpt.com",
        brand_name="ChatGPT",
    )

    payload = plan.to_dict()
    sources = {item["url"]: item for item in payload["sources_to_fetch"]}

    assert payload["version"] == "brand_research_acquisition_plan_v0_1"
    assert payload["resolved_entity"] == "ChatGPT"
    assert payload["analysis_mode"] == "product_with_parent"
    assert payload["parent_brand"] == "OpenAI"
    assert payload["product_name"] == "ChatGPT"
    assert "https://chatgpt.com" in sources
    assert "https://openai.com" in sources
    assert sources["https://chatgpt.com"]["fetch_intent"] == "seed_surface"
    assert sources["https://openai.com"]["fetch_intent"] == "parent_brand_context"
    assert payload["queries_to_run"] == [
        "OpenAI ChatGPT brand positioning",
        "OpenAI ChatGPT product updates",
        "OpenAI ChatGPT reviews",
        "OpenAI ChatGPT competitors",
    ]


def test_lab_subdomain_seed_expands_parent_candidate_surfaces() -> None:
    plan = build_brand_research_acquisition_plan(
        seed_url="https://lab.naturaumana.ai",
        brand_name="lab.naturaumana.ai",
    )

    payload = plan.to_dict()
    sources = {item["url"]: item for item in payload["sources_to_fetch"]}

    assert payload["analysis_mode"] == "company_brand"
    assert payload["resolved_entity"] == "Natura Umana"
    assert "https://lab.naturaumana.ai" in sources
    assert "https://www.naturaumana.ai" in sources
    assert "https://www.naturaumana.ai/mission" in sources
    assert "https://www.naturaumana.ai/natureos" in sources
    assert sources["https://www.naturaumana.ai/mission"]["fetch_intent"] == "mission_and_origin"
    assert sources["https://www.naturaumana.ai/natureos"]["fetch_intent"] == "product_context"


def test_owned_web_urls_become_fetch_sources_and_blog_is_deferred() -> None:
    plan = build_brand_research_acquisition_plan(
        seed_url="https://www.langchain.com",
        brand_name="www.langchain.com",
        web_data=WebData(
            url="https://www.langchain.com",
            owned_fallback_urls=[
                "https://www.langchain.com/langsmith-platform",
                "https://www.langchain.com/about",
                "https://www.langchain.com/blog",
            ],
        ),
    )

    payload = plan.to_dict()
    sources = {item["url"]: item for item in payload["sources_to_fetch"]}

    assert payload["resolved_entity"] == "LangChain"
    assert sources["https://www.langchain.com/langsmith-platform"]["fetch_intent"] == "product_context"
    assert sources["https://www.langchain.com/about"]["fetch_intent"] == "mission_and_origin"
    assert sources["https://www.langchain.com/blog"]["fetch_intent"] == "defer_by_default"
    assert payload["sources_to_ignore"] == [
        {
            "url": "https://www.langchain.com/blog",
            "role": "blog_feed",
            "reason": "Blog/feed surfaces are not first-pass owned brand evidence unless explicitly requested.",
        }
    ]


def test_unknown_seed_records_low_confidence_limitations() -> None:
    plan = build_brand_research_acquisition_plan(
        seed_url="https://example.com",
        brand_name="Obscure Thing",
    )

    payload = plan.to_dict()

    assert payload["analysis_mode"] == "url_only"
    assert payload["entity_type"] == "unknown"
    assert payload["confidence"] <= 0.2
    assert "entity_resolution_low_confidence" in payload["limitations"]
    assert "seed_url_only_no_verified_brand_entity" in payload["limitations"]


def test_acquisition_trace_marks_observed_deferred_and_missing_sources() -> None:
    plan = {
        "version": "brand_research_acquisition_plan_v0_1",
        "seed_url": "https://www.langchain.com",
        "resolved_entity": "LangChain",
        "analysis_mode": "company_brand",
        "sources_to_fetch": [
            {
                "url": "https://www.langchain.com",
                "role": "audited_surface",
                "fetch_intent": "seed_surface",
                "priority": 10,
            },
            {
                "url": "https://www.langchain.com/about",
                "role": "mission_about",
                "fetch_intent": "mission_and_origin",
                "priority": 40,
            },
            {
                "url": "https://www.langchain.com/blog",
                "role": "blog_feed",
                "fetch_intent": "defer_by_default",
                "priority": 200,
            },
        ],
        "queries_to_run": ["LangChain brand positioning", "LangChain competitors"],
        "limitations": [],
    }

    trace = build_brand_research_acquisition_trace(
        acquisition_plan=plan,
        discovery_enrichment={
            "applied": True,
            "urls_used": ["https://www.langchain.com/about"],
            "queries_used": ["LangChain brand positioning"],
            "added_owned_evidence": 1,
            "added_third_party_evidence": 2,
        },
        raw_input_cache={"web": "miss", "exa": "hit"},
        content_source="firecrawl",
        data_quality="good",
        web_data=WebData(url="https://www.langchain.com", markdown_content="LangChain"),
    )

    sources = {item["url"]: item for item in trace["sources"]}
    queries = {item["query"]: item for item in trace["queries"]}

    assert trace["version"] == "brand_research_acquisition_trace_v0_1"
    assert trace["provider_summary"]["web_cache"] == "miss"
    assert trace["provider_summary"]["exa_cache"] == "hit"
    assert sources["https://www.langchain.com"]["status"] == "observed"
    assert sources["https://www.langchain.com/about"]["observed_via"] == "discovery_enrichment"
    assert sources["https://www.langchain.com/blog"]["status"] == "deferred"
    assert queries["LangChain brand positioning"]["status"] == "executed"
    assert queries["LangChain competitors"]["status"] == "not_executed"
    assert trace["coverage"]["observed_sources"] == 2
    assert "planned_queries_not_executed" in trace["limitations"]


def test_acquisition_quality_summary_scores_trace_coverage_and_fallback_dependency() -> None:
    strong = build_brand_research_acquisition_quality_summary(
        {
            "version": "brand_research_acquisition_trace_v0_1",
            "provider_summary": {
                "content_source": "firecrawl",
                "data_quality": "good",
                "discovery_added_owned_evidence": 2,
                "discovery_added_third_party_evidence": 1,
            },
            "coverage": {
                "planned_sources": 2,
                "observed_sources": 2,
                "planned_queries": 1,
                "executed_queries": 1,
                "deferred_sources": 0,
            },
            "sources": [],
            "queries": [],
        }
    )
    weak = build_brand_research_acquisition_quality_summary(
        {
            "version": "brand_research_acquisition_trace_v0_1",
            "provider_summary": {"content_source": "exa_fallback", "data_quality": "degraded"},
            "coverage": {
                "planned_sources": 3,
                "observed_sources": 1,
                "planned_queries": 2,
                "executed_queries": 0,
                "deferred_sources": 0,
            },
            "sources": [
                {"status": "planned_not_observed", "priority": 40, "fetch_intent": "mission_and_origin"},
                {"status": "planned_not_observed", "priority": 50, "fetch_intent": "customer_proof"},
            ],
            "queries": [],
        }
    )

    assert strong["label"] == "good"
    assert strong["score"] == 100
    assert "owned_evidence_enriched" in strong["strengths"]
    assert weak["score"] < strong["score"]
    assert weak["label"] == "insufficient"
    assert "critical_planned_sources_missing" in weak["warnings"]
    assert "high_fallback_dependency" in weak["warnings"]
