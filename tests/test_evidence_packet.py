from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from src.reports.evidence_packet import OUTPUT_FIELDS, build_evidence_packet_v0


def _feature(dimension, name, source, raw, confidence=0.8):
    return {
        "dimension_name": dimension,
        "feature_name": name,
        "source": source,
        "confidence": confidence,
        "raw_value": repr(raw),
    }


def _snapshot():
    return {
        "run": {
            "id": 74,
            "brand_name": "builtwith.kit.com",
            "url": "https://builtwith.kit.com",
        },
        "raw_inputs": [
            {"source": "web", "payload": {"url": "https://builtwith.kit.com"}},
            {"source": "exa", "payload": {"mentions": []}},
        ],
        "features": [
            _feature(
                "presencia",
                "web_presence",
                "web_scrape",
                {
                    "evidence_snippet": "Make email your most valuable channel. Kit is the email-first operating system for creators who mean business."
                },
            ),
            _feature(
                "presencia",
                "context_readiness",
                "context",
                {"robots_found": True, "evidence_url": "https://builtwith.kit.com/robots.txt"},
            ),
            _feature(
                "coherencia",
                "visual_consistency",
                "visual_analysis",
                {"evidence_insights": ["Local image analysis found 6 dominant color groups."]},
            ),
            _feature(
                "coherencia",
                "messaging_consistency",
                "llm",
                {
                    "gaps": [
                        {
                            "self_says": "Make email your most valuable channel",
                            "third_party_says": "BuiltWith is a web intelligence platform.",
                            "source_url": "https://builtwith.com/about",
                        }
                    ]
                },
            ),
            _feature(
                "percepcion",
                "brand_sentiment",
                "llm",
                {
                    "evidence": [
                        {
                            "quote": "Automated Malware Analysis Report",
                            "source_url": "https://www.joesandbox.com/analysis/1719754/0/html",
                        },
                        {
                            "quote": "Independent external article",
                            "source_url": "https://example-news.com/builtwith-kit",
                        },
                        {
                            "quote": "Independent customer review language",
                            "source_url": "https://example-reviews.com/builtwith-kit",
                        },
                    ]
                },
            ),
            _feature(
                "percepcion",
                "external_profile",
                "exa",
                {"evidence": [{"source_url": "https://example.com/profile-only"}]},
            ),
            _feature(
                "vitalidad",
                "developer_activity",
                "exa",
                {
                    "evidence": [
                        {
                            "quote": "Watermelon UI repository has 14 stars and 6 forks.",
                            "source_url": "https://github.com/WatermelonCorp/watermellon-registry",
                        }
                    ]
                },
            ),
            _feature(
                "presencia",
                "marketplace_presence",
                "exa",
                {
                    "evidence": [
                        {
                            "quote": "Watermelon UI listing has 13 upvotes.",
                            "source_url": "https://www.uneed.best/tool/watermelon-ui",
                        }
                    ]
                },
            ),
            _feature(
                "vitalidad",
                "publication_cadence",
                "exa",
                {
                    "evidence": [
                        {
                            "quote": "Fresh-pro announces honey watermelons brand refresh and new mascot.",
                            "source_url": "https://perishablenews.com/produce/fresh-pro-announces-honey-watermelons-brand-refresh-new-mascot/",
                        }
                    ]
                },
            ),
            _feature(
                "coherencia",
                "messaging_consistency",
                "exa",
                {
                    "evidence": [
                        {
                            "quote": "BuiltWith is a Software Development company.",
                            "source_url": "https://www.crunchbase.com/organization/builtwith",
                        }
                    ]
                },
            ),
        ],
        "evidence_items": [
            {
                "source": "context",
                "url": "https://builtwith.kit.com/robots.txt",
                "quote": "robots.txt found",
                "feature_name": "site_structure",
                "dimension_name": "presencia",
                "confidence": 0.75,
            }
        ],
        "scores": [],
    }


def _linear_comparison_snapshot(raw):
    return {
        "run": {"id": 80, "brand_name": "Linear", "url": "https://linear.app"},
        "raw_inputs": [],
        "features": [
            _feature("diferenciacion", "competitor_distance", "competitor_web_comparison", raw),
        ],
        "evidence_items": [],
        "scores": [],
    }


def _snapshot_with_exa_url_override(url: str, *, source_class: str, relation: str = "", requires_review: bool = False, reason: str = ""):
    snapshot = deepcopy(_snapshot())
    exa_payload = next(item["payload"] for item in snapshot["raw_inputs"] if item["source"] == "exa")
    exa_payload["mentions"] = exa_payload.get("mentions", []) + [
        {
            "url": url,
            "title": "override",
            "text": "override",
            "source_class": source_class,
            "relation": relation,
            "requires_human_review": requires_review,
            "classification_reason": reason,
        }
    ]
    return snapshot


def test_evidence_packet_has_stable_output_shape_and_offline_flags():
    packet = build_evidence_packet_v0(_snapshot())

    assert list(packet.keys()) == list(OUTPUT_FIELDS)
    assert packet["version"] == 0
    assert packet["metadata"]["llm_required"] is False
    assert packet["metadata"]["deep_research_required"] is False
    assert packet["metadata"]["runtime_effect"] is False
    assert packet["metadata"]["network_required"] is False
    assert "entity_resolution" in packet
    assert "cross_dimension_evidence" in packet
    assert "dimension_readiness" in packet
    assert set(packet["dimension_readiness"]) == {"coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad"}


def test_technical_artifacts_are_not_finding_eligible():
    packet = build_evidence_packet_v0(_snapshot())

    assert any("robots.txt" in item["url"] for item in packet["technical_signals"])
    assert not any("robots.txt" in item.get("url", "") for item in packet["finding_eligible_evidence"])
    assert any(
        "robots.txt" in item.get("url", "") and item["eligibility"] == "technical_only"
        for item in packet["evidence_not_eligible_for_findings"]
    )


def test_visual_internal_metrics_are_not_finding_eligible():
    packet = build_evidence_packet_v0(_snapshot())

    assert any("Local image analysis" in item["text"] for item in packet["visual_or_internal_signals"])
    assert not any("Local image analysis" in item["text"] for item in packet["finding_eligible_evidence"])


def test_url_less_owned_claim_is_owned_and_missing_evidence():
    packet = build_evidence_packet_v0(_snapshot())

    assert any("email-first operating system" in item["text"] for item in packet["owned_claims"])
    assert any("email-first operating system" in item["text"] for item in packet["missing_evidence"])
    assert not any("email-first operating system" in item["text"] for item in packet["finding_eligible_evidence"])


def test_same_name_different_root_is_unresolved_related_surface_not_alias():
    packet = build_evidence_packet_v0(_snapshot())

    related = [item for item in packet["related_surface_evidence"] if "builtwith.com" in item["url"]]
    assert related
    assert all(item["relationship"] == "unresolved" for item in related)
    assert any(item["ambiguity"] == "same_name_different_root" for item in packet["entity_ambiguity"])
    assert not any("BuiltWith is a web intelligence platform" in item["text"] for item in packet["finding_eligible_evidence"])


def test_trust_security_signals_require_review():
    packet = build_evidence_packet_v0(_snapshot())

    assert any("joesandbox.com" in item["url"] for item in packet["trust_or_security_signals"])
    assert any(item["reason"] == "trust_or_security_signal_requires_review" for item in packet["requires_human_review"])
    assert not any("joesandbox.com" in item.get("url", "") for item in packet["finding_eligible_evidence"])


def test_external_evidence_can_be_finding_eligible_after_classification():
    packet = build_evidence_packet_v0(_snapshot())

    assert any("example-news.com" in item["url"] for item in packet["external_evidence"])
    assert any("example-news.com" in item["url"] for item in packet["finding_eligible_evidence"])


def test_exa_related_unresolved_metadata_downgrades_external_eligibility():
    packet = build_evidence_packet_v0(
        _snapshot_with_exa_url_override(
            "https://example-news.com/builtwith-kit",
            source_class="related_unresolved",
            relation="unresolved",
            requires_review=True,
            reason="same_name_different_root_domain",
        )
    )

    related = [item for item in packet["related_surface_evidence"] if "example-news.com" in item.get("url", "")]
    assert related
    assert all(item["eligibility"] == "requires_human_review" for item in related)
    assert not any("example-news.com" in item.get("url", "") for item in packet["finding_eligible_evidence"])


def test_empty_text_url_evidence_is_blocked_from_normal_eligibility():
    packet = build_evidence_packet_v0(_snapshot())

    blocked = [
        item
        for item in packet["evidence_not_eligible_for_findings"]
        if item.get("url") == "https://example.com/profile-only"
    ]
    assert blocked
    assert blocked[0]["eligibility"] == "blocked_empty_text"
    assert not any(item.get("url") == "https://example.com/profile-only" for item in packet["finding_eligible_evidence"])


def test_entity_resolution_related_surfaces_include_relation_metadata():
    packet = build_evidence_packet_v0(_snapshot())

    related = packet["entity_resolution"]["related_surfaces"]
    assert related
    assert all(
        {"surface", "relation_type", "relationship", "confidence", "evidence", "requires_human_review"} <= set(item)
        for item in related
    )
    assert any(item["relation_type"] == "ambiguous_name_match" for item in related)


def test_source_inventory_uses_reference_shape():
    packet = build_evidence_packet_v0(_snapshot())

    assert packet["source_inventory"]
    assert all({"url", "source_type", "source_quality", "role", "notes"} <= set(item) for item in packet["source_inventory"])
    assert any(item["source_type"] == "repository" for item in packet["source_inventory"])
    assert any(item["source_type"] == "marketplace" for item in packet["source_inventory"])


def test_repository_evidence_does_not_imply_adoption():
    packet = build_evidence_packet_v0(_snapshot())

    repo_not_eligible = [
        item for item in packet["evidence_not_eligible_for_findings"] if "github.com" in item.get("url", "")
    ]
    assert repo_not_eligible
    assert all(item["eligibility"] == "observation_only" for item in repo_not_eligible)
    assert not any("github.com" in item.get("url", "") for item in packet["finding_eligible_evidence"])


def test_marketplace_listing_is_not_automatically_finding_eligible():
    packet = build_evidence_packet_v0(_snapshot())

    marketplace = [
        item for item in packet["evidence_not_eligible_for_findings"] if "uneed.best" in item.get("url", "")
    ]
    assert marketplace
    assert all(item["eligibility"] == "requires_human_review" for item in marketplace)
    assert not any("uneed.best" in item.get("url", "") for item in packet["finding_eligible_evidence"])


def test_contradiction_candidates_are_recorded_for_deterministic_risks():
    packet = build_evidence_packet_v0(_snapshot())

    candidates = packet["cross_dimension_evidence"]["contradiction_candidates"]
    assert candidates
    assert any(item["type"] == "same_name_different_root_ambiguity" for item in candidates)
    assert any(item["type"] == "count_or_activity_claims_require_support" for item in candidates)


def test_off_topic_same_name_noise_is_excluded():
    packet = build_evidence_packet_v0(_snapshot())

    assert any("perishablenews.com" in item.get("url", "") for item in packet["excluded_noise"])
    assert not any("perishablenews.com" in item.get("url", "") for item in packet["finding_eligible_evidence"])


def test_same_name_external_profiles_are_review_gated_not_eligible():
    packet = build_evidence_packet_v0(_snapshot())

    related = [item for item in packet["related_surface_evidence"] if "crunchbase.com" in item.get("url", "")]
    assert related
    assert all(item["eligibility"] == "requires_human_review" for item in related)
    assert not any("crunchbase.com" in item.get("url", "") for item in packet["finding_eligible_evidence"])


def test_dimension_readiness_contract_shape_and_counts():
    packet = build_evidence_packet_v0(_snapshot())

    for readiness in packet["dimension_readiness"].values():
        assert {
            "status",
            "eligible_count",
            "blocked_count",
            "review_required_count",
            "missing_evidence_count",
            "reason_codes",
            "readiness_reason",
            "recommended_action",
        } <= set(readiness)
        assert readiness["status"] in {"ready", "thin", "blocked", "abstain", "review_required"}


def test_diferenciacion_abstains_without_comparative_or_competitor_evidence():
    packet = build_evidence_packet_v0(_snapshot())

    readiness = packet["dimension_readiness"]["diferenciacion"]
    assert readiness["status"] == "abstain"
    assert "competitor_corpus_required" in readiness["reason_codes"]


def test_competitor_comparison_feature_creates_bounded_differentiation_evidence():
    packet = build_evidence_packet_v0(
        _linear_comparison_snapshot(
            {
                "avg_distance": 0.821,
                "closest_competitor": {"name": "Wrike", "distance": 0.752},
                "most_different": {"name": "ProjectManager", "distance": 0.872},
                "competitors_analyzed": 5,
            }
        )
    )

    comparison = [item for item in packet["finding_eligible_evidence"] if item["source_class"] == "competitor_comparison"]
    assert len(comparison) == 2
    assert all(item["dimension"] == "diferenciacion" for item in comparison)
    assert all(item["text"] for item in comparison)
    assert all(item["url"] == "snapshot://feature/competitor_web_comparison" for item in comparison)
    assert all(item["classification_reason"] == "bounded_competitor_comparison_snapshot" for item in comparison)
    forbidden = ("leadership", "market advantage", "better product", "moat", "traction", "customer preference", "strategy")
    assert not any(term in item["text"].lower() for item in comparison for term in forbidden)


def test_diferenciacion_becomes_ready_with_two_competitor_comparison_items():
    packet = build_evidence_packet_v0(
        _linear_comparison_snapshot(
            {
                "avg_distance": 0.821,
                "closest_competitor": {"name": "Wrike", "distance": 0.752},
                "most_different": {"name": "ProjectManager", "distance": 0.872},
                "competitors_analyzed": 5,
            }
        )
    )

    readiness = packet["dimension_readiness"]["diferenciacion"]
    assert readiness["status"] == "ready"
    assert readiness["eligible_count"] == 2
    assert "competitor_corpus_present" in readiness["reason_codes"]
    assert "bounded_comparison_evidence" in readiness["reason_codes"]
    assert "no_strategy_inference" in readiness["reason_codes"]


def test_diferenciacion_becomes_thin_with_one_competitor_comparison_item():
    packet = build_evidence_packet_v0(
        _linear_comparison_snapshot(
            {
                "avg_distance": 0.821,
                "closest_competitor": {"name": "Wrike", "distance": 0.752},
                "competitors_analyzed": 5,
            }
        )
    )

    readiness = packet["dimension_readiness"]["diferenciacion"]
    assert readiness["status"] == "thin"
    assert readiness["eligible_count"] == 1


def test_entity_ambiguity_blocks_competitor_comparison_readiness():
    snapshot = _snapshot()
    snapshot["features"].append(
        _feature(
            "diferenciacion",
            "competitor_distance",
            "competitor_web_comparison",
            {
                "avg_distance": 0.821,
                "closest_competitor": {"name": "Wrike", "distance": 0.752},
                "most_different": {"name": "ProjectManager", "distance": 0.872},
                "competitors_analyzed": 5,
            },
        )
    )

    packet = build_evidence_packet_v0(snapshot)
    readiness = packet["dimension_readiness"]["diferenciacion"]
    assert readiness["status"] == "blocked"
    assert "entity_ambiguity_blocks_readiness" in readiness["reason_codes"]


def test_percepcion_can_be_ready_with_external_non_empty_evidence():
    packet = build_evidence_packet_v0(_snapshot())

    readiness = packet["dimension_readiness"]["percepcion"]
    assert readiness["status"] == "ready"
    assert readiness["eligible_count"] >= 2
    assert "empty_text_evidence_blocked" in readiness["reason_codes"]


def test_evidence_packet_module_has_no_network_or_llm_imports():
    source = Path("src/reports/evidence_packet.py").read_text()

    banned = [
        "requests",
        "httpx",
        "exa_py",
        "firecrawl",
        "playwright",
        "LLMAnalyzer",
        "google",
        "openai",
        "anthropic",
    ]
    assert not any(token in source for token in banned)


def test_builtwith_like_packet_contains_expected_categories():
    packet = build_evidence_packet_v0(_snapshot())

    assert packet["owned_claims"]
    assert packet["related_surface_evidence"]
    assert packet["technical_signals"]
    assert packet["trust_or_security_signals"]
    assert packet["visual_or_internal_signals"]
    assert packet["missing_evidence"]


def test_packet_is_json_serializable():
    json.dumps(build_evidence_packet_v0(_snapshot()))
