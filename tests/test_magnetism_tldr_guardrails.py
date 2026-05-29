from __future__ import annotations

from src.features.magnetism.tldr_guardrails import validate_analyst_tldr


def _base_pack() -> dict:
    return {
        "version": "brand_research_pack_v0_1",
        "input_url": "https://base44.com",
        "resolved_entity": {
            "resolved_entity": "Base44",
            "entity_type": "company",
            "canonical_url": "https://base44.com",
            "parent_brand": "",
            "surface_role": "homepage",
            "entity_scope": "owned",
            "confidence": "high",
            "notes": [],
        },
        "entity_type": "company",
        "parent_brand": "",
        "official_urls": ["https://base44.com"],
        "analyzed_urls": ["https://base44.com"],
        "source_map": {
            "https://base44.com": {
                "url": "https://base44.com",
                "source_type": "owned_official",
                "label": "Base44",
                "surface_role": "homepage",
                "entity_scope": "company",
                "title": "Base44",
                "notes": [],
            },
            "https://base44.com/about": {
                "url": "https://base44.com/about",
                "source_type": "press_or_founder",
                "label": "About",
                "surface_role": "about",
                "entity_scope": "company",
                "title": "About Base44",
                "notes": [],
            },
        },
        "company_summary": "Base44 is an AI app builder for non-technical founders.",
        "product_summary": "Base44 is an AI app builder for non-technical founders.",
        "audience": "non-technical founders",
        "offer": "Base44 is an AI app builder for non-technical founders.",
        "outcome": "Build and ship apps fast.",
        "category": "AI app builder",
        "declared_purpose": "Base44 is an AI app builder for non-technical founders.",
        "declared_mission": "We are on a mission to help teams ship software.",
        "future_direction": "Build and ship apps fast.",
        "tone_of_voice": "direct",
        "personality_signals": ["direct", "pragmatic"],
        "visual_or_conceptual_signals": ["simple app building"],
        "values_signals": ["speed", "simplicity"],
        "attributes_signals": ["AI-first", "fast"],
        "proof_points": [
            {
                "text": "Trusted by founders and small teams.",
                "kind": "proof",
                "source_url": "https://base44.com",
                "source_type": "owned_official",
                "source_label": "Base44",
                "surface_role": "homepage",
                "entity_scope": "company",
                "topic": "proof_point",
                "confidence": "high",
                "notes": [],
            }
        ],
        "founder_or_press_context": [
            {
                "text": "Our founder exited a previous startup and built Base44 to make app creation simple.",
                "kind": "context",
                "source_url": "https://base44.com/about",
                "source_type": "press_or_founder",
                "source_label": "About Base44",
                "surface_role": "about",
                "entity_scope": "company",
                "topic": "founder_or_press",
                "confidence": "medium",
                "notes": [],
            }
        ],
        "noise_rejected": [
            {
                "text": "Main Menu",
                "kind": "noise",
                "source_url": "https://base44.com",
                "source_type": "noise",
                "source_label": "Homepage chrome",
                "surface_role": "homepage",
                "entity_scope": "company",
                "topic": "page chrome",
                "confidence": "low",
                "notes": [],
            }
        ],
        "evidence_gaps": [],
        "confidence_notes": ["Owned homepage evidence is strong."],
    }


def test_founder_story_cannot_be_declared_personality() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "personality": {
                    "answer": "The founder story makes Base44 feel bold and visionary.",
                    "claim_type": "declared",
                    "mode": "literal",
                    "confidence": "high",
                    "evidence_used": [
                        "Our founder exited a previous startup and built Base44 to make app creation simple."
                    ],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["personality"]
    assert block["claim_type"] == "inferred"
    assert block["mode"] in {"interpreted_from_discourse", "needs_human_review"}
    assert block["confidence"] in {"medium", "low"}
    assert block["human_review_recommended"] is True
    assert validated["validation_warnings"]
    assert validated["degraded_fields"]


def test_feed_prediction_cannot_be_vision() -> None:
    pack = _base_pack()
    pack["input_url"] = "https://bokeroon.com"
    pack["resolved_entity"]["resolved_entity"] = "Bokeroon"
    pack["source_map"]["https://bokeroon.com/feed"] = {
        "url": "https://bokeroon.com/feed",
        "source_type": "noise",
        "label": "Feed",
        "surface_role": "feed",
        "entity_scope": "content",
        "title": "Feed",
        "notes": [],
    }
    pack["noise_rejected"] = [
        {
            "text": "Article prediction: the page lists forward-looking content and menu chrome.",
            "kind": "noise",
            "source_url": "https://bokeroon.com/feed",
            "source_type": "noise",
            "source_label": "Feed",
            "surface_role": "feed",
            "entity_scope": "content",
            "topic": "page chrome",
            "confidence": "low",
            "notes": [],
        }
    ]

    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "vision": {
                    "answer": "The feed predicts a future category shift.",
                    "claim_type": "inferred",
                    "mode": "interpreted_from_discourse",
                    "confidence": "high",
                    "evidence_used": ["Article prediction: the page lists forward-looking content and menu chrome."],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["vision"]
    assert block["detected"] is False
    assert block["claim_type"] == "absent"
    assert block["mode"] == "not_detected"
    assert block["confidence"] == "low"


def test_press_context_cannot_be_declared_mission() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "mission": {
                    "answer": "To help teams ship software.",
                    "claim_type": "declared",
                    "mode": "literal",
                    "confidence": "high",
                    "evidence_used": [
                        "Our founder exited a previous startup and built Base44 to make app creation simple."
                    ],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["mission"]
    assert block["claim_type"] == "inferred"
    assert block["mode"] in {"interpreted_from_discourse", "needs_human_review"}
    assert block["human_review_recommended"] is True
    assert any("mission" in warning for warning in validated["validation_warnings"])


def test_answer_without_evidence_degrades_to_absent() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "Base44 is a productivity platform.",
                    "claim_type": "inferred",
                    "mode": "interpreted_from_discourse",
                    "confidence": "high",
                    "evidence_used": [],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["value_proposition"]
    assert block["claim_type"] == "absent"
    assert block["mode"] == "not_detected"
    assert block["answer"] is None
    assert block["detected"] is False


def test_high_inferred_claim_without_strong_support_loses_confidence() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "Base44 is an AI app builder for non-technical founders.",
                    "claim_type": "inferred",
                    "mode": "interpreted_from_discourse",
                    "confidence": "high",
                    "evidence_used": ["Trusted by founders and small teams."],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["value_proposition"]
    assert block["confidence"] in {"medium", "low"}
    assert block["confidence"] != "high"
    assert block["human_review_recommended"] is True


def test_page_chrome_invalidates_value_proposition() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "Main Menu / Header / Footer",
                    "claim_type": "inferred",
                    "mode": "interpreted_from_discourse",
                    "confidence": "medium",
                    "evidence_used": ["Main Menu"],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["value_proposition"]
    assert block["claim_type"] == "absent"
    assert block["mode"] == "not_detected"
    assert block["detected"] is False
    assert any("value_proposition" in warning for warning in validated["validation_warnings"])
