import pytest

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
