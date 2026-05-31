from src.reports.entity_research_packet import (
    build_entity_research_packet,
    entity_scope_for_url,
    surface_role_for_url,
)
from src.collectors.web_collector import WebData
from src.collectors.exa_collector import ExaData, ExaResult


def test_entity_research_packet_detects_lab_subdomain_as_product_surface() -> None:
    packet = build_entity_research_packet(
        input_url="https://lab.naturaumana.ai",
        brand_name="lab.naturaumana.ai",
        entity_discovery={
            "analysis_scope": "product_with_parent",
            "entity_name": "tinyNature",
            "parent_brand_name": "Natura Umana",
            "product_name": "tinyNature",
        },
        discovery_search_plan={"owned_urls": ["https://lab.naturaumana.ai"]},
    ).to_dict()

    assert packet["audited_surface_type"] == "product_surface"
    assert packet["parent_brand"] == "Natura Umana"
    assert packet["product_name"] == "tinyNature"
    assert packet["brand_architecture"] == "parent_brand_with_product_surface"
    urls = {item["url"]: item for item in packet["owned_surfaces"]}
    assert urls["https://lab.naturaumana.ai"]["role"] == "audited_surface"
    assert urls["https://www.naturaumana.ai"]["role"] == "parent_home"
    assert urls["https://www.naturaumana.ai/mission"]["role"] == "mission_about"
    assert urls["https://www.naturaumana.ai/natureos"]["role"] == "product_system"
    assert urls["https://www.naturaumana.ai/privacy-policy"]["role"] == "policy_security"


def test_surface_role_and_entity_scope_can_be_resolved_from_packet() -> None:
    packet = build_entity_research_packet(
        input_url="https://lab.naturaumana.ai",
        entity_discovery={"analysis_scope": "product_with_parent", "parent_brand_name": "Natura Umana"},
    )

    assert surface_role_for_url("https://www.naturaumana.ai/mission", packet) == "mission_about"
    assert entity_scope_for_url("https://www.naturaumana.ai/mission", packet) == "parent_brand"
    assert surface_role_for_url("https://lab.naturaumana.ai", packet) == "audited_surface"
    assert entity_scope_for_url("https://lab.naturaumana.ai", packet) == "audited_surface"


def test_entity_research_packet_adds_langchain_product_surfaces_from_owned_web() -> None:
    packet = build_entity_research_packet(
        input_url="https://www.langchain.com/",
        brand_name="www.langchain.com",
        entity_discovery={
            "analysis_scope": "company_brand",
            "entity_name": "LangChain",
            "parent_brand_name": None,
            "product_name": None,
        },
        discovery_search_plan={"owned_urls": ["https://www.langchain.com"]},
        web_data=WebData(
            url="https://www.langchain.com/",
            owned_fallback_urls=[
                "https://www.langchain.com/langsmith-platform",
                "https://www.langchain.com/about",
            ],
        ),
        exa_data=ExaData(
            brand_name="LangChain",
            mentions=[
                ExaResult(url="https://www.langchain.com/langchain", title="LangChain OSS"),
                ExaResult(url="https://docs.langchain.com/oss/javascript/langgraph/graph-api", title="LangGraph docs"),
            ],
        ),
    ).to_dict()

    assert packet["entity_name"] == "LangChain"
    product_scopes = {surface["entity_scope"] for surface in packet["product_surfaces"]}
    assert "product:LangSmith" in product_scopes
    assert "product:LangChain OSS" in product_scopes
    assert "product:LangGraph" in product_scopes
    assert surface_role_for_url("https://www.langchain.com/langsmith-platform", packet) == "product_system"
    assert entity_scope_for_url("https://www.langchain.com/langsmith-platform", packet) == "product:LangSmith"
