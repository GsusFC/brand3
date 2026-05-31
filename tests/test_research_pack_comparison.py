from __future__ import annotations

from src.research.pack_comparison import compare_pack_builders_from_snapshot


def test_pack_comparison_reports_graph_gains_for_low_signal_product_copy() -> None:
    snapshot = {
        "run": {"id": 2001, "brand_name": "SigmaOS", "url": "https://sigmaos.com"},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://sigmaos.com",
                    "markdown_content": (
                        "A smarter way to browse the internet.\n"
                        "The new home for your internet. One window. Many workspaces. All your tabs.\n"
                        "Your tabs are like tasks in a to-do list. Mark them as done once they're complete.\n"
                        "Download Free\n"
                    ),
                },
            }
        ],
        "features": [],
        "evidence_items": [],
    }

    comparison = compare_pack_builders_from_snapshot(snapshot)
    payload = comparison.to_dict()

    assert payload["run_id"] == 2001
    assert payload["graph_summary"]["claim_count"] > 0
    assert "offer" in payload["summary"]["changed_fields"]
    offer = next(field for field in payload["fields"] if field["field"] == "offer")
    assert not offer["graph_empty"]
    assert "internet" in offer["graph_preview"].lower() or "tabs" in offer["graph_preview"].lower()


def test_pack_comparison_keeps_identity_fields_visible() -> None:
    snapshot = {
        "run": {"id": 2002, "brand_name": "tinyNature", "url": "https://lab.naturaumana.ai"},
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "canonical_url": "https://lab.naturaumana.ai",
                    "markdown_content": "tinyNature is a personal AI assistant platform for life orchestration.",
                },
            },
            {
                "source": "entity_research_packet",
                "payload": {
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

    comparison = compare_pack_builders_from_snapshot(snapshot)

    assert comparison.legacy_entity_type == "product"
    assert comparison.graph_entity_type == "product"
    assert comparison.legacy_parent_brand == "Natura Umana"
    assert comparison.graph_parent_brand == "Natura Umana"
