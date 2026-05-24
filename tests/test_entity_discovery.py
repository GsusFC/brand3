from src.collectors.exa_collector import ExaData, ExaResult
from src.discovery.calibration import apply_discovery_calibration_hint, build_discovery_calibration_hint
from src.discovery.entity_discovery import EntityDiscoveryResult, discover_entity
from src.discovery.evidence_preview import DiscoveryEvidencePreview, build_discovery_evidence_preview
from src.discovery.search_plan import DiscoverySearchPlan, build_discovery_search_plan
from src.niche.profiles import get_calibration_profile


def test_chatgpt_product_with_openai_parent():
    result = discover_entity("ChatGPT", "https://chatgpt.com")

    assert isinstance(result, EntityDiscoveryResult)
    assert result.input_name == "ChatGPT"
    assert result.input_url == "https://chatgpt.com"
    assert result.entity_name == "ChatGPT"
    assert result.entity_type == "product"
    assert result.analysis_scope == "product_with_parent"
    assert result.canonical_brand_name == "ChatGPT"
    assert result.canonical_url == "https://chatgpt.com"
    assert result.parent_brand_name == "OpenAI"
    assert result.parent_url == "https://openai.com"
    assert result.product_name == "ChatGPT"
    assert result.product_url == "https://chatgpt.com"
    assert result.confidence >= 0.9
    assert result.evidence
    assert result.warnings == []


def test_claude_product_with_anthropic_parent():
    result = discover_entity("Claude", "https://claude.ai")

    assert result.entity_name == "Claude"
    assert result.entity_type == "product"
    assert result.analysis_scope == "product_with_parent"
    assert result.canonical_brand_name == "Claude"
    assert result.canonical_url == "https://claude.ai"
    assert result.parent_brand_name == "Anthropic"
    assert result.parent_url == "https://anthropic.com"
    assert result.product_name == "Claude"
    assert result.product_url == "https://claude.ai"
    assert result.confidence >= 0.9


def test_openai_company_mode():
    result = discover_entity("OpenAI", "https://openai.com")

    assert result.entity_name == "OpenAI"
    assert result.entity_type == "company"
    assert result.analysis_scope == "company_brand"
    assert result.canonical_brand_name == "OpenAI"
    assert result.canonical_url == "https://openai.com"
    assert result.parent_brand_name is None
    assert result.product_name is None
    assert result.confidence >= 0.9


def test_anthropic_company_mode():
    result = discover_entity("Anthropic", "https://anthropic.com")

    assert result.entity_name == "Anthropic"
    assert result.entity_type == "company"
    assert result.analysis_scope == "company_brand"
    assert result.canonical_brand_name == "Anthropic"
    assert result.canonical_url == "https://anthropic.com"
    assert result.parent_brand_name is None
    assert result.product_name is None
    assert result.confidence >= 0.9


def test_base_protocol_ecosystem_mode():
    result = discover_entity("Base", "https://base.org")

    assert result.entity_name == "Base"
    assert result.entity_type == "protocol"
    assert result.analysis_scope == "ecosystem"
    assert result.canonical_brand_name == "Base"
    assert result.canonical_url == "https://base.org"
    assert result.parent_brand_name is None
    assert result.product_name is None
    assert result.confidence >= 0.85


def test_unknown_brand_fallback_when_domain_does_not_match():
    result = discover_entity("Obscure Thing", "https://example.com")

    assert result.entity_name == "Obscure Thing"
    assert result.entity_type == "unknown"
    assert result.analysis_scope == "url_only"
    assert result.canonical_brand_name == "Obscure Thing"
    assert result.canonical_url == "https://example.com"
    assert result.parent_brand_name is None
    assert result.product_name is None
    assert result.confidence <= 0.2
    assert "brand_domain_match_failed" in result.warnings


def test_generic_company_fallback_when_domain_matches_brand():
    result = discover_entity("Acme", "https://acme.com")

    assert result.entity_name == "Acme"
    assert result.entity_type == "company"
    assert result.analysis_scope == "company_brand"
    assert result.canonical_brand_name == "Acme"
    assert result.canonical_url == "https://acme.com"
    assert result.confidence >= 0.7


def test_chatgpt_search_plan_combines_openai_and_chatgpt():
    discovery = discover_entity("ChatGPT", "https://chatgpt.com")
    plan = build_discovery_search_plan(discovery, "ChatGPT", "https://chatgpt.com")

    assert isinstance(plan, DiscoverySearchPlan)
    assert plan.primary_entity == "OpenAI"
    assert plan.requested_entity == "ChatGPT"
    assert plan.analysis_mode == "product_with_parent"
    assert plan.queries == [
        "OpenAI ChatGPT brand positioning",
        "OpenAI ChatGPT product updates",
        "OpenAI ChatGPT reviews",
        "OpenAI ChatGPT competitors",
    ]
    assert plan.owned_urls == ["https://openai.com", "https://chatgpt.com"]


def test_claude_search_plan_combines_anthropic_and_claude():
    discovery = discover_entity("Claude", "https://claude.ai")
    plan = build_discovery_search_plan(discovery, "Claude", "https://claude.ai")

    assert plan.primary_entity == "Anthropic"
    assert plan.requested_entity == "Claude"
    assert plan.analysis_mode == "product_with_parent"
    assert plan.queries == [
        "Anthropic Claude brand positioning",
        "Anthropic Claude product updates",
        "Anthropic Claude reviews",
        "Anthropic Claude competitors",
    ]
    assert plan.owned_urls == ["https://anthropic.com", "https://claude.ai"]


def test_openai_search_plan_uses_company_queries():
    discovery = discover_entity("OpenAI", "https://openai.com")
    plan = build_discovery_search_plan(discovery, "OpenAI", "https://openai.com")

    assert plan.primary_entity == "OpenAI"
    assert plan.requested_entity == "OpenAI"
    assert plan.analysis_mode == "company_brand"
    assert plan.queries == [
        "OpenAI brand positioning",
        "OpenAI latest product updates",
        "OpenAI reviews reputation",
        "OpenAI competitors",
    ]
    assert plan.owned_urls == ["https://openai.com"]


def test_base_search_plan_uses_ecosystem_protocol_queries():
    discovery = discover_entity("Base", "https://base.org")
    plan = build_discovery_search_plan(discovery, "Base", "https://base.org")

    assert plan.primary_entity == "Base"
    assert plan.requested_entity == "Base"
    assert plan.analysis_mode == "ecosystem_or_protocol"
    assert plan.queries == [
        "Base ecosystem positioning",
        "Base protocol updates",
        "Base developer community",
        "Base competitors alternatives",
    ]
    assert plan.owned_urls == ["https://base.org"]


def test_chatgpt_evidence_preview_counts_owned_and_third_party_evidence():
    plan = build_discovery_search_plan(discover_entity("ChatGPT", "https://chatgpt.com"), "ChatGPT", "https://chatgpt.com")
    exa = ExaData(
        brand_name="ChatGPT",
        mentions=[
            ExaResult(url="https://openai.com/blog/chatgpt", title="OpenAI ChatGPT product updates"),
            ExaResult(url="https://chatgpt.com", title="ChatGPT by OpenAI"),
            ExaResult(url="https://techcrunch.com/story", title="OpenAI ChatGPT reviews"),
            ExaResult(url="https://theverge.com/story", title="ChatGPT competitors and reviews"),
            ExaResult(url="https://wired.com/story", title="OpenAI ChatGPT brand positioning"),
        ],
    )
    preview = build_discovery_evidence_preview(plan, exa_data=exa)

    assert isinstance(preview, DiscoveryEvidencePreview)
    assert preview.attempted is True
    assert preview.results_count == 5
    assert preview.owned_results_count == 2
    assert preview.third_party_results_count == 3
    assert preview.recommended_to_use_for_scoring is True
    assert preview.limitations == []


def test_claude_evidence_preview_matches_product_and_parent_terms():
    plan = build_discovery_search_plan(discover_entity("Claude", "https://claude.ai"), "Claude", "https://claude.ai")
    exa = ExaData(
        brand_name="Claude",
        mentions=[
            ExaResult(url="https://anthropic.com/news/claude", title="Anthropic Claude product updates"),
            ExaResult(url="https://claude.ai", title="Claude AI assistant"),
            ExaResult(url="https://techcrunch.com/claude", title="Anthropic launches Claude reviews"),
            ExaResult(url="https://theverge.com/claude", title="Claude competitors"),
            ExaResult(url="https://wired.com/anthropic", title="Anthropic Claude brand positioning"),
        ],
    )
    preview = build_discovery_evidence_preview(plan, exa_data=exa)

    assert preview.results_count == 5
    assert preview.owned_results_count == 2
    assert preview.third_party_results_count == 3
    assert preview.recommended_to_use_for_scoring is True


def test_base_evidence_preview_matches_ecosystem_protocol_terms():
    plan = build_discovery_search_plan(discover_entity("Base", "https://base.org"), "Base", "https://base.org")
    exa = ExaData(
        brand_name="Base",
        mentions=[
            ExaResult(url="https://base.org", title="Base protocol updates"),
            ExaResult(url="https://docs.base.org", title="Base developer community"),
            ExaResult(url="https://cointelegraph.com/base", title="Base ecosystem positioning"),
            ExaResult(url="https://decrypt.co/base", title="Base competitors alternatives"),
            ExaResult(url="https://blockworks.co/base", title="Base protocol developer community"),
        ],
    )
    preview = build_discovery_evidence_preview(plan, exa_data=exa)

    assert preview.results_count == 5
    assert preview.owned_results_count == 1
    assert preview.third_party_results_count == 4
    assert preview.official_domains == ["base.org"]
    assert preview.recommended_to_use_for_scoring is True


def test_evidence_preview_insufficient_evidence_is_not_recommended():
    plan = build_discovery_search_plan(discover_entity("OpenAI", "https://openai.com"), "OpenAI", "https://openai.com")
    exa = ExaData(
        brand_name="OpenAI",
        mentions=[
            ExaResult(url="https://openai.com", title="OpenAI brand positioning"),
            ExaResult(url="https://example.com/openai", title="OpenAI reviews"),
        ],
    )
    preview = build_discovery_evidence_preview(plan, exa_data=exa)

    assert preview.results_count == 2
    assert preview.recommended_to_use_for_scoring is False
    assert "insufficient_results" in preview.limitations
    assert "third_party_evidence_insufficient" in preview.limitations


def test_base_discovery_calibration_hint_recommends_ecosystem_profile():
    hint = build_discovery_calibration_hint(discover_entity("Base", "https://base.org"))

    assert hint["recommended_profile"] == "ecosystem_or_protocol"
    assert hint["reason"] == "entity_discovery.analysis_scope=ecosystem"
    assert hint["applied"] is False
    assert hint["current_behavior"] == "informational_only"


def test_claude_discovery_calibration_hint_product_with_parent():
    hint = build_discovery_calibration_hint(discover_entity("Claude", "https://claude.ai"))

    assert hint["recommended_profile"] == "product_with_parent"
    assert hint["applied"] is False
    assert hint["limitations"] == []


def test_chatgpt_discovery_calibration_hint_product_with_parent():
    hint = build_discovery_calibration_hint(discover_entity("ChatGPT", "https://chatgpt.com"))

    assert hint["recommended_profile"] == "product_with_parent"
    assert hint["reason"] == "entity_discovery.analysis_scope=product_with_parent"


def test_openai_discovery_calibration_hint_uses_current_niche():
    hint = build_discovery_calibration_hint(
        discover_entity("OpenAI", "https://openai.com"),
        niche_classification={"predicted_niche": "frontier_ai", "confidence": 0.77},
    )

    assert hint["recommended_profile"] == "frontier_ai"
    assert hint["reason"] == "company entity uses high-confidence niche classification"
    assert hint["confidence"] == 0.77
    assert hint["limitations"] == []


def test_company_discovery_calibration_hint_rejects_low_niche_confidence():
    hint = build_discovery_calibration_hint(
        discover_entity("Example", "https://example.com"),
        niche_classification={"predicted_niche": "base", "confidence": 0.55},
    )

    assert hint["recommended_profile"] == "base"
    assert hint["reason"] == "company entity without high-confidence niche classification"
    assert hint["confidence"] == 0.55
    assert "Niche classification confidence is below discovery calibration threshold." in hint["limitations"]


def test_company_discovery_calibration_hint_without_niche_uses_base():
    hint = build_discovery_calibration_hint(discover_entity("Example", "https://example.com"))

    assert hint["recommended_profile"] == "base"
    assert hint["reason"] == "company entity without niche confidence"


def test_unknown_discovery_calibration_hint_uses_base_with_url_limitation():
    hint = build_discovery_calibration_hint(discover_entity("Unknown", "https://example.com"))

    assert hint["recommended_profile"] == "base"
    assert hint["reason"] == "url_only discovery scope"
    assert "Audit basis is limited to the provided URL." in hint["limitations"]


def test_missing_discovery_calibration_hint_uses_base():
    hint = build_discovery_calibration_hint(None)

    assert hint["recommended_profile"] == "base"
    assert hint["reason"] == "missing_entity_discovery"
    assert hint["confidence"] == 0.0
    assert hint["limitations"] == ["Entity discovery was unavailable."]


def test_product_with_parent_profile_exists_and_is_manual():
    profile = get_calibration_profile("product_with_parent")

    assert profile["label"] == "Product with Parent"
    assert profile["description"]
    assert profile["auto_apply"] is False
    assert abs(sum(profile["dimension_weights"].values()) - 1.0) < 0.0001


def test_ecosystem_or_protocol_profile_exists_and_is_manual():
    profile = get_calibration_profile("ecosystem_or_protocol")

    assert profile["label"] == "Ecosystem / Protocol"
    assert profile["description"]
    assert profile["auto_apply"] is False
    assert abs(sum(profile["dimension_weights"].values()) - 1.0) < 0.0001


def test_discovery_calibration_decision_applies_when_all_gates_pass():
    decision = apply_discovery_calibration_hint(
        current_profile="base",
        current_profile_source="fallback",
        discovery_calibration_hint={"recommended_profile": "frontier_ai", "confidence": 0.9, "applied": False, "limitations": []},
        discovery_evidence_preview={"recommended_to_use_for_scoring": True},
        discovery_enrichment={"applied": True},
        available_profiles={"base", "frontier_ai"},
    )

    assert decision["calibration_profile"] == "frontier_ai"
    assert decision["profile_source"] == "discovery"
    assert decision["applied"] is True
    assert decision["previous_calibration_profile"] == "base"
    assert decision["reason"] == "discovery_calibration_gate_passed"


def test_discovery_calibration_decision_applies_product_with_parent_when_profile_exists():
    decision = apply_discovery_calibration_hint(
        current_profile="base",
        current_profile_source="fallback",
        discovery_calibration_hint={"recommended_profile": "product_with_parent", "confidence": 0.9, "applied": False, "limitations": []},
        discovery_evidence_preview={"recommended_to_use_for_scoring": True},
        discovery_enrichment={"applied": True},
        available_profiles={"base", "product_with_parent"},
    )

    assert decision["calibration_profile"] == "product_with_parent"
    assert decision["profile_source"] == "discovery"
    assert decision["applied"] is True


def test_discovery_calibration_decision_applies_ecosystem_or_protocol_when_profile_exists():
    decision = apply_discovery_calibration_hint(
        current_profile="base",
        current_profile_source="fallback",
        discovery_calibration_hint={"recommended_profile": "ecosystem_or_protocol", "confidence": 0.9, "applied": False, "limitations": []},
        discovery_evidence_preview={"recommended_to_use_for_scoring": True},
        discovery_enrichment={"applied": True},
        available_profiles={"base", "ecosystem_or_protocol"},
    )

    assert decision["calibration_profile"] == "ecosystem_or_protocol"
    assert decision["profile_source"] == "discovery"
    assert decision["applied"] is True


def test_discovery_calibration_decision_rejects_low_confidence():
    decision = apply_discovery_calibration_hint(
        current_profile="base",
        current_profile_source="fallback",
        discovery_calibration_hint={"recommended_profile": "frontier_ai", "confidence": 0.74, "applied": False, "limitations": []},
        discovery_evidence_preview={"recommended_to_use_for_scoring": True},
        discovery_enrichment={"applied": True},
        available_profiles={"base", "frontier_ai"},
    )

    assert decision["applied"] is False
    assert decision["reason"] == "low_confidence"


def test_discovery_calibration_decision_rejects_unrecommended_evidence():
    decision = apply_discovery_calibration_hint(
        current_profile="base",
        current_profile_source="fallback",
        discovery_calibration_hint={"recommended_profile": "frontier_ai", "confidence": 0.9, "applied": False, "limitations": []},
        discovery_evidence_preview={"recommended_to_use_for_scoring": False},
        discovery_enrichment={"applied": True},
        available_profiles={"base", "frontier_ai"},
    )

    assert decision["reason"] == "evidence_not_recommended"


def test_discovery_calibration_decision_rejects_missing_enrichment():
    decision = apply_discovery_calibration_hint(
        current_profile="base",
        current_profile_source="fallback",
        discovery_calibration_hint={"recommended_profile": "frontier_ai", "confidence": 0.9, "applied": False, "limitations": []},
        discovery_evidence_preview={"recommended_to_use_for_scoring": True},
        discovery_enrichment={"applied": False},
        available_profiles={"base", "frontier_ai"},
    )

    assert decision["reason"] == "discovery_enrichment_not_applied"


def test_discovery_calibration_decision_rejects_hint_limitations():
    decision = apply_discovery_calibration_hint(
        current_profile="base",
        current_profile_source="fallback",
        discovery_calibration_hint={"recommended_profile": "frontier_ai", "confidence": 0.9, "applied": False, "limitations": ["limited"]},
        discovery_evidence_preview={"recommended_to_use_for_scoring": True},
        discovery_enrichment={"applied": True},
        available_profiles={"base", "frontier_ai"},
    )

    assert decision["reason"] == "hint_has_limitations"


def test_discovery_calibration_decision_rejects_unavailable_profile():
    decision = apply_discovery_calibration_hint(
        current_profile="base",
        current_profile_source="fallback",
        discovery_calibration_hint={"recommended_profile": "ecosystem_or_protocol", "confidence": 0.9, "applied": False, "limitations": []},
        discovery_evidence_preview={"recommended_to_use_for_scoring": True},
        discovery_enrichment={"applied": True},
        available_profiles={"base", "frontier_ai"},
    )

    assert decision["reason"] == "recommended_profile_unavailable"


def test_discovery_calibration_decision_rejects_product_parent_without_profile():
    decision = apply_discovery_calibration_hint(
        current_profile="base",
        current_profile_source="fallback",
        discovery_calibration_hint={"recommended_profile": "product_with_parent", "confidence": 0.9, "applied": False, "limitations": []},
        discovery_evidence_preview={"recommended_to_use_for_scoring": True},
        discovery_enrichment={"applied": True},
        available_profiles={"base", "frontier_ai"},
    )

    assert decision["reason"] == "product_with_parent_profile_not_available"
