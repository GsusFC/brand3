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


def test_personality_answer_snaps_to_signal_candidates() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "personality": {
                    "answer": "Direct and pragmatic builder energy.",
                    "claim_type": "performed",
                    "mode": "interpreted_from_discourse",
                    "confidence": "medium",
                    "evidence_used": ["direct"],
                    "evidence_sources": [{"source_key": "https://base44.com", "source_type": "owned_official"}],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["personality"]
    assert block["answer"] == "direct, pragmatic"


def test_evidence_sources_snap_to_shortlist_source() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "An AI app builder for non-technical founders.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "evidence_used": ["AI app builder for non-technical founders."],
                    "evidence_sources": [{"source_key": "input_url", "source_type": "owned_official"}],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["value_proposition"]
    assert block["evidence_sources"][0]["source_key"] == "https://base44.com"
    assert block["evidence_sources"][0]["url"] == "https://base44.com"


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


def test_attributes_answer_is_canonicalized_and_reasoning_is_deterministic() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "attributes": {
                    "answer": "Specialized, Analytical, Pragmatic",
                    "claim_type": "inferred",
                    "mode": "needs_human_review",
                    "confidence": "high",
                    "reasoning": "Freeform LLM explanation that should not survive as-is.",
                    "evidence_used": [
                        "Consultora boutique especialista",
                        "Traduce a euros el impacto",
                    ],
                    "evidence_sources": [
                        {"source_key": "https://base44.com", "source_type": "owned_official"},
                    ],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["attributes"]
    assert block["answer"] == "Analytical, Pragmatic, Specialized"
    assert block["reasoning"] == block["rationale"]
    assert block["reasoning"].startswith("Inferred attributes reading in needs_human_review mode")


def test_attributes_list_like_answer_is_cleaned_and_sorted() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "attributes": {
                    "answer": "['Fast'], 'Simple', ['Developer-first']",
                    "claim_type": "performed",
                    "mode": "interpreted_from_discourse",
                    "confidence": "medium",
                    "evidence_used": [
                        "6× faster to build + deploy.",
                        "Shipping an agent should be as simple as shipping a site.",
                    ],
                }
            }
        },
        pack,
    )

    assert validated["tldr_brand3"]["attributes"]["answer"] == "Developer-first, Fast, Simple"


def test_evidence_sources_are_canonicalized_with_url_and_sorted() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "mission": {
                    "answer": "We are on a mission to help teams ship software.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "evidence_used": ["We are on a mission to help teams ship software."],
                    "evidence_sources": [
                        {"source_key": "https://base44.com/about", "source_type": "press_or_founder"},
                        {"source_key": "https://base44.com", "source_type": "owned_official"},
                    ],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["mission"]
    assert block["evidence_sources"][0]["source_key"] == "https://base44.com"
    assert block["evidence_sources"][0]["url"] == "https://base44.com"
    assert block["evidence_sources"][1]["label"] == "About"


def test_evidence_sources_normalize_trailing_slash_and_generic_label() -> None:
    pack = _base_pack()
    pack["source_map"]["https://base44.com"]["label"] = "input_url"
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "brand_idea": {
                    "answer": "A clear idea.",
                    "claim_type": "inferred",
                    "mode": "interpreted_from_discourse",
                    "confidence": "medium",
                    "evidence_used": ["Base44 is an AI app builder for non-technical founders."],
                    "evidence_sources": [
                        {"source_key": "https://base44.com/", "source_type": "owned_official"},
                    ],
                }
            }
        },
        pack,
    )

    source = validated["tldr_brand3"]["brand_idea"]["evidence_sources"][0]
    assert source["source_key"] == "https://base44.com"
    assert source["url"] == "https://base44.com"
    assert source["label"] == ""


def test_evidence_used_snaps_to_block_shortlist_when_matching() -> None:
    pack = _base_pack()
    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "AI app builder for founders.",
                    "claim_type": "declared",
                    "mode": "compressed",
                    "confidence": "high",
                    "evidence_used": ["AI app builder for non-technical founders."],
                }
            }
        },
        pack,
    )

    assert validated["tldr_brand3"]["value_proposition"]["evidence_used"] == [
        "Base44 is an AI app builder for non-technical founders."
    ]


def test_core_purpose_absent_when_only_functional_offer_language_exists() -> None:
    pack = _base_pack()
    pack["declared_purpose"] = ""
    pack["company_summary"] = (
        "Pleo helps businesses manage spending with company cards and expense software."
    )
    pack["product_summary"] = (
        "Company cards and expense software that automate spend management."
    )

    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "core_purpose": {
                    "answer": "Pleo exists to transform the way businesses manage their spending.",
                    "claim_type": "inferred",
                    "mode": "interpreted_from_discourse",
                    "confidence": "medium",
                    "evidence_used": [
                        "Pleo helps businesses manage spending with company cards and expense software."
                    ],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["core_purpose"]
    assert block["detected"] is False
    assert block["claim_type"] == "absent"
    assert block["mode"] == "not_detected"


def test_values_absent_without_canonical_value_signals() -> None:
    pack = _base_pack()
    pack["values_signals"] = []
    pack["declared_purpose"] = ""
    pack["proof_points"] = [
        {
            "text": "98% of users say they feel secure using the product.",
            "kind": "proof",
            "source_url": "https://base44.com",
            "source_type": "proof_point",
            "source_label": "Proof",
            "surface_role": "homepage",
            "entity_scope": "company",
            "topic": "proof_point",
            "confidence": "high",
            "notes": [],
        }
    ]

    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "values": {
                    "answer": "Security",
                    "claim_type": "performed",
                    "mode": "needs_human_review",
                    "confidence": "medium",
                    "evidence_used": [
                        "98% of users say they feel secure using the product."
                    ],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["values"]
    assert block["detected"] is False
    assert block["claim_type"] == "absent"
    assert block["mode"] == "not_detected"


def test_values_absent_when_only_mission_literal_support_exists() -> None:
    pack = _base_pack()
    pack["values_signals"] = []
    pack["declared_mission"] = (
        "At Vercel, our mission is to enable developers to build and publish wonderful, high-performant apps and websites."
    )

    validated = validate_analyst_tldr(
        {
            "tldr_brand3": {
                "values": {
                    "answer": "Developer empowerment and high performance.",
                    "claim_type": "performed",
                    "mode": "interpreted_from_discourse",
                    "confidence": "high",
                    "evidence_used": [
                        "At Vercel, our mission is to enable developers to build and publish wonderful, high-performant apps and websites."
                    ],
                }
            }
        },
        pack,
    )

    block = validated["tldr_brand3"]["values"]
    assert block["detected"] is False
    assert block["claim_type"] == "absent"
    assert block["mode"] == "not_detected"
