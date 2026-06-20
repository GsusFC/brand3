import pytest

from src.classification.market_classifier import classify_market_heuristic
from src.classification.market_llm_classifier import classify_market_llm, market_llm_response_schema
from src.classification.market_taxonomy import canonical_tag, tag_definition, tags_for_group
from src.classification.schemas import ClassificationTag, MarketClassification


def test_taxonomy_normalizes_aliases_without_copying_external_categories():
    assert canonical_tag("technology_capability", "genAI") == "generative AI"
    assert canonical_tag("technology_capability", "api") == "API"
    assert canonical_tag("corporate_status", "became subsidiary") == "subsidiary"
    assert "B2B" in tags_for_group("business_model")
    assert tag_definition("technology_capability", "gen ai").definition


def test_classification_tag_rejects_unknown_tags():
    with pytest.raises(ValueError):
        ClassificationTag(
            group="technology_capability",
            tag="magic category",
            confidence="medium",
        )


def test_market_classification_serializes_reviewable_tags():
    classification = MarketClassification(
        brand_key="Linear",
        tags=[
            ClassificationTag(
                group="business_model",
                tag="saas",
                confidence="high",
                status="accepted",
                evidence_text="Linear is a hosted issue tracking product.",
            ),
            ClassificationTag(
                group="sector_industry",
                tag="project management",
                confidence="medium",
                status="proposed",
                evidence_text="Issue tracking and project planning.",
            ),
        ],
    )

    payload = classification.to_dict()
    assert payload["brand_key"] == "linear"
    assert payload["requires_human_review"] is True
    assert payload["accepted"]["business_model"] == ["SaaS"]
    assert payload["proposed"]["sector_industry"] == ["project management"]

    restored = MarketClassification.from_dict(payload)
    assert restored.to_dict() == payload


def test_heuristic_classifier_accepts_only_obvious_signals_and_proposes_inferred_context():
    classification = classify_market_heuristic(
        brand_key="acme",
        domain="acme.test",
        evidence=[
            {
                "text": "A SaaS platform for teams with pricing per seat per month.",
                "url": "https://acme.test/pricing",
                "source_type": "owned",
            },
            {
                "text": "Generate content with generative AI and image generation workflows.",
                "url": "https://acme.test/product",
                "source_type": "owned",
            },
        ],
    )
    accepted = classification.tags_by_group(status="accepted")
    proposed = classification.tags_by_group(status="proposed")

    assert accepted["business_model"] == ["B2B", "SaaS", "subscription"]
    assert accepted["corporate_status"] == ["active"]
    assert proposed["technology_capability"] == ["image generation", "generative AI"]
    assert classification.requires_human_review is True


def test_heuristic_classifier_does_not_match_api_inside_words():
    classification = classify_market_heuristic(
        brand_key="mafer",
        domain="mafer.test",
        evidence=[
            {
                "text": "Private investment and holding capital group.",
                "url": "https://mafer.test",
                "source_type": "owned",
            }
        ],
    )

    assert "API" not in classification.tags_by_group(status="accepted")["technology_capability"]


def test_llm_market_classifier_uses_structured_taxonomy_schema():
    class FakeLLM:
        api_key = "test"
        model = "gemini-3.5-flash"
        base_url = "https://example.test/openai"

        def __init__(self):
            self.calls = []

        def _call_json(self, system, user, max_tokens=8000, **kwargs):
            self.calls.append(
                {
                    "system": system,
                    "user": user,
                    "max_tokens": max_tokens,
                    **kwargs,
                }
            )
            return {
                "items": [
                    {
                        "group": "sector_industry",
                        "tag": "artificial intelligence",
                        "confidence": "medium",
                        "evidence_text": "The product automates workflows with AI agents.",
                        "source_url": "https://acme.test",
                        "reason_codes": ["semantic_product_category"],
                    },
                    {
                        "group": "technology_capability",
                        "tag": "generative AI",
                        "confidence": "medium",
                        "evidence_text": "The product generates campaign content.",
                        "source_url": "https://acme.test",
                        "reason_codes": ["semantic_capability"],
                    },
                ]
            }

    llm = FakeLLM()

    classification = classify_market_llm(
        brand_key="acme",
        domain="acme.test",
        evidence=[
            {
                "text": "AI agents that generate campaign content for marketing teams.",
                "url": "https://acme.test",
                "source_type": "profile",
            }
        ],
        llm=llm,
    )

    assert classification is not None
    assert classification.tags_by_group(status="proposed")["sector_industry"] == [
        "artificial intelligence"
    ]
    assert classification.tags_by_group(status="proposed")["technology_capability"] == [
        "generative AI"
    ]
    assert llm.calls[0]["json_schema"] == market_llm_response_schema()
    assert llm.calls[0]["strict_schema"] is True
