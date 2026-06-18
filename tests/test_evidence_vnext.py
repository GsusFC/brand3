from __future__ import annotations

from src.research.evidence_vnext import (
    EvidenceVNextPacket,
    SourceObservation,
    apply_evidence_vnext_acquisition_contracts,
    build_evidence_vnext_semantic_assessment,
    build_evidence_vnext_packet_from_snapshot,
    build_vnext_brand_research_pack_from_snapshot,
    build_vnext_evidence_graph_from_snapshot,
    compare_evidence_vnext_from_snapshot,
    compare_legacy_current_and_vnext_from_snapshot,
)
from src.research.evidence_vnext_report import build_batch_report, render_batch_report_markdown


def _ambiguous_exa_snapshot() -> dict:
    return {
        "run": {
            "id": 4101,
            "brand_name": "Publicit",
            "url": "https://www.publicit.com",
        },
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
                            "url": "https://www.publicisgroupe.com/news/microsoft-publicis",
                            "title": "Microsoft and Publicis Groupe expand media partnership",
                            "summary": "Publicis Media announces a global advertising collaboration.",
                            "source_class": "related_unresolved",
                            "relation": "unresolved",
                            "classification_reason": "same_name_different_root_domain",
                            "requires_human_review": True,
                        }
                    ],
                    "competitors": [],
                    "ai_visibility_results": [],
                    "news": [],
                },
            },
        ],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "brand_sentiment",
                "value": 0.5,
                "raw_value": (
                    "{'evidence': [{'quote': 'Publicis Media announces a global advertising collaboration.', "
                    "'source_url': 'https://www.publicisgroupe.com/news/microsoft-publicis'}]}"
                ),
                "confidence": 0.7,
                "source": "exa",
            },
            {
                "dimension_name": "presencia",
                "feature_name": "context_readiness",
                "value": 0.5,
                "raw_value": "{'evidence_url': 'https://www.publicit.com/robots.txt'}",
                "confidence": 0.7,
                "source": "context",
            },
        ],
        "evidence_items": [],
    }


def _exa_empty_text_contract_snapshot() -> dict:
    return {
        "run": {
            "id": 4109,
            "brand_name": "SignalDesk",
            "url": "https://www.signaldesk.test",
        },
        "raw_inputs": [
            {
                "source": "exa",
                "payload": {
                    "mentions": [
                        {
                            "url": "https://empty.example.com/signaldesk",
                            "title": "",
                            "summary": "",
                            "text": "",
                        },
                        {
                            "url": "https://press.example.com/signaldesk-launch",
                            "title": "SignalDesk launches for B2B teams",
                            "summary": "SignalDesk helps operators coordinate revenue workflows.",
                        },
                    ],
                    "competitors": [],
                    "ai_visibility_results": [],
                    "news": [],
                },
            },
        ],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "press_signal",
                "value": 0.7,
                "raw_value": {
                    "evidence": [
                        {
                            "source_url": "https://empty.example.com/signaldesk",
                            "quote": "",
                        },
                        {
                            "source_url": "https://press.example.com/signaldesk-launch",
                            "quote": "SignalDesk helps operators coordinate revenue workflows.",
                        },
                    ]
                },
                "confidence": 0.7,
                "source": "exa",
            }
        ],
        "evidence_items": [],
    }


def _split_snippet_url_snapshot() -> dict:
    return {
        "run": {
            "id": 4102,
            "brand_name": "Publicit",
            "url": "https://www.publicit.com",
        },
        "raw_inputs": [],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "press_signal",
                "value": 0.8,
                "raw_value": (
                    "{'evidence_snippet': 'Publicit announced a verified agency partner program.', "
                    "'evidence_url': 'https://news.example.com/publicit-partner-program'}"
                ),
                "confidence": 0.8,
                "source": "exa",
            },
        ],
        "evidence_items": [],
    }


def _derived_feature_without_url_snapshot() -> dict:
    quote = "Publicit gives operators a campaign planning workspace with tracked creative results."
    return {
        "run": {
            "id": 4103,
            "brand_name": "Publicit",
            "url": "https://www.publicit.com",
        },
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://www.publicit.com/about",
                    "title": "About Publicit",
                    "markdown_content": f"About Publicit\n\n{quote}\n\nBuilt for local operators.",
                },
            }
        ],
        "features": [
            {
                "dimension_name": "diferenciacion",
                "feature_name": "positioning_clarity",
                "value": 0.8,
                "raw_value": repr({"evidence": [{"quote": quote, "signal": "clear"}]}),
                "confidence": 0.8,
                "source": "llm",
            },
        ],
        "evidence_items": [],
    }


def _formatted_and_fragmented_source_snapshot() -> dict:
    return {
        "run": {
            "id": 4105,
            "brand_name": "Instantly",
            "url": "https://instantly.ai",
        },
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://instantly.ai",
                    "title": "Instantly",
                    "markdown_content": (
                        "Customer proof includes 2X Faster-to-start campaign across outbound teams.\n"
                        "Pricing section: # Simple Pricing for Everyone\n"
                        "**Copilot** is Instantly’s built-in AI assistant designed specifically for cold email and outbound workflows."
                    ),
                },
            },
            {
                "source": "web",
                "payload": {
                    "url": "https://instantly.ai/copilot",
                    "title": "Copilot",
                    "markdown_content": (
                        "Copilot is Instantly’s built-in AI assistant designed specifically for cold email and outbound workflows."
                    ),
                },
            },
        ],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "tone_consistency",
                "value": 0.8,
                "raw_value": repr(
                    {
                        "evidence": [
                            {"quote": "Faster-to-start campaign, Simple Pricing for Everyone"},
                            {
                                "quote": (
                                    "Copilot is Instantly’s built-in AI assistant designed specifically for "
                                    "cold email and outbound workflows."
                                )
                            },
                        ]
                    }
                ),
                "confidence": 0.8,
                "source": "llm",
            },
        ],
        "evidence_items": [],
    }


def _internal_analysis_without_url_snapshot() -> dict:
    return {
        "run": {
            "id": 4104,
            "brand_name": "Publicit",
            "url": "https://www.publicit.com",
        },
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://www.publicit.com",
                    "title": "Publicit",
                    "markdown_content": "Publicit is an advertising automation platform.",
                },
            }
        ],
        "features": [
            {
                "dimension_name": "diferenciacion",
                "feature_name": "content_authenticity",
                "value": 0.6,
                "raw_value": repr(
                    {
                        "authenticity_verdict": "mixed",
                        "evidence_snippets": [
                            "The layout feels like a polished template rather than distinct market proof."
                        ],
                    }
                ),
                "confidence": 0.7,
                "source": "content_analysis",
            },
        ],
        "evidence_items": [],
    }


def _exa_external_visual_product_evidence_snapshot() -> dict:
    return {
        "run": {
            "id": 4110,
            "brand_name": "Figma",
            "url": "https://www.figma.com",
        },
        "raw_inputs": [
            {
                "source": "exa",
                "payload": {
                    "mentions": [
                        {
                            "url": "https://www.gartner.com/reviews/product/figma-design",
                            "title": "Figma Design Reviews",
                            "summary": "Figma Design reviews describe collaborative visual design workflows.",
                            "source_class": "external",
                            "relation": "external",
                            "classification_reason": "external_candidate",
                        }
                    ],
                    "competitors": [],
                    "ai_visibility_results": [],
                    "news": [],
                },
            }
        ],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "search_visibility",
                "value": 0.7,
                "raw_value": repr(
                    {
                        "evidence": [
                            {
                                "quote": "Figma Design reviews describe collaborative visual design workflows.",
                                "source_url": "https://www.gartner.com/reviews/product/figma-design",
                            }
                        ]
                    }
                ),
                "confidence": 0.7,
                "source": "exa",
            },
        ],
        "evidence_items": [],
    }


def _exa_semantic_materiality_snapshot() -> dict:
    return {
        "run": {
            "id": 4111,
            "brand_name": "Canva",
            "url": "https://www.canva.com",
        },
        "raw_inputs": [
            {
                "source": "exa",
                "payload": {
                    "mentions": [
                        {
                            "url": "https://www.enterpret.com/customers/canva",
                            "title": "Case Study: How Canva leverages Enterpret",
                            "summary": "Case Study: How Canva leverages Enterpret to build products that delight users.",
                            "source_class": "external",
                            "relation": "external",
                            "classification_reason": "external_candidate",
                        },
                        {
                            "url": "https://www.guideflow.com/blog/ai-design-tools",
                            "title": "15 best AI design tools in 2026 compared",
                            "summary": "A comparison of AI design tools, Canva alternatives, and visual design workflows.",
                            "source_class": "external",
                            "relation": "external",
                            "classification_reason": "external_candidate",
                        },
                    ],
                    "competitors": [],
                    "ai_visibility_results": [],
                    "news": [],
                },
            }
        ],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "search_visibility",
                "value": 0.7,
                "raw_value": repr(
                    {
                        "evidence": [
                            {
                                "quote": "Case Study: How Canva leverages Enterpret to build products that delight users.",
                                "source_url": "https://www.enterpret.com/customers/canva",
                            },
                            {
                                "quote": "A comparison of AI design tools, Canva alternatives, and visual design workflows.",
                                "source_url": "https://www.guideflow.com/blog/ai-design-tools",
                            },
                        ]
                    }
                ),
                "confidence": 0.7,
                "source": "exa",
            },
        ],
        "evidence_items": [],
    }


def _covered_by_accepted_source_snapshot() -> dict:
    first = "Archetype is an early-stage venture firm focused on accelerating the decentralized future."
    second = "We back the next generation of crypto founders who are disrupting the status quo."
    return {
        "run": {
            "id": 4106,
            "brand_name": "Archetype",
            "url": "https://www.archetype.fund",
        },
        "raw_inputs": [],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "brand_sentiment",
                "value": 0.8,
                "raw_value": repr(
                    {
                        "evidence": [
                            {"quote": first, "source_url": "https://www.archetype.fund/about"},
                            {"quote": second, "source_url": "https://www.archetype.fund/about"},
                        ]
                    }
                ),
                "confidence": 0.8,
                "source": "web",
            },
            {
                "dimension_name": "diferenciacion",
                "feature_name": "tone_consistency",
                "value": 0.8,
                "raw_value": repr({"evidence": [{"quote": f"{first} {second}"}]}),
                "confidence": 0.8,
                "source": "llm",
            },
        ],
        "evidence_items": [],
    }


def _audited_source_window_snapshot() -> dict:
    quote = (
        "Build agents fast with any model provider. Choose the right framework for the job "
        "from batteries included to low-level control."
    )
    return {
        "run": {
            "id": 4107,
            "brand_name": "LangChain",
            "url": "https://www.langchain.com",
        },
        "raw_inputs": [
            {
                "source": "web",
                "payload": {
                    "url": "https://www.langchain.com",
                    "title": "LangChain",
                    "markdown_content": (
                        "Launch reliable agents.\n"
                        "Build agents fast with any model provider. Choose the right framework for the job "
                        "from batteries included to low-level control.\n"
                        "Ship with observability."
                    ),
                },
            },
        ],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "tone_consistency",
                "value": 0.8,
                "raw_value": repr({"evidence": [{"quote": quote}]}),
                "confidence": 0.8,
                "source": "llm",
            },
        ],
        "evidence_items": [],
    }


def _ambiguous_exa_window_snapshot() -> dict:
    quote = "Mistral AI is a company that provides open and portable generative AI for developers and businesses."
    return {
        "run": {
            "id": 4108,
            "brand_name": "Mistral AI",
            "url": "https://mistral.ai",
        },
        "raw_inputs": [
            {
                "source": "exa",
                "payload": {
                    "mentions": [
                        {
                            "url": "https://linkedin.com/company/mistralai/",
                            "title": "Mistral AI",
                            "summary": quote,
                        },
                        {
                            "url": "https://mistral.ai/",
                            "title": "Mistral AI",
                            "summary": quote,
                        },
                    ],
                    "competitors": [],
                    "ai_visibility_results": [],
                    "news": [],
                },
            },
        ],
        "features": [
            {
                "dimension_name": "percepcion",
                "feature_name": "tone_consistency",
                "value": 0.8,
                "raw_value": repr({"evidence": [{"quote": quote}]}),
                "confidence": 0.8,
                "source": "llm",
            },
        ],
        "evidence_items": [],
    }


def _unresolved_profile_source_snapshot() -> dict:
    snapshot = _ambiguous_exa_window_snapshot()
    snapshot["features"].append(
        {
            "dimension_name": "presencia",
            "feature_name": "social_footprint",
            "value": 0.5,
            "raw_value": repr(
                {
                    "evidence": [
                        {
                            "quote": "linkedin profile candidate",
                            "source_url": "https://www.linkedin.com/company/mistralai",
                        }
                    ]
                }
            ),
            "confidence": 0.7,
            "source": "social_scrape",
        }
    )
    return snapshot


def test_evidence_vnext_gate_separates_review_and_technical_candidates() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_ambiguous_exa_snapshot())
    payload = packet.to_dict()

    assert payload["runtime_effect"] is False
    assert payload["prompt_effect"] is False
    assert payload["summary"]["review_required_count"] >= 1
    assert payload["summary"]["rejected_count"] >= 1
    assert payload["summary"]["review_reason_counts"]["same_name_different_root_domain"] >= 1
    assert payload["summary"]["rejected_reason_counts"]["technical_context_not_brand_narrative_evidence"] >= 1
    assert any(item["source_class"] == "related_unresolved" for item in payload["review_required"])
    assert any(item["source_class"] == "technical_internal" for item in payload["rejected"])


def test_exa_empty_text_result_is_rejected_before_material_evidence() -> None:
    result = apply_evidence_vnext_acquisition_contracts(_exa_empty_text_contract_snapshot())
    payload = result.to_dict()

    assert payload["runtime_effect"] is False
    assert payload["prompt_effect"] is False
    assert payload["persistence_effect"] is False
    assert payload["summary"]["excluded_count"] == 2
    assert payload["summary"]["exclusion_counts_by_contract"]["exa.non_empty_text"] == 2
    assert payload["summary"]["exclusion_counts_by_surface"]["raw_inputs.exa.mentions"] == 1
    assert payload["summary"]["exclusion_counts_by_surface"]["features.exa.raw_value.evidence"] == 1

    packet = build_evidence_vnext_packet_from_snapshot(result.normalized_snapshot).to_dict()

    assert packet["summary"]["rejected_reason_counts"].get("empty_text_evidence_blocked", 0) == 0
    assert all(item["url"] != "https://empty.example.com/signaldesk" for item in packet["observations"])


def test_exa_non_empty_result_can_still_be_accepted_after_shadow_contract() -> None:
    result = apply_evidence_vnext_acquisition_contracts(_exa_empty_text_contract_snapshot())
    packet = build_evidence_vnext_packet_from_snapshot(result.normalized_snapshot).to_dict()

    accepted = [
        item
        for item in packet["accepted"]
        if item["url"] == "https://press.example.com/signaldesk-launch"
    ]
    assert accepted
    assert accepted[0]["provider"] == "exa"
    assert "coordinate revenue workflows" in accepted[0]["text"]


def test_vnext_graph_quarantines_review_required_exa_claims_but_keeps_owned_offer() -> None:
    graph = build_vnext_evidence_graph_from_snapshot(_ambiguous_exa_snapshot())
    payload = graph.to_dict()

    publicis_claims = [
        claim
        for claim in payload["claims"]
        if "publicisgroupe.com" in claim.get("source_url", "")
    ]
    assert publicis_claims
    assert all(claim["claim_type"] == "noise" for claim in publicis_claims)
    assert any("advertising automation platform" in claim["text"].lower() for claim in payload["claims"])


def test_vnext_pack_remains_usable_from_owned_content() -> None:
    pack = build_vnext_brand_research_pack_from_snapshot(_ambiguous_exa_snapshot()).to_dict()

    assert "advertising automation platform" in pack["offer"].lower()
    assert "publicis" not in pack["offer"].lower()
    assert pack["noise_rejected"]


def test_vnext_comparison_reports_gate_counts_and_deltas() -> None:
    comparison = compare_evidence_vnext_from_snapshot(_ambiguous_exa_snapshot()).to_dict()

    assert comparison["gate_summary"]["review_required_count"] >= 1
    assert "claim_delta" in comparison["summary"]
    assert comparison["summary"]["scorecard"]["status"] == "review_required"
    assert "review_required_evidence_present" in comparison["summary"]["scorecard"]["reason_codes"]
    assert comparison["summary"]["reclassified_to_noise_count"] >= 1
    assert comparison["vnext_graph_summary"]["noise_claim_count"] >= comparison["current_graph_summary"]["noise_claim_count"]


def test_vnext_infers_url_for_split_feature_snippet_and_url() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_split_snippet_url_snapshot()).to_dict()
    graph = build_vnext_evidence_graph_from_snapshot(_split_snippet_url_snapshot()).to_dict()

    assert packet["summary"]["review_reason_counts"].get("missing_evidence_url", 0) == 0
    assert any(
        item["classification_reason"] == "evidence_url_inferred_from_same_feature"
        and item["gate_status"] == "accepted"
        and item["url"] == "https://news.example.com/publicit-partner-program"
        for item in packet["observations"]
    )
    assert any(
        "verified agency partner program" in claim["text"]
        and claim["source_url"] == "https://news.example.com/publicit-partner-program"
        for claim in graph["claims"]
    )


def test_vnext_infers_url_for_derived_feature_text_from_raw_source() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_derived_feature_without_url_snapshot()).to_dict()
    graph = build_vnext_evidence_graph_from_snapshot(_derived_feature_without_url_snapshot()).to_dict()

    assert packet["summary"]["review_reason_counts"].get("missing_evidence_url", 0) == 0
    assert any(
        item["classification_reason"] == "evidence_url_inferred_from_raw_source_text"
        and item["gate_status"] == "accepted"
        and item["url"] == "https://www.publicit.com/about"
        for item in packet["observations"]
    )
    assert any(
        "campaign planning workspace" in claim["text"]
        and claim["source_url"] == "https://www.publicit.com/about"
        for claim in graph["claims"]
    )


def test_vnext_infers_url_for_formatted_and_fragmented_raw_source_text() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_formatted_and_fragmented_source_snapshot()).to_dict()

    assert packet["summary"]["review_reason_counts"].get("missing_evidence_url", 0) == 0
    inferred = [
        item
        for item in packet["observations"]
        if item["classification_reason"] == "evidence_url_inferred_from_raw_source_text"
    ]
    assert len(inferred) == 2
    assert all(item["url"] == "https://instantly.ai" for item in inferred)


def test_vnext_infers_url_from_audited_raw_source_word_windows() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_audited_source_window_snapshot()).to_dict()

    assert packet["summary"]["review_reason_counts"].get("missing_evidence_url", 0) == 0
    assert any(
        item["classification_reason"] == "evidence_url_inferred_from_raw_source_text"
        and item["gate_status"] == "accepted"
        and item["url"] == "https://www.langchain.com"
        for item in packet["observations"]
    )


def test_vnext_does_not_infer_ambiguous_exa_window_matches() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_ambiguous_exa_window_snapshot()).to_dict()

    assert packet["summary"]["review_reason_counts"].get("missing_evidence_url", 0) == 1
    assert not any(
        item["classification_reason"] == "evidence_url_inferred_from_raw_source_text"
        for item in packet["observations"]
    )


def test_vnext_quarantines_claims_from_unresolved_profile_source_urls() -> None:
    graph = build_vnext_evidence_graph_from_snapshot(_unresolved_profile_source_snapshot()).to_dict()
    linkedin_claims = [
        claim
        for claim in graph["claims"]
        if claim.get("source_url") == "https://linkedin.com/company/mistralai"
    ]

    assert linkedin_claims
    assert all(claim["claim_type"] == "noise" for claim in linkedin_claims)
    assert all(claim["source_type"] == "noise" for claim in linkedin_claims)
    assert all(claim["noise_reason"] == "unresolved_external_profile_source" for claim in linkedin_claims)


def test_vnext_marks_url_less_quote_as_covered_by_accepted_source() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_covered_by_accepted_source_snapshot()).to_dict()

    assert packet["summary"]["review_reason_counts"].get("missing_evidence_url", 0) == 0
    covered = [
        item
        for item in packet["accepted"]
        if item["classification_reason"] == "covered_by_accepted_source"
    ]
    assert len(covered) == 1
    assert covered[0]["url"] == "https://www.archetype.fund/about"


def test_vnext_rejects_internal_analysis_without_source_url() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_internal_analysis_without_url_snapshot()).to_dict()

    assert packet["summary"]["review_reason_counts"].get("missing_evidence_url", 0) == 0
    assert packet["summary"]["rejected_reason_counts"]["internal_analysis_not_market_evidence"] == 1
    assert packet["rejected"][0]["source_class"] == "visual_internal_metric"


def test_vnext_keeps_exa_external_visual_product_evidence_as_market_evidence() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_exa_external_visual_product_evidence_snapshot()).to_dict()

    assert packet["summary"]["rejected_reason_counts"].get("visual_or_internal_analysis_not_market_evidence", 0) == 0
    accepted = [
        item
        for item in packet["accepted"]
        if item["url"] == "https://www.gartner.com/reviews/product/figma-design"
    ]
    assert len(accepted) == 1
    assert accepted[0]["source_class"] == "external_third_party"
    assert accepted[0]["classification_reason"] == "exa_external_product_evidence_not_internal_visual_analysis"


def test_vnext_semantic_shadow_separates_material_and_weak_accepted_evidence() -> None:
    packet = build_evidence_vnext_packet_from_snapshot(_exa_semantic_materiality_snapshot())
    semantic = build_evidence_vnext_semantic_assessment(packet)

    assert packet.summary()["accepted_count"] == 2
    assert semantic["model_effect"] is False
    assert semantic["classifier"] == "heuristic_shadow_v0"
    assert semantic["summary"]["accepted_material_count"] == 1
    assert semantic["summary"]["accepted_weak_count"] == 1
    assert semantic["summary"]["semantic_class_counts"]["customer_case"] == 1
    assert semantic["summary"]["semantic_class_counts"]["competitor_comparison"] == 1
    weak = [
        item
        for item in semantic["assessments"]
        if item["semantic_class"] == "competitor_comparison"
    ]
    assert weak[0]["materiality"] == "low"
    assert weak[0]["gate_status"] == "accepted"


def test_vnext_semantic_shadow_marks_social_profile_placeholders_as_weak() -> None:
    packet = EvidenceVNextPacket(
        version="test",
        run_id=4201,
        brand_name="Becauce",
        url="https://www.becauce.com",
        observations=(
            SourceObservation(
                observation_id="obs_0001",
                text="instagram profile candidate",
                url="https://www.instagram.com/wwwbecaucecom",
                dimension="presencia",
                provider="social_scrape",
                feature_name="social_footprint",
                source_class="external_third_party",
                eligibility="observation_only",
                gate_status="accepted",
            ),
        ),
    )

    semantic = build_evidence_vnext_semantic_assessment(packet)

    row = semantic["assessments"][0]
    assert row["semantic_class"] == "tangential"
    assert row["materiality"] == "low"
    assert row["reason_codes"] == ["social_profile_placeholder_only"]
    assert semantic["summary"]["accepted_material_count"] == 0
    assert semantic["summary"]["accepted_weak_count"] == 1


def test_vnext_semantic_entity_fit_ignores_domain_stopwords_and_substrings() -> None:
    packet = EvidenceVNextPacket(
        version="test",
        run_id=4202,
        brand_name="Becauce",
        url="https://www.becauce.com",
        observations=(
            SourceObservation(
                observation_id="obs_0001",
                text=(
                    "Existing Brand3 competitor comparison identifies Be as the audited brand's "
                    "closest measured competitor with measured distance 0.941."
                ),
                url="snapshot://feature/competitor_web_comparison",
                dimension="diferenciacion",
                provider="competitor_web_comparison",
                feature_name="competitor_distance",
                source_class="competitor_comparison",
                eligibility="eligible_for_narrative_finding",
                gate_status="accepted",
            ),
        ),
    )

    semantic = build_evidence_vnext_semantic_assessment(packet)

    row = semantic["assessments"][0]
    assert row["entity_fit"] == "missing"
    assert row["semantic_class"] == "tangential"
    assert row["reason_codes"] == ["brand_entity_not_visible_in_text_or_url"]
    assert semantic["summary"]["accepted_material_count"] == 0
    assert semantic["summary"]["accepted_weak_count"] == 1


def test_vnext_semantic_shadow_classifies_strong_github_repo_as_owned_material() -> None:
    packet = EvidenceVNextPacket(
        version="test",
        run_id=4203,
        brand_name="Hermes Agent",
        url="https://hermes-agent.nousresearch.com",
        observations=(
            SourceObservation(
                observation_id="obs_0001",
                text="# Repository: NousResearch/hermes-agent The agent that grows with you - Stars: 194428",
                url="https://github.com/NousResearch/hermes-agent",
                dimension="presencia",
                provider="exa",
                feature_name="search_visibility",
                source_class="external_third_party",
                eligibility="observation_only",
                gate_status="accepted",
            ),
        ),
    )

    semantic = build_evidence_vnext_semantic_assessment(packet)

    row = semantic["assessments"][0]
    assert row["semantic_class"] == "owned_brand_evidence"
    assert row["materiality"] == "high"
    assert row["reason_codes"] == ["official_repository_signal"]
    assert semantic["summary"]["accepted_material_count"] == 1


def test_vnext_semantic_shadow_detects_release_and_ship_news_terms() -> None:
    packet = EvidenceVNextPacket(
        version="test",
        run_id=4204,
        brand_name="Hermes Agent",
        url="https://hermes-agent.nousresearch.com",
        observations=(
            SourceObservation(
                observation_id="obs_0001",
                text="Nous Research ships Hermes Agent Profile Builder in one dashboard flow",
                url="https://news.example.com/hermes-agent-profile-builder",
                dimension="vitalidad",
                provider="llm",
                feature_name="momentum",
                source_class="external_third_party",
                eligibility="eligible_for_narrative_finding",
                gate_status="accepted",
            ),
        ),
    )

    semantic = build_evidence_vnext_semantic_assessment(packet)

    row = semantic["assessments"][0]
    assert row["semantic_class"] == "market_news"
    assert row["materiality"] == "medium"
    assert row["reason_codes"] == ["market_news_or_press_signal"]


def test_vnext_semantic_shadow_does_not_treat_url_slug_alternative_as_comparison() -> None:
    packet = EvidenceVNextPacket(
        version="test",
        run_id=4205,
        brand_name="Hermes Agent",
        url="https://hermes-agent.nousresearch.com",
        observations=(
            SourceObservation(
                observation_id="obs_0001",
                text="Hermes Agent is an open-source AI agent framework from Nous Research that runs locally.",
                url="https://blog.example.com/hermes-agent-an-openclaw-alternative-with-memory",
                dimension="percepcion",
                provider="llm",
                feature_name="brand_sentiment",
                source_class="external_third_party",
                eligibility="eligible_for_narrative_finding",
                gate_status="accepted",
            ),
        ),
    )

    semantic = build_evidence_vnext_semantic_assessment(packet)

    row = semantic["assessments"][0]
    assert row["semantic_class"] == "direct_brand_evidence"
    assert row["materiality"] == "medium"


def test_vnext_batch_report_includes_semantic_shadow_counts() -> None:
    result = compare_legacy_current_and_vnext_from_snapshot(_exa_semantic_materiality_snapshot())
    report = build_batch_report([result])
    markdown = render_batch_report_markdown(report)

    assert result["vnext_semantic_assessment"]["summary"]["accepted_weak_count"] == 1
    assert report["semantic_evidence"]["classifier"] == "heuristic_shadow_v0"
    assert report["semantic_evidence"]["accepted_material"] == 1
    assert report["semantic_evidence"]["accepted_weak"] == 1
    assert report["semantic_evidence"]["semantic_class_counts"]["competitor_comparison"] == 1
    assert report["semantic_evidence"]["weak_examples"][0]["brand_name"] == "Canva"
    assert "## Semantic Evidence Shadow" in markdown
    assert "| competitor_comparison | 1 |" in markdown


def test_batch_report_summarizes_vnext_results_for_review() -> None:
    result = compare_legacy_current_and_vnext_from_snapshot(_ambiguous_exa_snapshot())
    report = build_batch_report([result], db_path="test.sqlite")
    markdown = render_batch_report_markdown(report)

    assert report["version"] == "evidence_vnext_batch_report_v0_1"
    assert report["runtime_effect"] is False
    assert report["prompt_effect"] is False
    assert report["totals"]["run_count"] == 1
    assert report["totals"]["review_required"] >= 1
    assert report["recommendation"]["status"] == "review_required"
    assert report["promotion_counts"]["blocked"] == 1
    assert report["manual_audit_counts"]["required"] == 0
    assert report["manual_audit_counts"]["not_required"] == 1
    assert report["rows"][0]["promotion_status"] == "blocked"
    assert report["rows"][0]["manual_audit_required"] is False
    assert "entity_boundary_review_blocks_promotion" in report["rows"][0]["promotion_reason_codes"]
    assert "missing_evidence_url_needs_source_propagation" not in report["recommendation"]["reason_codes"]
    assert report["review_examples_by_reason"]["same_name_different_root_domain"][0]["run_id"] == 4101
    assert report["rejected_examples_by_reason"]["technical_context_not_brand_narrative_evidence"][0]["run_id"] == 4101
    exa_row = next(row for row in report["acquisition_matrix"]["provider_rows"] if row["provider"] == "exa")
    assert exa_row["review_required"] >= 1
    assert exa_row["reason_counts"]["same_name_different_root_domain"] >= 1
    related_row = next(
        row for row in report["acquisition_matrix"]["source_class_rows"] if row["source_class"] == "related_unresolved"
    )
    assert related_row["review_required"] >= 1
    provider_contracts = {item["contract"]: item for item in report["provider_acquisition_contracts"]}
    assert provider_contracts["exa.entity_boundary_review"]["provider"] == "exa"
    assert provider_contracts["exa.entity_boundary_review"]["affected_observation_count"] >= 1
    assert provider_contracts["exa.entity_boundary_review"]["recommended_action"] == (
        "preserve_same_name_or_different_root_results_as_review_only"
    )
    assert provider_contracts["exa.entity_boundary_review"]["enforcement_point"] == "exa_entity_classification"
    assert "test_exa_same_name_different_root_is_review_required" in provider_contracts["exa.entity_boundary_review"][
        "proposed_tests"
    ]
    assert provider_contracts["exa.entity_boundary_review"]["acceptance_criteria"]
    assert provider_contracts["exa.entity_boundary_review"]["implementation_status"] == "vnext_gate_enforced"
    assert provider_contracts["context.technical_only"]["recommended_action"] == (
        "keep_technical_context_out_of_brand_narrative_evidence"
    )
    backlog_rows = {item["contract"]: item for item in report["provider_contract_backlog"]["rows"]}
    assert backlog_rows["exa.entity_boundary_review"]["implementation_status"] == "vnext_gate_enforced"
    assert report["provider_contract_backlog"]["counts"]["vnext_gate_enforced"] >= 1
    assert any(item["action"] == "implement_provider_acquisition_contract" for item in report["decision_queue"])
    assert report["decision_action_counts"]["implement_provider_acquisition_contract"] >= 1
    assert "# Evidence vNext Batch Report" in markdown
    assert "## Acquisition Matrix" in markdown
    assert "| exa |" in markdown
    assert "## Provider Acquisition Contracts" in markdown
    assert "`exa.entity_boundary_review`" in markdown
    assert "enforcement `exa_entity_classification`" in markdown
    assert "## Provider Contract Backlog" in markdown
    assert "| exa.entity_boundary_review | vnext_gate_enforced | evidence_gate |" in markdown
    assert "## Review Examples" in markdown
    assert "## Shadow Policy" in markdown
    assert "## Readiness Matrix" in markdown
    assert "## Intervention Packets" in markdown
    assert "## Work Orders" in markdown
    assert "## Adjudication Intake" in markdown
    assert "| 4101 | Publicit | review_required | blocked | no |" in markdown


def test_batch_report_aggregates_shadow_acquisition_contract_exclusions() -> None:
    result = compare_legacy_current_and_vnext_from_snapshot(_exa_empty_text_contract_snapshot())
    report = build_batch_report([result], db_path="test.sqlite")
    markdown = render_batch_report_markdown(report)

    exclusions = report["acquisition_contract_exclusions"]
    assert exclusions["total"] == 2
    assert exclusions["by_contract"]["exa.non_empty_text"] == 2
    assert exclusions["by_surface"]["raw_inputs.exa.mentions"] == 1
    assert exclusions["by_surface"]["features.exa.raw_value.evidence"] == 1
    assert "## Acquisition Contract Exclusions" in markdown
    assert "| exa.non_empty_text | 2 |" in markdown


def test_batch_report_marks_limited_candidate_with_material_changes_as_audit_required() -> None:
    result = {
        "vnext_gate": {
            "summary": {
                "accepted_count": 4,
                "review_required_count": 1,
                "rejected_count": 2,
                "review_reason_counts": {"missing_evidence_url": 1},
                "rejected_reason_counts": {},
                "source_class_counts": {},
            },
            "review_required": [
                {
                    "classification_reason": "missing_evidence_url",
                    "feature_name": "tone_consistency",
                    "provider": "llm",
                    "source_class": "external_third_party",
                    "eligibility": "requires_human_review",
                    "url": "",
                    "text": "A source-less tone quote.",
                }
            ],
            "rejected": [],
        },
            "vnext_comparison": {
                "run_id": 4201,
                "brand_name": "AuditCo",
                "url": "https://auditco.com",
            "fields": [
                {"field": "proof_points", "changed": True},
                {"field": "offer", "changed": False},
            ],
            "summary": {
                "scorecard": {"status": "review_required", "reason_codes": []},
                "reclassified_to_noise_count": 1,
                "changed_count": 1,
                "lost_count": 0,
                "material_lost_count": 0,
                "material_lost_fields": [],
                "non_material_lost_fields": [],
            },
        },
    }

    report = build_batch_report([result])

    assert report["promotion_counts"]["audit_required"] == 1
    assert report["manual_audit_counts"]["required"] == 1
    assert report["manual_audit_verdict_counts"]["quote_source_review"] == 1
    assert report["rows"][0]["promotion_status"] == "audit_required"
    assert report["rows"][0]["manual_audit_required"] is True
    assert "manual_audit_required_for_material_field_changes" in report["rows"][0]["promotion_reason_codes"]
    assert report["manual_audit_queue"][0]["run_id"] == 4201
    assert report["manual_audit_queue"][0]["audit_verdict"] == "quote_source_review"
    assert "url_less_quote_review_present" in report["manual_audit_queue"][0]["audit_reason_codes"]
    assert report["manual_audit_queue"][0]["changed_material_fields"][0]["field"] == "proof_points"
    assert report["manual_audit_queue"][0]["review_examples"][0]["classification_reason"] == "missing_evidence_url"
    assert "review_material_field_changes" in report["manual_audit_queue"][0]["triage_actions"]
    assert "add_source_url_or_keep_quote_review_gated" in report["manual_audit_queue"][0]["triage_actions"]
    assert report["quote_source_review_queue"][0]["run_id"] == 4201
    assert report["quote_source_review_queue"][0]["manual_audit_required"] is True
    assert report["quote_source_review_queue"][0]["observations"][0]["feature_name"] == "tone_consistency"


def test_batch_report_blocks_reserved_placeholder_domains() -> None:
    result = {
        "vnext_gate": {
            "summary": {
                "accepted_count": 4,
                "review_required_count": 1,
                "rejected_count": 0,
                "review_reason_counts": {"same_name_external_profile_not_alias": 1},
                "rejected_reason_counts": {},
                "source_class_counts": {},
            },
            "review_required": [],
            "rejected": [],
        },
        "vnext_comparison": {
            "run_id": 4202,
            "brand_name": "example.com",
            "url": "https://example.com",
            "fields": [{"field": "proof_points", "changed": False}],
            "summary": {
                "scorecard": {"status": "review_required", "reason_codes": []},
                "reclassified_to_noise_count": 1,
                "changed_count": 0,
                "lost_count": 0,
                "material_lost_count": 0,
                "material_lost_fields": [],
                "non_material_lost_fields": [],
            },
        },
    }

    report = build_batch_report([result])

    assert report["promotion_counts"]["blocked"] == 1
    assert report["rows"][0]["promotion_status"] == "blocked"
    assert "reserved_or_placeholder_entity_blocks_promotion" in report["rows"][0]["promotion_reason_codes"]


def test_batch_report_keeps_external_profile_review_only_without_material_overlap() -> None:
    result = {
        "vnext_gate": {
            "summary": {
                "accepted_count": 4,
                "review_required_count": 1,
                "rejected_count": 0,
                "review_reason_counts": {"same_name_external_profile_not_alias": 1},
                "rejected_reason_counts": {},
                "source_class_counts": {},
            },
            "review_required": [
                {
                    "classification_reason": "same_name_external_profile_not_alias",
                    "feature_name": "social_footprint",
                    "provider": "social_scrape",
                    "source_class": "related_unresolved",
                    "eligibility": "requires_human_review",
                    "url": "https://linkedin.com/company/auditco",
                    "text": "linkedin profile candidate",
                }
            ],
            "rejected": [],
        },
        "vnext_pack": {
            "proof_points": [{"text": "AuditCo ships workflow automation for support teams."}],
            "founder_or_press_context": [],
            "competitive_context": [],
        },
        "vnext_comparison": {
            "run_id": 4203,
            "brand_name": "AuditCo",
            "url": "https://auditco.com",
            "fields": [{"field": "proof_points", "changed": True}],
            "summary": {
                "scorecard": {"status": "review_required", "reason_codes": []},
                "reclassified_to_noise_count": 1,
                "changed_count": 1,
                "lost_count": 0,
                "material_lost_count": 0,
                "material_lost_fields": [],
                "non_material_lost_fields": [],
            },
        },
    }

    report = build_batch_report([result])

    assert report["rows"][0]["promotion_status"] == "audit_required"
    assert report["manual_audit_verdict_counts"]["alias_confirmation_review"] == 1
    assert report["manual_audit_queue"][0]["audit_verdict"] == "alias_confirmation_review"
    assert report["manual_audit_queue"][0]["review_material_overlaps"] == []
    assert "confirm_external_profile_alias" in report["manual_audit_queue"][0]["triage_actions"]
    assert report["contract_projection"]["applied_contracts"] == ["social_scrape.placeholder_profile_non_material"]
    assert report["contract_projection"]["removed_review_observation_count"] == 1
    assert report["contract_projection"]["projected_promotion_counts"]["candidate"] == 1
    assert report["shadow_policy"]["runs"][0]["next_action"] == "candidate_after_contract"


def test_batch_report_distinguishes_quote_plus_alias_manual_audit() -> None:
    result = {
        "vnext_gate": {
            "summary": {
                "accepted_count": 4,
                "review_required_count": 2,
                "rejected_count": 0,
                "review_reason_counts": {
                    "missing_evidence_url": 1,
                    "same_name_external_profile_not_alias": 1,
                },
                "rejected_reason_counts": {},
                "source_class_counts": {},
            },
            "review_required": [
                {
                    "classification_reason": "same_name_external_profile_not_alias",
                    "feature_name": "social_footprint",
                    "provider": "social_scrape",
                    "source_class": "related_unresolved",
                    "eligibility": "requires_human_review",
                    "url": "https://linkedin.com/company/auditco",
                    "text": "linkedin profile candidate",
                },
                {
                    "classification_reason": "missing_evidence_url",
                    "feature_name": "tone_consistency",
                    "provider": "llm",
                    "source_class": "external_third_party",
                    "eligibility": "requires_human_review",
                    "url": "",
                    "text": "A source-less tone quote.",
                },
            ],
            "rejected": [],
        },
        "current_graph_pack": {
            "proof_points": [{"text": "A source-less tone quote."}],
            "founder_or_press_context": [],
            "competitive_context": [],
        },
        "vnext_pack": {
            "proof_points": [{"text": "AuditCo ships workflow automation for support teams."}],
            "founder_or_press_context": [],
            "competitive_context": [],
        },
        "vnext_comparison": {
            "run_id": 4207,
            "brand_name": "AuditCo",
            "url": "https://auditco.com",
            "fields": [{"field": "proof_points", "changed": True}],
            "summary": {
                "scorecard": {"status": "review_required", "reason_codes": []},
                "reclassified_to_noise_count": 1,
                "changed_count": 1,
                "lost_count": 0,
                "material_lost_count": 0,
                "material_lost_fields": [],
                "non_material_lost_fields": [],
            },
        },
    }

    report = build_batch_report([result])

    assert report["rows"][0]["promotion_status"] == "audit_required"
    assert report["manual_audit_verdict_counts"]["quote_source_and_alias_review"] == 1
    assert report["manual_audit_queue"][0]["audit_verdict"] == "quote_source_and_alias_review"
    assert "url_less_quote_review_present" in report["manual_audit_queue"][0]["audit_reason_codes"]
    assert "external_profile_alias_review_present" in report["manual_audit_queue"][0]["audit_reason_codes"]
    assert report["quote_source_review_queue"][0]["observations"][0]["material_impact"] == "removed_from_material_by_vnext"
    assert report["quote_source_review_queue"][0]["observations"][0]["current_material_fields"] == ["proof_points"]
    assert report["quote_source_review_queue"][0]["observations"][0]["vnext_material_fields"] == []
    assert report["quote_source_material_impact_counts"]["removed_from_material_by_vnext"] == 1
    assert report["contract_recommendations"][0]["contract"] == "tone_consistency.source_url"
    assert report["contract_recommendations"][0]["severity"] == "high"
    assert report["contract_recommendations"][0]["recommended_action"] == (
        "require_source_url_or_exclude_from_material_evidence"
    )
    assert report["contract_recommendations"][0]["affected_runs"] == [4207]
    assert report["contract_projection"]["applied_contracts"] == [
        "social_scrape.placeholder_profile_non_material",
        "tone_consistency.source_url",
    ]
    assert report["contract_projection"]["removed_review_observation_count"] == 2
    assert report["contract_projection"]["projected_promotion_counts"]["candidate"] == 1
    assert report["contract_projection"]["status_transitions"][0]["projected_promotion_status"] == "candidate"
    assert report["decision_queue"][0]["action"] == "implement_contract_recommendation"
    assert report["decision_queue"][0]["affected_runs"] == [4207]
    assert "manual_audit_projected_material_changes" not in report["decision_action_counts"]
    assert report["shadow_policy"]["runtime_effect"] is False
    assert report["shadow_policy"]["prompt_effect"] is False
    assert report["shadow_policy"]["runs"][0]["contract_effect"] == "removes_review_observations"
    assert report["shadow_policy"]["runs"][0]["next_action"] == "candidate_after_contract"
    assert report["shadow_policy"]["next_action_counts"]["candidate_after_contract"] == 1
    assert report["readiness_matrix"]["rows"][0]["readiness_status"] == "ready_after_shadow_policy"
    assert report["readiness_matrix"]["rows"][0]["intervention_type"] == "none"
    assert report["readiness_matrix"]["rows"][0]["automation_lane"] == "contract_can_auto_clear"
    assert report["readiness_matrix"]["counts"]["intervention:none"] == 1
    assert report["intervention_packets"][0]["packet_id"] == "intervention:none"
    assert report["intervention_packets"][0]["affected_runs"] == [4207]
    assert report["intervention_packets"][0]["automation_lane"] == "contract_can_auto_clear"
    assert report["intervention_packets"][0]["closure_criteria"]
    assert report["intervention_packets"][0]["checklist"]
    assert report["work_orders"][0]["work_order_id"] == "workorder:none:4207"
    assert report["work_orders"][0]["expected_output"] == "candidate"
    assert report["work_orders"][0]["requires_recompute"] is False
    assert report["work_orders"][0]["checklist"]
    assert report["work_orders"][0]["allowed_decisions"] == ["no_action_required"]
    assert report["work_orders"][0]["decision_required_fields"] == ["decision"]
    assert report["work_orders"][0]["decision_record_template"]["work_order_id"] == "workorder:none:4207"
    assert report["adjudication_intake"]["status"] == "pending_decisions"
    assert report["adjudication_intake"]["pending_count"] == 1
    assert report["adjudication_intake"]["expected_output_counts"]["candidate"] == 1
    assert report["adjudication_intake"]["records"][0]["status"] == "pending_decision"
    assert report["adjudication_intake"]["records"][0]["record"]["work_order_id"] == "workorder:none:4207"


def test_batch_report_projects_contract_effect_on_review_required_runs() -> None:
    result = {
        "vnext_gate": {
            "summary": {
                "accepted_count": 4,
                "review_required_count": 4,
                "rejected_count": 0,
                "review_reason_counts": {
                    "missing_evidence_url": 1,
                    "same_name_external_profile_not_alias": 3,
                },
                "rejected_reason_counts": {},
                "source_class_counts": {},
            },
            "review_required": [
                {
                    "classification_reason": "same_name_external_profile_not_alias",
                    "feature_name": "social_footprint",
                    "provider": "social_scrape",
                    "source_class": "related_unresolved",
                    "eligibility": "requires_human_review",
                    "url": "https://linkedin.com/company/auditco",
                    "text": "linkedin profile candidate",
                },
                {
                    "classification_reason": "same_name_external_profile_not_alias",
                    "feature_name": "search_visibility",
                    "provider": "exa",
                    "source_class": "related_unresolved",
                    "eligibility": "requires_human_review",
                    "url": "https://linkedin.com/company/auditco-news",
                    "text": "another profile candidate",
                },
                {
                    "classification_reason": "same_name_external_profile_not_alias",
                    "feature_name": "brand_sentiment",
                    "provider": "exa",
                    "source_class": "related_unresolved",
                    "eligibility": "requires_human_review",
                    "url": "https://linkedin.com/company/auditco-alt",
                    "text": "third profile candidate",
                },
                {
                    "classification_reason": "missing_evidence_url",
                    "feature_name": "tone_consistency",
                    "provider": "llm",
                    "source_class": "external_third_party",
                    "eligibility": "requires_human_review",
                    "url": "",
                    "text": "A source-less tone quote.",
                },
            ],
            "rejected": [],
        },
        "current_graph_pack": {
            "proof_points": [{"text": "A source-less tone quote."}],
            "founder_or_press_context": [],
            "competitive_context": [],
        },
        "vnext_pack": {
            "proof_points": [{"text": "AuditCo ships workflow automation for support teams."}],
            "founder_or_press_context": [],
            "competitive_context": [],
        },
        "vnext_comparison": {
            "run_id": 4208,
            "brand_name": "AuditCo",
            "url": "https://auditco.com",
            "fields": [{"field": "proof_points", "changed": True}],
            "summary": {
                "scorecard": {"status": "review_required", "reason_codes": []},
                "reclassified_to_noise_count": 1,
                "changed_count": 1,
                "lost_count": 0,
                "material_lost_count": 0,
                "material_lost_fields": [],
                "non_material_lost_fields": [],
            },
        },
    }

    report = build_batch_report([result])

    assert report["rows"][0]["promotion_status"] == "review_required"
    assert report["contract_projection"]["applied_contracts"] == [
        "social_scrape.placeholder_profile_non_material",
        "tone_consistency.source_url",
    ]
    assert report["contract_projection"]["removed_review_observation_count"] == 2
    assert report["contract_projection"]["projected_promotion_counts"]["audit_required"] == 1
    assert report["contract_projection"]["status_transitions"][0]["run_id"] == 4208
    assert report["contract_projection"]["status_transitions"][0]["current_promotion_status"] == "review_required"
    assert report["contract_projection"]["status_transitions"][0]["projected_promotion_status"] == "audit_required"
    assert report["decision_action_counts"]["implement_contract_recommendation"] == 1
    assert report["decision_action_counts"]["manual_audit_projected_material_changes"] == 1
    assert report["shadow_policy"]["runs"][0]["status_transition"] is True
    assert report["shadow_policy"]["runs"][0]["current_promotion_status"] == "review_required"
    assert report["shadow_policy"]["runs"][0]["projected_promotion_status"] == "audit_required"
    assert report["shadow_policy"]["runs"][0]["next_action"] == "manual_audit_projected_material_changes"
    assert report["readiness_matrix"]["rows"][0]["status_transition"] is True
    assert report["readiness_matrix"]["rows"][0]["readiness_status"] == "needs_manual_audit"
    assert report["intervention_packets"][0]["promotion_after_closure"] == "candidate_if_no_new_blockers"
    assert report["work_orders"][0]["promotion_after_closure"] == "candidate_if_no_new_blockers"


def test_batch_report_blocks_external_profile_review_when_it_overlaps_material_fields() -> None:
    profile_text = "AuditCo LinkedIn says the company is an unrelated staffing agency."
    result = {
        "vnext_gate": {
            "summary": {
                "accepted_count": 4,
                "review_required_count": 1,
                "rejected_count": 0,
                "review_reason_counts": {"same_name_external_profile_not_alias": 1},
                "rejected_reason_counts": {},
                "source_class_counts": {},
            },
            "review_required": [
                {
                    "classification_reason": "same_name_external_profile_not_alias",
                    "feature_name": "social_footprint",
                    "provider": "social_scrape",
                    "source_class": "related_unresolved",
                    "eligibility": "requires_human_review",
                    "url": "https://linkedin.com/company/auditco",
                    "text": profile_text,
                }
            ],
            "rejected": [],
        },
        "vnext_pack": {
            "proof_points": [{"text": profile_text}],
            "founder_or_press_context": [],
            "competitive_context": [],
        },
        "vnext_comparison": {
            "run_id": 4204,
            "brand_name": "AuditCo",
            "url": "https://auditco.com",
            "fields": [{"field": "proof_points", "changed": True}],
            "summary": {
                "scorecard": {"status": "review_required", "reason_codes": []},
                "reclassified_to_noise_count": 1,
                "changed_count": 1,
                "lost_count": 0,
                "material_lost_count": 0,
                "material_lost_fields": [],
                "non_material_lost_fields": [],
            },
        },
    }

    report = build_batch_report([result])

    assert report["rows"][0]["promotion_status"] == "blocked"
    assert "entity_profile_review_in_material_fields_blocks_promotion" in report["rows"][0]["promotion_reason_codes"]
    assert report["blocked_evidence_queue"][0]["run_id"] == 4204
    assert report["blocked_evidence_queue"][0]["review_material_overlaps"][0]["field"] == "proof_points"
    assert "confirm_entity_alias_before_promotion" in report["blocked_evidence_queue"][0]["triage_actions"]
    assert "keep_blocked_until_triage_resolved" in report["blocked_evidence_queue"][0]["triage_actions"]


def test_batch_report_blocks_unresolved_profile_source_url_in_material_fields() -> None:
    result = {
        "vnext_gate": {
            "summary": {
                "accepted_count": 4,
                "review_required_count": 1,
                "rejected_count": 0,
                "review_reason_counts": {"same_name_external_profile_not_alias": 1},
                "rejected_reason_counts": {},
                "source_class_counts": {},
            },
            "review_required": [
                {
                    "classification_reason": "same_name_external_profile_not_alias",
                    "feature_name": "social_footprint",
                    "provider": "social_scrape",
                    "source_class": "related_unresolved",
                    "eligibility": "requires_human_review",
                    "url": "https://www.linkedin.com/company/auditco/",
                    "text": "linkedin profile candidate",
                }
            ],
            "rejected": [],
        },
        "vnext_pack": {
            "proof_points": [],
            "founder_or_press_context": [
                {
                    "text": "AuditCo is a workflow automation company according to the unresolved profile.",
                    "source_url": "https://linkedin.com/company/auditco",
                }
            ],
            "competitive_context": [],
        },
        "vnext_comparison": {
            "run_id": 4206,
            "brand_name": "AuditCo",
            "url": "https://auditco.com",
            "fields": [{"field": "founder_or_press_context", "changed": True}],
            "summary": {
                "scorecard": {"status": "review_required", "reason_codes": []},
                "reclassified_to_noise_count": 1,
                "changed_count": 1,
                "lost_count": 0,
                "material_lost_count": 0,
                "material_lost_fields": [],
                "non_material_lost_fields": [],
            },
        },
    }

    report = build_batch_report([result])

    assert report["rows"][0]["promotion_status"] == "blocked"
    assert "entity_profile_review_in_material_fields_blocks_promotion" in report["rows"][0]["promotion_reason_codes"]
    assert report["blocked_evidence_queue"][0]["review_material_overlaps"][0]["classification_reason"] == (
        "same_name_external_profile_material_source"
    )
    assert "confirm_entity_alias_before_promotion" in report["blocked_evidence_queue"][0]["triage_actions"]


def test_batch_report_lists_material_quote_contract_violations() -> None:
    quote = "AuditCo gives support teams a sourced workflow automation platform."
    result = {
        "vnext_gate": {
            "summary": {
                "accepted_count": 4,
                "review_required_count": 1,
                "rejected_count": 0,
                "review_reason_counts": {"missing_evidence_url": 1},
                "rejected_reason_counts": {},
                "source_class_counts": {},
            },
            "review_required": [
                {
                    "classification_reason": "missing_evidence_url",
                    "feature_name": "tone_consistency",
                    "provider": "llm",
                    "source_class": "external_third_party",
                    "eligibility": "requires_human_review",
                    "url": "",
                    "text": quote,
                }
            ],
            "rejected": [],
        },
        "vnext_pack": {
            "proof_points": [{"text": quote}],
            "founder_or_press_context": [],
            "competitive_context": [],
        },
        "current_graph_pack": {
            "proof_points": [{"text": quote}],
            "founder_or_press_context": [],
            "competitive_context": [],
        },
        "vnext_comparison": {
            "run_id": 4205,
            "brand_name": "AuditCo",
            "url": "https://auditco.com",
            "fields": [{"field": "proof_points", "changed": True}],
            "summary": {
                "scorecard": {"status": "review_required", "reason_codes": []},
                "reclassified_to_noise_count": 1,
                "changed_count": 1,
                "lost_count": 0,
                "material_lost_count": 0,
                "material_lost_fields": [],
                "non_material_lost_fields": [],
            },
        },
    }

    report = build_batch_report([result])

    assert report["rows"][0]["promotion_status"] == "blocked"
    assert "material_quote_without_source_blocks_promotion" in report["rows"][0]["promotion_reason_codes"]
    assert report["blocked_evidence_queue"][0]["run_id"] == 4205
    assert report["material_quote_contract_queue"][0]["run_id"] == 4205
    assert report["material_quote_contract_queue"][0]["promotion_status"] == "blocked"
    assert report["material_quote_contract_queue"][0]["violations"][0]["feature_name"] == "tone_consistency"
    assert report["quote_source_review_queue"][0]["run_id"] == 4205
    assert report["quote_source_review_queue"][0]["promotion_status"] == "blocked"
    assert report["quote_source_material_impact_counts"]["still_in_material"] == 1
    assert report["contract_recommendations"][0]["contract"] == "tone_consistency.source_url"
    assert "unsourced_quote_still_in_material_fields" in report["contract_recommendations"][0]["reason_codes"]
    assert "add_source_url_or_remove_material_quote" in report["material_quote_contract_queue"][0]["triage_actions"]
    assert "keep_blocked_until_triage_resolved" in report["material_quote_contract_queue"][0]["triage_actions"]
