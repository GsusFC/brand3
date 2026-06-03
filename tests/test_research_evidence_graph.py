from __future__ import annotations

from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot
from src.research.evidence_graph import BrandResearchRun, EvidenceClaim, EvidenceGraph, ResearchSource, build_evidence_graph_from_snapshot
from src.research.research_pack_builder import build_brand_research_pack_from_graph


def _base44_snapshot() -> dict:
    return {
        "run": {"id": 1001, "brand_name": "Base44", "url": "https://base44.com"},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://base44.com",
                    "title": "Base44",
                    "markdown_content": (
                        "Base44 is an AI app builder for non-technical founders.\n"
                        "Build and ship apps fast.\n"
                        "---\n"
                        "## Subpage: https://base44.com/about\n"
                        "Our founder exited a previous startup and built Base44 to make app creation simple.\n"
                        "We are on a mission to help teams ship software.\n"
                        "---\n"
                        "## Subpage: https://base44.com/privacy\n"
                        "Privacy and security are built in."
                    ),
                },
            },
            {
                "source": "exa",
                "payload": {
                    "mentions": [],
                    "competitors": [],
                    "ai_visibility_results": [],
                    "news": [
                        {
                            "url": "https://techcrunch.com/2026/01/01/base44-founder-exit",
                            "title": "Base44 founder exit lands new platform",
                            "summary": "Founder exit context",
                        }
                    ],
                },
            },
            {
                "source": "entity_research_packet",
                "payload": {
                    "version": "entity_research_packet_v0_1",
                    "input_url": "https://base44.com",
                    "audited_surface_type": "parent_home",
                    "entity_name": "Base44",
                    "parent_brand": None,
                    "product_name": None,
                    "brand_architecture": "single_brand_surface",
                    "owned_surfaces": [
                        {
                            "url": "https://base44.com",
                            "role": "audited_surface",
                            "entity_scope": "audited_surface",
                            "reason": "input",
                        }
                    ],
                    "confidence": "medium",
                    "limitations": [],
                },
            },
        ],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "brand_sentiment",
                "value": 0.7,
                "raw_value": "{'evidence': [{'quote': 'Trusted by founders and small teams', 'source_url': 'https://base44.com', 'signal': 'trusted'}]}",
                "confidence": 0.9,
                "source": "firecrawl",
            }
        ],
        "evidence_items": [],
    }


def _bokeroon_snapshot() -> dict:
    return {
        "run": {"id": 1002, "brand_name": "Bokeroon", "url": "https://bokeroon.com"},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://bokeroon.com",
                    "title": "Bokeroon",
                    "markdown_content": (
                        "Navigation Feed Articles Predictions\n"
                        "Article prediction: the page lists forward-looking content and menu chrome.\n"
                        "Bokeroon is a crypto platform for instant trading.\n"
                        "---\n"
                        "## Subpage: https://bokeroon.com/feed\n"
                        "Feed and page chrome."
                    ),
                },
            }
        ],
        "features": [],
        "evidence_items": [],
    }


def _lab_snapshot() -> dict:
    return {
        "run": {"id": 1003, "brand_name": "tinyNature", "url": "https://lab.naturaumana.ai"},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://lab.naturaumana.ai",
                    "title": "tinyNature",
                    "canonical_url": "https://lab.naturaumana.ai",
                    "owned_fallback_urls": [
                        "https://lab.naturaumana.ai",
                        "https://www.naturaumana.ai/mission",
                        "https://www.naturaumana.ai/natureos",
                        "https://www.naturaumana.ai/privacy-policy",
                    ],
                    "markdown_content": (
                        "Life orchestration, perfected by nature.\n"
                        "tinyNature is a personal AI assistant platform for life orchestration.\n"
                        "tinyNature is not just a chatbot; it is a command center.\n"
                        "---\n"
                        "## Subpage: https://www.naturaumana.ai/mission\n"
                        "Our mission is to build technology that enhances life without distraction.\n"
                        "We are building the future of human-machine interaction through voice-first personal agents.\n"
                        "---\n"
                        "## Subpage: https://www.naturaumana.ai/privacy-policy\n"
                        "Privacy first. Your data stays yours. Security is at the core."
                    ),
                },
            },
            {
                "source": "entity_research_packet",
                "payload": {
                    "version": "entity_research_packet_v0_1",
                    "input_url": "https://lab.naturaumana.ai",
                    "audited_surface_type": "product_lab",
                    "entity_name": "tinyNature",
                    "parent_brand": "Natura Umana",
                    "product_name": "tinyNature",
                    "brand_architecture": "parent_brand_with_product_surface",
                    "owned_surfaces": [
                        {
                            "url": "https://lab.naturaumana.ai",
                            "role": "audited_surface",
                            "entity_scope": "audited_surface",
                            "reason": "input",
                        },
                        {
                            "url": "https://www.naturaumana.ai/mission",
                            "role": "mission_about",
                            "entity_scope": "parent_brand",
                            "reason": "mission",
                        },
                        {
                            "url": "https://www.naturaumana.ai/natureos",
                            "role": "product_system",
                            "entity_scope": "parent_brand",
                            "reason": "system",
                        },
                        {
                            "url": "https://www.naturaumana.ai/privacy-policy",
                            "role": "policy_security",
                            "entity_scope": "parent_brand",
                            "reason": "privacy",
                        },
                    ],
                    "confidence": "medium",
                    "limitations": ["Product lab should retain parent-brand context."],
                },
            },
        ],
        "features": [],
        "evidence_items": [],
    }


def _sigmaos_like_snapshot() -> dict:
    return {
        "run": {"id": 1004, "brand_name": "SigmaOS", "url": "https://sigmaos.com"},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://sigmaos.com",
                    "title": "SigmaOS",
                    "markdown_content": (
                        "A smarter way to browse the internet.\n"
                        "The new home for your internet. One window. Many workspaces. All your tabs.\n"
                        "Your tabs are like tasks in a to-do list. Mark them as done once they're complete.\n"
                        "Work smarter, not harder.\n"
                        "Download Free\n"
                    ),
                },
            }
        ],
        "features": [],
        "evidence_items": [],
    }


def _langchain_like_snapshot() -> dict:
    return {
        "run": {"id": 1005, "brand_name": "www.langchain.com", "url": "https://www.langchain.com"},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://www.langchain.com",
                    "title": "LangChain",
                    "owned_fallback_urls": [
                        "https://www.langchain.com/langsmith-platform",
                        "https://www.langchain.com/about",
                        "https://www.langchain.com/langchain",
                        "https://docs.langchain.com/oss/javascript/langgraph/graph-api",
                    ],
                    "markdown_content": (
                        "LangSmith Agent Engineering Platform. Observe, evaluate, and deploy agents with LangSmith.\n"
                        "LangSmith turns your trace data into fuel for agent improvement.\n"
                        "---\n"
                        "## Subpage: https://www.langchain.com/about\n"
                        "LangChain provides the agent engineering platform and open-source frameworks for reliable agents.\n"
                        "Our mission is to figure out what the future of agents looks like and create tools that make it easy to build them.\n"
                        "---\n"
                        "## Subpage: https://www.langchain.com/langchain\n"
                        "LangChain OSS is the framework for building context-aware reasoning applications.\n"
                        "---\n"
                        "## Subpage: https://docs.langchain.com/oss/javascript/langgraph/graph-api\n"
                        "LangGraph provides durable execution for long-running agents."
                    ),
                },
            },
            {
                "source": "entity_research_packet",
                "payload": {
                    "version": "entity_research_packet_v0_1",
                    "input_url": "https://www.langchain.com",
                    "audited_surface_type": "parent_home",
                    "entity_name": "LangChain",
                    "parent_brand": None,
                    "product_name": "",
                    "brand_architecture": "single_brand_surface",
                    "owned_surfaces": [
                        {
                            "url": "https://www.langchain.com",
                            "role": "audited_surface",
                            "entity_scope": "audited_surface",
                            "reason": "input",
                        },
                        {
                            "url": "https://www.langchain.com/about",
                            "role": "mission_about",
                            "entity_scope": "parent_brand",
                            "reason": "about",
                        },
                        {
                            "url": "https://www.langchain.com/langsmith-platform",
                            "role": "product_system",
                            "entity_scope": "product:LangSmith",
                            "reason": "product",
                        },
                        {
                            "url": "https://www.langchain.com/langchain",
                            "role": "product_system",
                            "entity_scope": "product:LangChain OSS",
                            "reason": "product",
                        },
                        {
                            "url": "https://docs.langchain.com/oss/javascript/langgraph/graph-api",
                            "role": "product_system",
                            "entity_scope": "product:LangGraph",
                            "reason": "product",
                        },
                    ],
                    "product_surfaces": [
                        {
                            "url": "https://www.langchain.com/langsmith-platform",
                            "role": "product:LangSmith",
                            "entity_scope": "product:LangSmith",
                            "reason": "Detected product surface for LangSmith under LangChain.",
                        },
                        {
                            "url": "https://www.langchain.com/langchain",
                            "role": "product:LangChain OSS",
                            "entity_scope": "product:LangChain OSS",
                            "reason": "Detected product surface for LangChain OSS under LangChain.",
                        },
                        {
                            "url": "https://docs.langchain.com/oss/javascript/langgraph/graph-api",
                            "role": "product:LangGraph",
                            "entity_scope": "product:LangGraph",
                            "reason": "Detected product surface for LangGraph under LangChain.",
                        },
                    ],
                    "confidence": "medium",
                    "limitations": [],
                },
            },
        ],
        "features": [],
        "evidence_items": [],
    }


def _publicit_collision_snapshot() -> dict:
    return {
        "run": {"id": 1007, "brand_name": "Publicit", "url": "https://www.publicit.com"},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://www.publicit.com",
                    "title": "Publicit",
                    "markdown_content": (
                        "Publicit is an advertising automation platform for local operators.\n"
                        "Plan campaigns, publish creatives, and track results from one workspace."
                    ),
                },
            },
            {
                "source": "exa",
                "payload": {
                    "mentions": [
                        {
                            "url": "https://tech.example/publicit-launch",
                            "title": "Publicit launch brings campaign automation to local retailers",
                            "summary": "The Publicit team launched an advertising platform for small businesses.",
                        },
                        {
                            "url": "https://www.publicisgroupe.com/news/microsoft-publicis",
                            "title": "Microsoft and Publicis Groupe expand media partnership",
                            "summary": "Publicis Media announces a global advertising collaboration.",
                        },
                    ],
                    "competitors": [],
                    "ai_visibility_results": [],
                    "news": [],
                },
            },
            {
                "source": "entity_research_packet",
                "payload": {
                    "version": "entity_research_packet_v0_1",
                    "input_url": "https://www.publicit.com",
                    "audited_surface_type": "parent_home",
                    "entity_name": "Publicit",
                    "parent_brand": None,
                    "product_name": "",
                    "brand_architecture": "single_brand_surface",
                    "owned_surfaces": [
                        {
                            "url": "https://www.publicit.com",
                            "role": "audited_surface",
                            "entity_scope": "audited_surface",
                            "reason": "input",
                        }
                    ],
                    "confidence": "medium",
                    "limitations": [],
                },
            },
        ],
        "features": [],
        "evidence_items": [],
    }


def _sigmaos_collision_snapshot() -> dict:
    return {
        "run": {"id": 1008, "brand_name": "SigmaOS", "url": "https://sigmaos.com"},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://sigmaos.com",
                    "title": "SigmaOS",
                    "markdown_content": (
                        "SigmaOS is a browser designed for faster work.\n"
                        "The new home for your internet, organized with workspaces and vertical tabs."
                    ),
                },
            },
            {
                "source": "exa",
                "payload": {
                    "mentions": [
                        {
                            "url": "https://www.ycombinator.com/companies/sigmaos",
                            "title": "SigmaOS: The new home for your internet",
                            "summary": "SigmaOS is a MacOS web browser designed for faster work.",
                        },
                        {
                            "url": "https://sigma.software/about/media/sigma-software-and-near-ai",
                            "title": "Sigma Software and NEAR AI partner on infrastructure",
                            "summary": "Sigma Software Group announced secure AI infrastructure for enterprise workloads.",
                        },
                    ],
                    "competitors": [],
                    "ai_visibility_results": [],
                    "news": [],
                },
            },
            {
                "source": "entity_research_packet",
                "payload": {
                    "version": "entity_research_packet_v0_1",
                    "input_url": "https://sigmaos.com",
                    "audited_surface_type": "parent_home",
                    "entity_name": "SigmaOS",
                    "parent_brand": None,
                    "product_name": "",
                    "brand_architecture": "single_brand_surface",
                    "owned_surfaces": [
                        {
                            "url": "https://sigmaos.com",
                            "role": "audited_surface",
                            "entity_scope": "audited_surface",
                            "reason": "input",
                        }
                    ],
                    "confidence": "medium",
                    "limitations": [],
                },
            },
        ],
        "features": [],
        "evidence_items": [],
    }


def test_evidence_graph_from_snapshot_tracks_sources_and_block_claims() -> None:
    graph = build_evidence_graph_from_snapshot(_base44_snapshot())
    payload = graph.to_dict()

    assert payload["version"] == "brand_research_evidence_graph_v0_1"
    assert payload["run"]["resolved_entity"] == "Base44"
    assert payload["summary"]["source_counts"]["owned_home"] >= 1
    assert any(source["source_type"] == "owned_about" for source in payload["sources"].values())
    assert any(source["source_type"] == "press_founder" for source in payload["sources"].values())
    assert any("value_proposition" in claim["supports_blocks"] for claim in payload["claims"])
    assert any(claim["claim_type"] == "feature_evidence" for claim in payload["claims"])


def test_evidence_graph_preserves_noise_as_claims_not_strategy() -> None:
    graph = build_evidence_graph_from_snapshot(_bokeroon_snapshot())
    payload = graph.to_dict()

    noise_claims = [claim for claim in payload["claims"] if claim["claim_type"] == "noise"]
    assert noise_claims
    assert any("feed" in claim["text"].lower() or "chrome" in claim["text"].lower() for claim in noise_claims)
    assert all(not claim["supports_blocks"] for claim in noise_claims)


def test_evidence_graph_marks_product_surface_and_parent_owned_pages() -> None:
    graph = build_evidence_graph_from_snapshot(_lab_snapshot())
    payload = graph.to_dict()

    assert payload["run"]["entity_type"] == "product"
    assert payload["run"]["parent_brand"] == "Natura Umana"
    source_types = {source["source_type"] for source in payload["sources"].values()}
    assert "owned_about" in source_types
    assert "owned_product" in source_types
    assert "owned_security" in source_types
    assert any(claim["claim_type"] == "mission" for claim in payload["claims"])
    assert any("mission" in claim["supports_blocks"] for claim in payload["claims"])


def test_evidence_graph_roundtrips() -> None:
    graph = build_evidence_graph_from_snapshot(_lab_snapshot())
    payload = graph.to_dict()
    rebuilt = EvidenceGraph.from_dict(payload)

    assert rebuilt.to_dict() == payload


def test_brand_research_pack_can_be_built_from_evidence_graph() -> None:
    graph = build_evidence_graph_from_snapshot(_lab_snapshot())
    pack = build_brand_research_pack_from_graph(graph)
    payload = pack.to_dict()

    assert payload["entity_type"] == "product"
    assert payload["parent_brand"] == "Natura Umana"
    assert any(url.endswith("/mission") for url in payload["official_urls"])
    assert "life orchestration" in payload["offer"].lower()
    assert payload["declared_mission"]
    assert payload["values_signals"]
    assert any("EvidenceGraph summary" in note for note in payload["confidence_notes"])
    assert pack.__class__.from_dict(payload).to_dict() == payload


def test_graph_to_pack_keeps_rejected_noise_out_of_offer() -> None:
    graph = build_evidence_graph_from_snapshot(_bokeroon_snapshot())
    pack = build_brand_research_pack_from_graph(graph)
    payload = pack.to_dict()

    assert "feed" not in payload["offer"].lower()
    assert payload["noise_rejected"]
    assert all(item["kind"] == "noise" for item in payload["noise_rejected"])


def test_graph_pack_matches_legacy_pack_for_core_lab_identity() -> None:
    snapshot = _lab_snapshot()
    legacy = build_brand_research_pack_from_snapshot(snapshot).to_dict()
    graph_pack = build_brand_research_pack_from_graph(
        build_evidence_graph_from_snapshot(snapshot)
    ).to_dict()

    assert graph_pack["entity_type"] == legacy["entity_type"]
    assert graph_pack["parent_brand"] == legacy["parent_brand"]
    assert set(graph_pack["official_urls"]) >= set(legacy["official_urls"])
    assert graph_pack["declared_mission"] == legacy["declared_mission"]
    assert graph_pack["future_direction"] == legacy["future_direction"]
    assert graph_pack["values_signals"]
    assert legacy["values_signals"]


def test_graph_pack_matches_legacy_pack_for_base44_offer_and_context() -> None:
    snapshot = _base44_snapshot()
    legacy = build_brand_research_pack_from_snapshot(snapshot).to_dict()
    graph_pack = build_brand_research_pack_from_graph(
        build_evidence_graph_from_snapshot(snapshot)
    ).to_dict()

    assert "AI app builder" in graph_pack["offer"]
    assert graph_pack["entity_type"] == legacy["entity_type"]
    assert graph_pack["founder_or_press_context"]
    assert any("founder" in item["text"].lower() for item in graph_pack["founder_or_press_context"])
    assert graph_pack["source_map"]


def test_evidence_graph_recovers_low_signal_owned_product_claims() -> None:
    graph = build_evidence_graph_from_snapshot(_sigmaos_like_snapshot())
    pack = build_brand_research_pack_from_graph(graph).to_dict()

    recovered = [claim for claim in graph.to_dict()["claims"] if claim["claim_type"] in {"hero_claim", "product_offer", "outcome"}]
    assert recovered
    assert any(marker in pack["offer"].lower() for marker in ("new home for your internet", "tabs are like tasks"))
    assert any("value_proposition" in claim["supports_blocks"] for claim in recovered)
    assert all("Download Free" not in claim["text"] for claim in recovered)
    assert pack["audience"] == "browser users"


def test_graph_pack_rejects_pricing_labels_as_product_summary() -> None:
    graph = EvidenceGraph(
        version="brand_research_evidence_graph_v0_1",
        run=BrandResearchRun(
            run_id=1006,
            brand_name="Galtea",
            input_url="https://galtea.ai",
            resolved_entity="Galtea",
            entity_type="company",
        ),
        sources={
            "home": ResearchSource(
                source_id="home",
                url="https://galtea.ai",
                source_type="owned_home",
                surface_role="audited_surface",
                entity_scope="audited_surface",
            ),
            "pricing": ResearchSource(
                source_id="pricing",
                url="https://galtea.ai/pricing",
                source_type="owned_pricing",
                surface_role="product:pricing",
                entity_scope="product:plans",
            ),
        },
        claims=[
            EvidenceClaim(
                claim_id="offer",
                text="Galtea is the Quality Assurance platform for companies deploying Generative AI solutions.",
                claim_type="product_offer",
                source_id="home",
                source_url="https://galtea.ai",
                source_type="owned_home",
                surface_role="audited_surface",
                entity_scope="audited_surface",
            ),
            EvidenceClaim(
                claim_id="pricing",
                text="Free Pro Enterprise",
                claim_type="product_offer",
                source_id="pricing",
                source_url="https://galtea.ai/pricing",
                source_type="owned_pricing",
                surface_role="product:pricing",
                entity_scope="product:plans",
            ),
            EvidenceClaim(
                claim_id="pricing-detail",
                text="From solo developers evaluating their first LLM feature to enterprise teams validating AI at scale. Pick the plan that fits your stage.",
                claim_type="product_offer",
                source_id="pricing",
                source_url="https://galtea.ai/pricing",
                source_type="owned_pricing",
                surface_role="product:pricing",
                entity_scope="product:plans",
            ),
            EvidenceClaim(
                claim_id="pricing-billing",
                text="Your evaluations will pause until the next billing cycle. With a Pro or Enterprise plan, you can top up with a credit package at any time without changing your plan.",
                claim_type="product_offer",
                source_id="pricing",
                source_url="https://galtea.ai/pricing",
                source_type="owned_pricing",
                surface_role="product:pricing",
                entity_scope="product:plans",
            ),
            EvidenceClaim(
                claim_id="plan-audience",
                text="Enterprise",
                claim_type="audience",
                source_id="pricing",
                source_url="https://galtea.ai/pricing",
                source_type="owned_pricing",
                surface_role="product:pricing",
                entity_scope="product:plans",
            ),
            EvidenceClaim(
                claim_id="founder-page-audience",
                text="Meet the founders",
                claim_type="audience",
                source_id="home",
                source_url="https://galtea.ai/company/about-us",
                source_type="owned_about",
                surface_role="mission_about",
                entity_scope="audited_surface",
            ),
            EvidenceClaim(
                claim_id="bad-audience",
                text="The unit of evaluation is what users experience, not individual model calls, regardless of how many models, agents, or nodes are running underneath.",
                claim_type="audience",
                source_id="pricing",
                source_url="https://galtea.ai/pricing",
                source_type="owned_pricing",
                surface_role="product:pricing",
                entity_scope="product:plans",
            ),
        ],
    )

    pack = build_brand_research_pack_from_graph(graph).to_dict()

    assert pack["product_summary"] == "Galtea is the Quality Assurance platform for companies deploying Generative AI solutions."
    assert pack["audience"] == "companies deploying generative AI"


def test_graph_pack_rejects_docs_navigation_and_sitemap_as_strategy() -> None:
    graph = EvidenceGraph(
        version="brand_research_evidence_graph_v0_1",
        run=BrandResearchRun(
            run_id=1007,
            brand_name="docs.parallel.ai",
            input_url="https://docs.parallel.ai/getting-started/overview",
            resolved_entity="Parallel",
            entity_type="company",
            parent_brand="Parallel",
        ),
        sources={
            "docs": ResearchSource(
                source_id="docs",
                url="https://docs.parallel.ai/getting-started/overview",
                source_type="owned_docs",
                surface_role="audited_surface",
                entity_scope="audited_surface",
            ),
            "integration": ResearchSource(
                source_id="integration",
                url="https://docs.parallel.ai/integrations/google-gemini-enterprise",
                source_type="owned_docs",
                surface_role="product:docs",
                entity_scope="product:docs",
            ),
            "home": ResearchSource(
                source_id="home",
                url="https://www.parallel.ai",
                source_type="owned_home",
                surface_role="parent_home",
                entity_scope="parent_brand",
            ),
        },
        claims=[
            EvidenceClaim(
                claim_id="chrome-offer",
                text="Overview - Parallel Skip to main content Parallel home page Search... Cmd K Ask Assistant API Playground",
                claim_type="product_offer",
                source_id="docs",
                source_url="https://docs.parallel.ai/getting-started/overview",
                source_type="owned_docs",
                surface_role="audited_surface",
                entity_scope="audited_surface",
            ),
            EvidenceClaim(
                claim_id="sitemap-audience",
                text="<loc>https://docs.parallel.ai/integrations/google-gemini-enterprise</loc>",
                claim_type="audience",
                source_id="docs",
                source_url="https://docs.parallel.ai/sitemap.xml",
                source_type="owned_docs",
                surface_role="audited_surface",
                entity_scope="audited_surface",
            ),
            EvidenceClaim(
                claim_id="integration-title",
                text="Google Gemini Enterprise",
                claim_type="audience",
                source_id="integration",
                source_url="https://docs.parallel.ai/integrations/google-gemini-enterprise",
                source_type="owned_docs",
                surface_role="product:docs",
                entity_scope="product:docs",
            ),
            EvidenceClaim(
                claim_id="clean-offer",
                text="Parallel's web APIs give AI agents and developers high-quality, low-latency access to the web.",
                claim_type="product_offer",
                source_id="home",
                source_url="https://www.parallel.ai",
                source_type="owned_home",
                surface_role="parent_home",
                entity_scope="parent_brand",
            ),
        ],
    )

    pack = build_brand_research_pack_from_graph(graph).to_dict()

    assert pack["offer"] == "Parallel's web APIs give AI agents and developers high-quality, low-latency access to the web."
    assert pack["audience"] == "AI builders and developers"
    assert "Skip to main content" not in pack["offer"]
    assert "Google Gemini Enterprise" not in pack["audience"]


def test_graph_pack_strips_cta_tail_from_offer() -> None:
    graph = EvidenceGraph(
        version="brand_research_evidence_graph_v0_1",
        run=BrandResearchRun(
            run_id=1008,
            brand_name="Publicit",
            input_url="https://www.publicit.com",
            resolved_entity="Publicit",
            entity_type="company",
        ),
        sources={
            "home": ResearchSource(
                source_id="home",
                url="https://www.publicit.com",
                source_type="owned_home",
                surface_role="audited_surface",
                entity_scope="audited_surface",
            )
        },
        claims=[
            EvidenceClaim(
                claim_id="offer",
                text=(
                    "Plataforma de Publicidad Omnicanal Self-Service La primera infraestructura self-service "
                    "para lanzar campanas en todos los espacios publicitarios Unete a Publicit Quieres unirte"
                ),
                claim_type="product_offer",
                source_id="home",
                source_url="https://www.publicit.com",
                source_type="owned_home",
                surface_role="audited_surface",
                entity_scope="audited_surface",
            )
        ],
    )

    pack = build_brand_research_pack_from_graph(graph).to_dict()

    assert pack["offer"].endswith("espacios publicitarios")
    assert "Unete a" not in pack["offer"]
    assert "Quieres unirte" not in pack["offer"]


def test_company_brand_pack_prefers_parent_offer_over_single_product_copy() -> None:
    graph = build_evidence_graph_from_snapshot(_langchain_like_snapshot())
    pack = build_brand_research_pack_from_graph(graph).to_dict()

    assert pack["entity_type"] == "company"
    assert pack["parent_brand"] == ""
    assert pack["category"] == "agent engineering platform"
    assert "LangChain provides the agent engineering platform" in pack["offer"]
    assert "LangSmith Agent Engineering Platform" not in pack["offer"]
    assert pack["product_summary"]
    assert "LangSmith" in pack["product_summary"] or "LangGraph" in pack["product_summary"]


def test_evidence_graph_quarantines_external_near_name_entity_collisions() -> None:
    graph = build_evidence_graph_from_snapshot(_publicit_collision_snapshot())
    payload = graph.to_dict()
    pack = build_brand_research_pack_from_graph(graph).to_dict()

    publicis_sources = [
        source
        for source in payload["sources"].values()
        if "publicis" in source["url"].lower() or "publicis" in source["title"].lower()
    ]
    assert publicis_sources
    assert all(source["source_type"] == "noise" for source in publicis_sources)
    assert all(
        any(note.startswith("entity_boundary_collision") for note in source["notes"])
        for source in publicis_sources
    )
    assert any(warning.startswith("entity_boundary_collision") for warning in payload["warnings"])

    publicis_claims = [claim for claim in payload["claims"] if "publicis" in claim["text"].lower()]
    assert publicis_claims
    assert all(claim["claim_type"] == "noise" for claim in publicis_claims)
    assert all(claim["noise_reason"] == "entity_boundary_collision" for claim in publicis_claims)
    assert all(not claim["supports_blocks"] for claim in publicis_claims)

    assert "Publicit launch" in " ".join(item["text"] for item in pack["founder_or_press_context"])
    assert "Publicis" not in pack["offer"]
    assert "Publicis" not in " ".join(item["text"] for item in pack["proof_points"])
    assert "Publicis" in " ".join(item["text"] for item in pack["noise_rejected"])
    assert any(note.startswith("entity_boundary_collision") for note in pack["confidence_notes"])


def test_evidence_graph_quarantines_sigmaos_sigma_family_collisions() -> None:
    graph = build_evidence_graph_from_snapshot(_sigmaos_collision_snapshot())
    payload = graph.to_dict()
    pack = build_brand_research_pack_from_graph(graph).to_dict()

    sigma_software_sources = [
        source
        for source in payload["sources"].values()
        if "sigma.software" in source["url"].lower()
    ]
    assert sigma_software_sources
    assert all(source["source_type"] == "noise" for source in sigma_software_sources)
    assert any(warning.startswith("entity_boundary_collision") for warning in payload["warnings"])

    sigma_software_claims = [
        claim
        for claim in payload["claims"]
        if "sigma software" in claim["text"].lower()
    ]
    assert sigma_software_claims
    assert all(claim["claim_type"] == "noise" for claim in sigma_software_claims)
    assert all(not claim["supports_blocks"] for claim in sigma_software_claims)

    assert "browser" in pack["offer"].lower() or "internet" in pack["offer"].lower()
    assert "Sigma Software" not in pack["offer"]
    assert "Sigma Software" in " ".join(item["text"] for item in pack["noise_rejected"])


def test_competitor_sources_remain_competitive_context_not_brand_noise() -> None:
    snapshot = _sigmaos_collision_snapshot()
    exa_payload = snapshot["raw_inputs"][1]["payload"]
    exa_payload["mentions"] = []
    exa_payload["competitors"] = [
        {
            "url": "https://browseros.com/",
            "title": "BrowserOS",
            "summary": "BrowserOS is an alternative browser project.",
        }
    ]

    graph = build_evidence_graph_from_snapshot(snapshot)
    pack = build_brand_research_pack_from_graph(graph).to_dict()

    competitor_sources = [
        source for source in graph.to_dict()["sources"].values() if source["url"] == "https://browseros.com"
    ]
    assert competitor_sources
    assert competitor_sources[0]["source_type"] == "competitor_context"
    assert pack["competitive_context"]
    assert pack["competitive_context"][0]["source_type"] == "competitive_context"
    assert pack["competitive_context"][0]["kind"] == "context"
    assert "BrowserOS" in pack["competitive_context"][0]["text"]
    assert "BrowserOS" not in pack["offer"]
    assert "BrowserOS" not in " ".join(item["text"] for item in pack["noise_rejected"])
