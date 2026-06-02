from __future__ import annotations

import pytest

from src.reports.brand_research_pack import (
    BrandResearchPack,
    EntityResolution,
    ResearchEvidence,
    ResearchSource,
)
from src.research.research_pack_contract import (
    assert_brand_research_pack_contract,
    validate_brand_research_pack_contract,
)


def _valid_pack() -> BrandResearchPack:
    return BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url="https://example.com",
        resolved_entity=EntityResolution(
            resolved_entity="Example",
            entity_type="company",
            canonical_url="https://example.com",
            confidence="medium",
        ),
        entity_type="company",
        official_urls=["https://example.com"],
        analyzed_urls=["https://example.com", "https://example.com/customers"],
        source_map={
            "https://example.com": ResearchSource(
                url="https://example.com",
                source_type="owned_official",
                label="home",
            ),
            "https://example.com/customers": ResearchSource(
                url="https://example.com/customers",
                source_type="proof_point",
                label="customers",
            ),
        },
        company_summary="Example offers workflow software.",
        offer="Workflow software for operations teams.",
        audience="Operations teams.",
        outcome="Teams coordinate work faster.",
        proof_points=[
            ResearchEvidence(
                text="Trusted by operations teams.",
                kind="proof",
                source_url="https://example.com/customers",
                source_type="proof_point",
            )
        ],
        evidence_gaps=["Mission language remains thin."],
    )


def test_research_pack_contract_accepts_traceable_pack() -> None:
    report = validate_brand_research_pack_contract(_valid_pack())

    assert report.passed
    assert report.to_dict()["version"] == "brand_research_pack_contract_v0_1"
    assert report.errors == ()


def test_research_pack_contract_rejects_invalid_identity_url() -> None:
    pack = _valid_pack()
    pack.input_url = "example"

    report = validate_brand_research_pack_contract(pack)

    assert not report.passed
    assert any(issue.code == "invalid_input_url" for issue in report.errors)


def test_research_pack_contract_rejects_untraced_evidence_source() -> None:
    pack = _valid_pack()
    pack.proof_points[0].source_url = "https://external.example/review"

    report = validate_brand_research_pack_contract(pack)

    assert not report.passed
    assert any(issue.code == "untraced_evidence_source" for issue in report.errors)


def test_research_pack_contract_rejects_empty_pack_without_gap() -> None:
    pack = BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url="https://example.com",
        resolved_entity=EntityResolution(resolved_entity="Example", entity_type="company"),
        entity_type="company",
        source_map={
            "https://example.com": ResearchSource(
                url="https://example.com",
                source_type="owned_official",
                label="home",
            )
        },
    )

    report = validate_brand_research_pack_contract(pack)

    assert not report.passed
    assert any(issue.code == "empty_pack_without_gap" for issue in report.errors)


def test_assert_research_pack_contract_raises_readable_summary() -> None:
    pack = _valid_pack()
    pack.official_urls = ["not-a-url"]

    with pytest.raises(ValueError, match="official_urls.0"):
        assert_brand_research_pack_contract(pack)
