from __future__ import annotations

from src.reports.brand_research_pack import BrandResearchPack, EntityResolution, ResearchEvidence, ResearchSource
from src.research.research_pack_quality import evaluate_research_pack_quality, evaluate_research_pack_quality_gate


def test_research_pack_quality_passes_strong_traceable_pack() -> None:
    report = evaluate_research_pack_quality(_strong_pack())
    payload = report.to_dict()

    assert payload["version"] == "brand_research_pack_quality_v0_1"
    assert payload["status"] == "pass"
    assert payload["total_score"] >= 85.0
    assert payload["dimensions"]["offer"]["status"] == "pass"
    assert payload["dimensions"]["proof"]["status"] == "pass"
    assert evaluate_research_pack_quality_gate(report)["passed"]


def test_research_pack_quality_flags_noisy_product_summary() -> None:
    pack = _strong_pack()
    pack.product_summary = "Free Pro Enterprise"
    pack.offer = ""
    pack.noise_rejected = []

    report = evaluate_research_pack_quality(pack)
    payload = report.to_dict()

    assert payload["status"] == "fail"
    assert "missing_offer" in payload["dimensions"]["offer"]["reasons"]
    assert "product_summary_looks_like_noise" in payload["dimensions"]["offer"]["reasons"]
    assert payload["dimensions"]["noise"]["status"] == "fail"
    assert "noise_terms_in_product_summary" in payload["dimensions"]["noise"]["reasons"]
    assert not evaluate_research_pack_quality_gate(payload)["passed"]


def test_research_pack_quality_gate_fails_specific_low_dimensions() -> None:
    pack = _strong_pack()
    pack.audience = ""
    pack.proof_points = []
    pack.source_map = {}

    report = evaluate_research_pack_quality(pack)
    gate = evaluate_research_pack_quality_gate(report, min_total=50.0, min_dimension=60.0)

    assert report.dimensions["audience"].status == "fail"
    assert report.dimensions["proof"].status == "fail"
    assert report.dimensions["traceability"].status == "warn"
    assert not gate["passed"]
    assert any("dimension audience" in failure for failure in gate["failures"])
    assert any("dimension proof" in failure for failure in gate["failures"])


def _strong_pack() -> BrandResearchPack:
    url = "https://example.com"
    return BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url=url,
        resolved_entity=EntityResolution(resolved_entity="Example", entity_type="company", canonical_url=url),
        entity_type="company",
        official_urls=[url, "https://example.com/customers"],
        analyzed_urls=[url, "https://example.com/customers"],
        source_map={
            url: ResearchSource(url=url, source_type="owned_official", surface_role="audited_surface", entity_scope="audited_surface"),
            "https://example.com/customers": ResearchSource(
                url="https://example.com/customers",
                source_type="proof_point",
                surface_role="proof_points",
                entity_scope="audited_surface",
            ),
        },
        company_summary="Example helps operations teams automate complex approval workflows.",
        product_summary="Workflow automation platform for operations teams.",
        audience="Operations teams",
        offer="Workflow automation platform for operations teams.",
        outcome="Faster approval workflows with fewer manual handoffs.",
        category="workflow automation",
        visual_or_conceptual_signals=["Structured workflow-first interface."],
        attributes_signals=["reliable", "automated", "focused"],
        proof_points=[
            ResearchEvidence(
                text="Customer teams report faster approvals.",
                kind="proof",
                source_url="https://example.com/customers",
                source_type="proof_point",
                topic="customer_proof",
            )
        ],
        evidence_gaps=["Mission evidence remains thin."],
    )
