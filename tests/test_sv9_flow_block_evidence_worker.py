from src.sv9_flow.block_evidence_worker import (
    BLOCK_EVIDENCE_SHORTLIST_VERSION,
    BlockEvidenceShortlist,
    build_block_evidence_shortlists,
)
from src.sv9_flow.contracts import BrandEvidencePack, EvidenceRecord


def test_block_evidence_shortlists_are_deterministic_and_block_specific() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="Acme helps teams ship faster.",
            ),
            EvidenceRecord(
                ref="features.0",
                source="legacy_feature",
                evidence_type="coherencia.tone_consistency",
                content="The brand voice is direct, pragmatic, professional, and human.",
                confidence="high",
            ),
            EvidenceRecord(
                ref="features.1",
                source="legacy_feature",
                evidence_type="diferenciacion.positioning_clarity",
                content="The brand idea is a distinctive platform concept.",
                confidence="high",
            ),
        ],
    )

    shortlists = build_block_evidence_shortlists(
        pack,
        blocks=("personality", "brand_idea"),
        limit=2,
    )

    assert shortlists == build_block_evidence_shortlists(pack, blocks=("personality", "brand_idea"), limit=2)
    assert shortlists["personality"][0] == "features.0"
    assert shortlists["brand_idea"][0] == "features.1"


def test_block_evidence_shortlist_serializes_version() -> None:
    item = BlockEvidenceShortlist(block="vision", evidence_refs=["raw_inputs.0"])

    assert item.to_dict() == {
        "version": BLOCK_EVIDENCE_SHORTLIST_VERSION,
        "block": "vision",
        "evidence_refs": ["raw_inputs.0"],
    }


def test_brand_idea_shortlist_prefers_textual_evidence_over_visual_signature_when_available() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="visual_signature.tile_signals.0",
                source="visual_signature",
                evidence_type="visual_tile_signal",
                content="Distinctive visual signature supports a brand idea.",
            ),
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="The core brand idea is an ownable platform methodology.",
            ),
        ],
    )

    shortlists = build_block_evidence_shortlists(pack, blocks=("brand_idea",), limit=2)

    assert shortlists["brand_idea"][0] == "raw_inputs.0"


def test_brand_idea_shortlist_prioritizes_uniqueness_and_vocabulary_features() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="visual_signature",
                evidence_type="raw_input",
                content="Visual signature agreement payload with visual signature metrics.",
            ),
            EvidenceRecord(
                ref="features.0",
                source="legacy_feature",
                evidence_type="diferenciacion.uniqueness",
                content="unique_phrases and brand_vocabulary show an ownable differentiator_claimed.",
                confidence="high",
            ),
        ],
    )

    shortlists = build_block_evidence_shortlists(pack, blocks=("brand_idea",), limit=2)

    assert shortlists["brand_idea"][0] == "features.0"


def test_value_proposition_shortlist_prioritizes_financial_value_claims() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="features.0",
                source="legacy_feature",
                evidence_type="coherencia.visual_consistency",
                content="Visual consistency and corporate style.",
                confidence="high",
            ),
            EvidenceRecord(
                ref="features.1",
                source="legacy_feature",
                evidence_type="diferenciacion.uniqueness",
                content="Traduce a euros el impacto del trabajo and turns intangibles into capital arguments.",
                confidence="high",
            ),
        ],
    )

    shortlists = build_block_evidence_shortlists(pack, blocks=("value_proposition",), limit=2)

    assert shortlists["value_proposition"][0] == "features.1"
