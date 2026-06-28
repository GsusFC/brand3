from src.sv9_flow.block_detection_worker import resolve_block_detection
from src.sv9_flow.contracts import BrandEvidencePack, EvidenceRecord


def test_values_detection_requires_explicit_values_language() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="features.0",
                source="legacy_feature",
                evidence_type="tone",
                content="Direct, pragmatic, human-centric tone with clarity and efficiency.",
            )
        ],
    )

    decision = resolve_block_detection("values", pack, evidence_refs=["features.0"])

    assert decision.outcome == "insufficient_evidence"
    assert decision.limitation_code == "values_structural_gate_rejected"


def test_values_detection_accepts_explicit_values_language() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="Our values are transparency, accountability, and care for customers.",
            )
        ],
    )

    decision = resolve_block_detection("values", pack, evidence_refs=["raw_inputs.0"])

    assert decision.outcome == "supports_detection"
    assert decision.support_terms == ["our values", "values are"]
    assert decision.limitation_code == ""


def test_values_detection_rejects_financial_value_language() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="Acme translates intangible assets into clear financial value for investors.",
            )
        ],
    )

    decision = resolve_block_detection("values", pack, evidence_refs=["raw_inputs.0"])

    assert decision.outcome == "insufficient_evidence"
    assert decision.support_terms == []


def test_vision_detection_accepts_explicit_future_language() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="Our vision is to become the next generation operating system for finance teams.",
            )
        ],
    )

    decision = resolve_block_detection("vision", pack, evidence_refs=["raw_inputs.0"])

    assert decision.outcome == "supports_detection"
    assert decision.support_terms == ["our vision", "vision is", "next generation"]


def test_vision_detection_rejects_positioning_inference() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="Acme helps financial teams translate intangible assets into defensible arguments.",
            )
        ],
    )

    decision = resolve_block_detection("vision", pack, evidence_refs=["raw_inputs.0"])

    assert decision.outcome == "insufficient_evidence"
    assert decision.limitation_code == "vision_structural_gate_rejected"


def test_magnetism_detection_rejects_visual_polish_only() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="visual_signature.tile.0",
                source="visual_signature",
                evidence_type="visual_tile_signal",
                content="Visual polish, distinctive copy, and confident first impression.",
            )
        ],
    )

    decision = resolve_block_detection("magnetism", pack, evidence_refs=["visual_signature.tile.0"])

    assert decision.outcome == "insufficient_evidence"
    assert decision.limitation_code == "magnetism_structural_gate_rejected"


def test_magnetism_detection_marks_negative_engagement_as_weakening_internal_state() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="report_narrative",
                evidence_type="raw_input",
                content=(
                    "The brand suffers from stagnation in digital activity and a lack of active engagement "
                    "across public social channels."
                ),
            )
        ],
    )

    decision = resolve_block_detection("magnetism", pack, evidence_refs=["raw_inputs.0"])

    assert decision.outcome == "weakens_detection"
    assert decision.limitation_code == "magnetism_structural_negative_evidence"
    assert decision.weaken_terms == ["lack of active engagement", "stagnation"]


def test_magnetism_detection_accepts_structural_momentum_evidence() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="Revenue growth, community engagement, and press momentum are visible in the evidence.",
            )
        ],
    )

    decision = resolve_block_detection("magnetism", pack, evidence_refs=["raw_inputs.0"])

    assert decision.outcome == "supports_detection"
    assert decision.support_terms == ["momentum", "engagement", "community", "revenue growth", "press"]


def test_non_sensitive_blocks_keep_existing_ref_gate_behavior() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(ref="raw_inputs.0", source="homepage", evidence_type="raw_input", content="Mission text.")
        ],
    )

    decision = resolve_block_detection("mission", pack, evidence_refs=["raw_inputs.0"])

    assert decision.outcome == "supports_detection"


def test_block_detection_decision_serializes_for_debug_payloads() -> None:
    pack = BrandEvidencePack(
        brand_name="Acme",
        url="https://acme.example",
        evidence=[
            EvidenceRecord(
                ref="raw_inputs.0",
                source="homepage",
                evidence_type="raw_input",
                content="Revenue growth and press momentum are visible.",
            )
        ],
    )

    decision = resolve_block_detection("magnetism", pack, evidence_refs=["raw_inputs.0"])

    assert decision.to_dict() == {
        "version": "sv9-flow-block-detection-policy-v1",
        "block": "magnetism",
        "outcome": "supports_detection",
        "evidence_refs": ["raw_inputs.0"],
        "support_terms": ["momentum", "revenue growth", "press"],
        "weaken_terms": [],
        "limitation_code": "",
    }
