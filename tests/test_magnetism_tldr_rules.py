from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.features.magnetism.extractor import MagnetismExtractor

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "magnetism"


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _content_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def _assert_v03_contract(block_name: str, block: dict[str, Any]) -> None:
    for key in [
        "block",
        "question",
        "evidence_scope",
        "source_signal",
        "source_signal_path",
        "source_layer",
        "observations",
        "answer",
        "claim_type",
        "mode",
        "confidence",
        "reasoning",
        "evidence_used",
        "counter_evidence",
        "human_review_recommended",
    ]:
        assert key in block, (block_name, key)
    assert block["block"] == block_name
    assert block["claim_type"] in {"declared", "performed", "inferred", "absent"}
    assert block["confidence"] in {"high", "medium", "low"}
    assert isinstance(block["evidence_scope"], list)
    assert block["source_signal"]
    assert "→" in block["source_signal_path"]
    assert block["source_layer"]
    assert isinstance(block["observations"], list)
    assert isinstance(block["evidence_used"], list)
    assert isinstance(block["counter_evidence"], list)


def test_mediterranean_algae_fixture_matches_tldr_v02_contract() -> None:
    fixture = _load_fixture("mediterranean_algae_tldr_v02.json")
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text=fixture["evidence_text"],
        brand_name=fixture["brand_name"],
    )

    tldr = result["tldr_brand3"]
    for block_name, expectation in fixture["expected"].items():
        block = tldr[block_name]
        _assert_v03_contract(block_name, block)
        assert block["detected"], block_name
        assert block["mode"] == expectation["mode"], block_name
        assert block["confidence"] in expectation["confidence_any_of"], block_name
        assert block["evidence"], block_name
        assert block["rationale"], block_name
        assert block["source_layers"], block_name
        content = _content_text(block["content"]).lower()
        assert any(term.lower() in content for term in expectation["content_contains_any"]), (
            block_name,
            block["content"],
        )


def test_personality_can_be_interpreted_from_discourse_without_literal_personality_phrase() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text=(
            "Soluciones con macroalgas para cosmética, nutrición y biorremediación. "
            "Creamos materias primas funcionales con origen mediterráneo. "
            "Modelo regenerativo, circular y comprometido con el medio ambiente."
        ),
        brand_name="Implicit Personality",
    )

    personality = result["tldr_brand3"]["personality"]
    assert personality["detected"] is True
    assert personality["claim_type"] == "performed"
    assert personality["mode"] == "interpreted_from_discourse"
    assert "Sage" in personality["content"] or "Caregiver" in personality["content"]
    assert personality["evidence_used"]
    assert personality["reasoning"]


def test_cta_only_does_not_create_mission_or_vision() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text="Contact us. Book a demo. Subscribe now. Pricing. Buy now.",
        brand_name="CTA Only",
    )

    assert result["tldr_brand3"]["mission"]["detected"] is False
    assert result["tldr_brand3"]["mission"]["mode"] == "not_detected"
    assert result["tldr_brand3"]["mission"]["claim_type"] == "absent"
    assert result["tldr_brand3"]["mission"]["evidence_used"] == []
    assert result["tldr_brand3"]["vision"]["detected"] is False
    assert result["tldr_brand3"]["vision"]["mode"] == "not_detected"
    assert result["tldr_brand3"]["vision"]["claim_type"] == "absent"


def test_value_proposition_does_not_use_menu_when_offer_signal_exists() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text=(
            "Main Menu Activos marinos Contacto Nuestras soluciones. "
            "Soluciones con macroalgas para cosmética, nutrición y biorremediación."
        ),
        brand_name="Menu Plus Offer",
    )

    value_prop = result["tldr_brand3"]["value_proposition"]
    assert value_prop["detected"] is True
    assert value_prop["claim_type"] == "declared"
    assert "Main Menu" not in _content_text(value_prop["content"])
    assert "cosmética" in _content_text(value_prop["content"])


def test_vision_requires_future_state_language() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text="Creamos materias primas funcionales con origen mediterráneo para cosmética.",
        brand_name="No Vision",
    )

    assert result["tldr_brand3"]["mission"]["detected"] is True
    assert result["tldr_brand3"]["mission"]["claim_type"] == "declared"
    assert result["tldr_brand3"]["vision"]["detected"] is False


def test_tldr_v03_contract_is_present_for_every_block() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text=(
            "Just Do It. para inspirar a todo tipo de atletas. "
            "Creamos productos innovadores para performance deportiva. "
            "Construimos el futuro del deporte para todo tipo de atletas."
        ),
        brand_name="Contract Brand",
    )

    for block_name, block in result["tldr_brand3"].items():
        _assert_v03_contract(block_name, block)


def test_inferred_strategic_blocks_show_limits_and_review_when_weak() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text="Just Do It. Zapatillas para maratón.",
        brand_name="Sparse Action Brand",
    )

    brand_idea = result["tldr_brand3"]["brand_idea"]
    personality = result["tldr_brand3"]["personality"]
    assert personality["detected"] is True
    assert personality["claim_type"] == "performed"
    assert personality["mode"] == "interpreted_from_discourse"
    assert personality["counter_evidence"]
    if brand_idea["detected"]:
        assert brand_idea["claim_type"] == "inferred"
        assert brand_idea["human_review_recommended"] is True


def test_executable_mission_spec_rejects_future_and_cta_language() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text=(
            "Book a demo. Pricing. Buy now. "
            "Our vision is the future of treasury operations. "
            "A new model for finance teams."
        ),
        brand_name="Future CTA Brand",
    )

    mission = result["tldr_brand3"]["mission"]
    assert mission["detected"] is False
    assert mission["claim_type"] == "absent"
    assert mission["mode"] == "not_detected"


def test_executable_mission_spec_accepts_present_operating_activity() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text="We build treasury infrastructure for finance teams.",
        brand_name="Operating Brand",
    )

    mission = result["tldr_brand3"]["mission"]
    assert mission["detected"] is True
    assert mission["claim_type"] == "declared"
    assert mission["mode"] == "compressed"
    assert "present-tense operating" in mission["reasoning"]
    assert "We build treasury infrastructure" in mission["answer"]


def test_executable_vision_spec_rejects_current_offer_without_future_signal() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text="We build treasury infrastructure for finance teams. Treasury platform for cash visibility.",
        brand_name="No Future Brand",
    )

    vision = result["tldr_brand3"]["vision"]
    assert vision["detected"] is False
    assert vision["claim_type"] == "absent"


def test_executable_vision_spec_accepts_future_category_change() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text="We are building the future of corporate treasury: a new model for real-time finance operations.",
        brand_name="Future Vision Brand",
    )

    vision = result["tldr_brand3"]["vision"]
    assert vision["detected"] is True
    assert vision["claim_type"] == "inferred"
    assert vision["mode"] == "interpreted_from_discourse"
    assert "future-facing" in vision["reasoning"]


def test_executable_value_proposition_spec_marks_missing_audience_and_outcome() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text="Treasury platform.",
        brand_name="Sparse VP Brand",
    )

    value_prop = result["tldr_brand3"]["value_proposition"]
    assert value_prop["detected"] is True
    assert value_prop["confidence"] == "low"
    assert value_prop["human_review_recommended"] is True
    assert any("audience" in item for item in value_prop["counter_evidence"])
    assert any("outcome" in item for item in value_prop["counter_evidence"])
    assert "offer=" in " ".join(value_prop["observations"])




def test_system_reading_places_reverse_engineering_inside_tldr() -> None:
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text="Treasury platform for cash visibility and reconciliation.",
        brand_name="System Reading Brand",
    )

    summary = result["evidence_packet_summary"]
    reading = result["system_reading"]

    assert summary["source"] == "manual_evidence"
    assert summary["detected_signal_count"] >= 1
    assert reading["strategic_tensions"]
    assert reading["validation_questions"]
    assert any("brand voice" in item or "brand idea" in item for item in reading["strategic_tensions"])
    assert reading["derived_from"] == "TLDR Brand3 blocks and Magenta signal coverage"

def test_iconic_action_brand_can_derive_personality_and_brand_idea() -> None:
    fixture = _load_fixture("nike_tldr_v02.json")
    result = MagnetismExtractor(llm=None).extract(
        url=None,
        manual_text=fixture["evidence_text"],
        brand_name=fixture["brand_name"],
    )

    metrics = result["metrics"]
    assert metrics["magnetism_score"] >= fixture["expected"]["magnetism"]["min_score"]
    assert metrics["magnetism_tier"] == fixture["expected"]["magnetism"]["tier"]

    tldr = result["tldr_brand3"]
    for block_name in ["personality", "brand_idea"]:
        expectation = fixture["expected"][block_name]
        block = tldr[block_name]
        _assert_v03_contract(block_name, block)
        assert block["detected"], block_name
        assert block["mode"] == expectation["mode"], block_name
        assert block["confidence"] in expectation["confidence_any_of"], block_name
        content = _content_text(block["content"]).lower()
        assert any(term.lower() in content for term in expectation["content_contains_any"]), (
            block_name,
            block["content"],
        )

    for block_name in ["attributes", "values"]:
        block = tldr[block_name]
        assert block["detected"], block_name
        content = _content_text(block["content"]).lower()
        assert any(
            term.lower() in content for term in fixture["expected"][block_name]["content_contains_any"]
        ), (block_name, block["content"])
