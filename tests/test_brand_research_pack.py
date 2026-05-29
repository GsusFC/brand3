import json
from pathlib import Path

import pytest

from src.reports.brand_research_pack import (
    ALLOWED_ENTITY_TYPES,
    BrandResearchPack,
    EntityResolution,
    ResearchEvidence,
    ResearchSource,
)


FIXTURE_PATH = Path("examples/reports/brand_research_pack/minimal.brand_research_pack.v0.json")


def _pack() -> BrandResearchPack:
    return BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url="https://lab.example.com",
        resolved_entity=EntityResolution(
            resolved_entity="Example Co Lab",
            entity_type="product",
            canonical_url="https://lab.example.com",
            parent_brand="Example Co",
            surface_role="audited_surface",
            entity_scope="product_surface",
            confidence="medium",
            notes=["Resolved from subdomain context."],
        ),
        entity_type="product",
        parent_brand="Example Co",
        official_urls=["https://example.com", "https://lab.example.com"],
        analyzed_urls=["https://lab.example.com/about", "https://lab.example.com/privacy-policy"],
        source_map={
            "https://lab.example.com": ResearchSource(
                url="https://lab.example.com",
                source_type="owned",
                label="audited surface",
                surface_role="audited_surface",
                entity_scope="product_surface",
                title="Example Co Lab",
                notes=["Primary surface inspected."],
            ),
        },
        company_summary="Example Co operates a product lab surface.",
        product_summary="Example Co Lab presents the product surface under the parent brand.",
        audience="Builders who need a product surface.",
        offer="A product surface for experimentation.",
        outcome="Users can evaluate a clear product offer.",
        category="product surface",
        declared_purpose="Help users understand the product surface.",
        declared_mission="Ship a clearer product reading.",
        future_direction="Move from surface fragments to structured analysis.",
        tone_of_voice="clear and practical",
        personality_signals=["practical", "clear"],
        visual_or_conceptual_signals=["lab as product surface"],
        values_signals=["clarity", "structure"],
        attributes_signals=["practical", "organized"],
        proof_points=[
            ResearchEvidence(
                text="Case studies validate the product claim.",
                kind="proof",
                source_url="https://lab.example.com/case-studies",
                source_type="owned",
                source_label="case studies",
                surface_role="proof_points",
                entity_scope="product_surface",
                topic="validation",
            ),
        ],
        founder_or_press_context=[
            ResearchEvidence(
                text="Founder interview describes the product direction.",
                kind="context",
                source_url="https://news.example.com/interview",
                source_type="press",
                source_label="founder interview",
                surface_role="context",
                entity_scope="parent_brand",
                topic="founder_press",
            ),
        ],
        noise_rejected=[
            ResearchEvidence(
                text="top of page",
                kind="noise",
                source_url="https://lab.example.com",
                source_type="owned",
                source_label="page chrome",
                surface_role="chrome",
                entity_scope="product_surface",
                topic="page chrome",
                confidence="low",
            ),
        ],
        evidence_gaps=["No independent customer proof found."],
        confidence_notes=["Product surface is well resolved; vision remains thin."],
    )


def test_brand_research_pack_roundtrip_preserves_fields() -> None:
    pack = _pack()

    payload = pack.to_dict()
    rebuilt = BrandResearchPack.from_dict(payload)

    assert payload == rebuilt.to_dict()
    assert payload["resolved_entity"]["resolved_entity"] == "Example Co Lab"
    assert payload["source_map"]["https://lab.example.com"]["source_type"] == "owned"
    assert payload["proof_points"][0]["kind"] == "proof"
    assert payload["founder_or_press_context"][0]["kind"] == "context"
    assert payload["noise_rejected"][0]["kind"] == "noise"


def test_brand_research_pack_allows_empty_lists() -> None:
    pack = BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url="https://example.com",
        resolved_entity=EntityResolution(
            resolved_entity="Example Co",
            entity_type="brand",
        ),
        entity_type="brand",
        official_urls=[],
        analyzed_urls=[],
        source_map={},
        personality_signals=[],
        visual_or_conceptual_signals=[],
        values_signals=[],
        attributes_signals=[],
        proof_points=[],
        founder_or_press_context=[],
        noise_rejected=[],
        evidence_gaps=[],
        confidence_notes=[],
    )

    payload = pack.to_dict()

    assert payload["official_urls"] == []
    assert payload["analyzed_urls"] == []
    assert payload["source_map"] == {}
    assert payload["proof_points"] == []
    assert payload["noise_rejected"] == []


def test_brand_research_pack_validates_entity_type() -> None:
    with pytest.raises(ValueError):
        BrandResearchPack(
            version="brand_research_pack_v0_1",
            input_url="https://example.com",
            resolved_entity=EntityResolution(resolved_entity="Example Co", entity_type="brand"),
            entity_type="platform",
        )


def test_brand_research_pack_distinguishes_evidence_context_and_noise() -> None:
    pack = _pack()
    payload = pack.to_dict()

    assert payload["proof_points"][0]["kind"] == "proof"
    assert payload["founder_or_press_context"][0]["kind"] == "context"
    assert payload["noise_rejected"][0]["kind"] == "noise"
    assert payload["proof_points"][0]["text"] != payload["founder_or_press_context"][0]["text"]


def test_brand_research_pack_example_serializes() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    rebuilt = BrandResearchPack.from_dict(payload)

    assert rebuilt.to_dict() == payload
    assert rebuilt.entity_type in ALLOWED_ENTITY_TYPES
