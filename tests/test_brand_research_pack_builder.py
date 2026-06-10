from __future__ import annotations

import json
from pathlib import Path

from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot
from src.research.evidence_graph import build_evidence_graph_from_snapshot
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
                "source": "context",
                "payload": {
                    "url": "https://base44.com",
                    "homepage_status": 200,
                    "schema_types": ["Organization"],
                },
            },
            {
                "source": "entity_research_packet",
                "payload": {
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


def _parallel_shadow_raw_input() -> dict:
    return {
        "source": "parallel_shadow",
        "payload": {
            "version": "parallel_shadow_v0_1",
            "provider": "parallel",
            "mode": "advanced",
            "status": "ok",
            "summary": {
                "result_total": 2,
                "unique_domain_count": 2,
                "unique_domains": ["g2.com", "reddit.com"],
            },
            "intents": {
                "mentions": {
                    "status": "ok",
                    "result_count": 2,
                    "unique_domains": ["g2.com", "reddit.com"],
                    "results": [
                        {
                            "url": "https://g2.com/products/base44/reviews",
                            "title": "Base44 Reviews",
                            "excerpt": "Third-party review shadow signal.",
                        }
                    ],
                }
            },
        },
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
                    "limitations": ["No parent owned surfaces were available beyond the audited URL."],
                },
            },
        ],
        "features": [],
        "evidence_items": [],
    }


def test_brand_research_pack_builder_reads_base44_offer_and_founder_context() -> None:
    pack = build_brand_research_pack_from_snapshot(_base44_snapshot())
    payload = pack.to_dict()

    assert "AI app builder" in payload["offer"]
    assert "AI app builder" in payload["product_summary"]
    assert any("founder exit" in item["text"].lower() for item in payload["founder_or_press_context"])
    assert all("founder exit" not in signal.lower() for signal in payload["personality_signals"])
    assert payload["resolved_entity"]["entity_type"] == "company"
    assert payload["resolved_entity"]["confidence"] in {"low", "medium", "high"}
    assert any(item["source_url"] for item in payload["proof_points"])


def test_brand_research_pack_builder_rejects_bokeroon_feed_and_chrome_as_noise() -> None:
    pack = build_brand_research_pack_from_snapshot(_bokeroon_snapshot())
    payload = pack.to_dict()

    assert "article prediction" not in payload["offer"].lower()
    assert "feed" not in payload["product_summary"].lower()
    assert payload["category"] == "platform"
    assert any("feed" in item["text"].lower() or "page chrome" in item["topic"].lower() for item in payload["noise_rejected"])
    assert all(item["kind"] == "noise" for item in payload["noise_rejected"])


def test_brand_research_pack_builder_marks_lab_parent_context() -> None:
    pack = build_brand_research_pack_from_snapshot(_lab_snapshot())
    payload = pack.to_dict()

    assert payload["entity_type"] in {"product", "sub_brand"}
    assert payload["parent_brand"] == "Natura Umana"
    assert any("parent brand" in note.lower() for note in payload["confidence_notes"])
    assert "life orchestration" in payload["product_summary"].lower()
    assert any(url.endswith("/mission") for url in payload["official_urls"])
    assert all(item["source_url"] for item in payload["proof_points"] + payload["founder_or_press_context"] + payload["noise_rejected"])


def test_brand_research_pack_builder_roundtrips_and_preserves_source_map() -> None:
    pack = build_brand_research_pack_from_snapshot(_lab_snapshot())
    payload = pack.to_dict()
    rebuilt = pack.__class__.from_dict(payload)

    assert rebuilt.to_dict() == payload
    assert payload["source_map"]
    assert all(source["source_type"] for source in payload["source_map"].values())


def test_brand_research_pack_records_parallel_shadow_without_promoting_to_evidence() -> None:
    snapshot = _base44_snapshot()
    snapshot["raw_inputs"].append(_parallel_shadow_raw_input())

    pack = build_brand_research_pack_from_snapshot(snapshot)
    payload = pack.to_dict()

    assert payload["shadow_sources"][0]["provider"] == "parallel"
    assert payload["shadow_sources"][0]["result_total"] == 2
    assert payload["shadow_sources"][0]["intents"]["mentions"]["results"][0]["url"] == (
        "https://g2.com/products/base44/reviews"
    )
    assert "g2.com" not in " ".join(payload["source_map"].keys())
    assert not any("Third-party review shadow signal" in item["text"] for item in payload["proof_points"])
    assert pack.__class__.from_dict(payload).to_dict() == payload


def test_evidence_graph_pack_carries_parallel_shadow_as_metadata_only() -> None:
    snapshot = _base44_snapshot()
    snapshot["raw_inputs"].append(_parallel_shadow_raw_input())

    graph = build_evidence_graph_from_snapshot(snapshot)
    pack = build_brand_research_pack_from_graph(graph)
    payload = pack.to_dict()

    assert graph.summary()["shadow_source_count"] == 1
    assert payload["shadow_sources"][0]["provider"] == "parallel"
    assert payload["shadow_sources"][0]["intents"]["mentions"]["results"][0]["title"] == "Base44 Reviews"
    assert not any(source.origin == "parallel_shadow" for source in graph.sources.values())


def test_brand_research_pack_builder_example_json_written() -> None:
    example_path = Path("examples/reports/brand_research_pack/base44.brand_research_pack.v0.json")
    assert example_path.exists()
    payload = json.loads(example_path.read_text(encoding="utf-8"))
    assert payload["version"] == "brand_research_pack_v0_1"
