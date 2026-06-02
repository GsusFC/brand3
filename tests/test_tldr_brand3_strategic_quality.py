from __future__ import annotations

import json
from pathlib import Path

from src.reports.tldr_brand3_research_pack_evaluation import build_strategic_quality_report
from src.reports.tldr_brand3_research_pack_evaluation import (
    DEFAULT_DATASET_PATH,
    DEFAULT_STRATEGIC_QUALITY_CASES_PATH,
    build_strategic_quality_markdown_report,
    build_strategic_quality_cases_from_benchmark,
    evaluate_strategic_quality_gate,
    main,
    run_strategic_quality_evaluation,
)


def _source(url: str, source_type: str) -> dict:
    return {
        "url": url,
        "source_type": source_type,
        "label": source_type,
        "surface_role": "audited_surface",
        "entity_scope": "audited_surface",
        "title": "",
        "notes": [],
    }


def _block(
    answer: str,
    *,
    source_url: str,
    source_type: str = "owned_official",
    claim_type: str = "declared",
    counter_evidence: list[str] | None = None,
) -> dict:
    return {
        "answer": answer,
        "claim_type": claim_type,
        "confidence": "medium",
        "evidence_used": [answer],
        "evidence_sources": [
            {
                "source_key": source_url,
                "source_type": source_type,
                "url": source_url,
                "label": source_type,
            }
        ],
        "counter_evidence": counter_evidence or [],
    }


def _case(
    slug: str,
    *,
    archetype: str,
    url: str,
    value_proposition: str,
    brand_idea: str,
    source_type: str = "owned_official",
    entity_type: str = "company",
    parent_brand: str = "",
    gaps: list[str] | None = None,
    expectations: dict | None = None,
) -> dict:
    return {
        "slug": slug,
        "source_url": url,
        "archetype": archetype,
        "research_pack": {
            "version": "brand_research_pack_v0_1",
            "input_url": url,
            "entity_type": entity_type,
            "parent_brand": parent_brand,
            "official_urls": [url],
            "analyzed_urls": [url],
            "source_map": {url: _source(url, source_type)},
            "evidence_gaps": gaps or ["Mission evidence remains thin."],
        },
        "analyst_tldr": {
            "tldr_brand3": {
                "value_proposition": _block(value_proposition, source_url=url, source_type=source_type),
                "brand_idea": _block(brand_idea, source_url=url, source_type=source_type, claim_type="inferred"),
                "mission": _block(
                    "Mission evidence remains thin.",
                    source_url=url,
                    source_type=source_type,
                    claim_type="inferred",
                    counter_evidence=gaps or ["Mission evidence remains thin."],
                ),
            }
        },
        "strategic_expectations": expectations or {
            "offer": {"must_include_any": [[value_proposition.split()[0]]]},
            "audience": {"must_include_any": [["teams", "customers", "operators", "buyers", "brands"]]},
            "differentiation": {"must_include_any": [[brand_idea.split()[0]]]},
            "frictions": {"must_acknowledge": ["thin"], "require_counter_evidence": True},
            "evidence_traceability": {"require_traceable_sources": True, "forbid_source_types": ["noise"]},
            "entity_separation": {"forbid_press_as_declared_mission": True},
        },
    }


def test_strategic_quality_report_scores_industry_archetype_fixtures() -> None:
    cases = [
        _case(
            "langchain-like",
            archetype="multiproduct_saas",
            url="https://langchain.example",
            value_proposition="Agent engineering platform for AI teams building reliable agents.",
            brand_idea="Reliability layer for agent engineering across products.",
            expectations={
                "offer": {"must_include": ["agent engineering platform"], "must_not_include": ["LangSmith only"]},
                "audience": {"must_include": ["AI teams"]},
                "differentiation": {"must_include": ["reliability layer"]},
                "frictions": {"must_acknowledge": ["thin"], "require_counter_evidence": True},
                "evidence_traceability": {"require_traceable_sources": True, "forbid_source_types": ["noise"]},
                "entity_separation": {"company_offer_must_not_include": ["LangSmith only"]},
            },
        ),
        _case(
            "single-product-saas",
            archetype="single_product_saas",
            url="https://saas.example",
            value_proposition="Workflow automation software for operations teams.",
            brand_idea="Operational clarity through automated workflows.",
        ),
        _case(
            "retail",
            archetype="ecommerce",
            url="https://retail.example",
            value_proposition="Durable home goods for design-conscious buyers.",
            brand_idea="Quiet durability as a retail promise.",
        ),
        _case(
            "agency",
            archetype="service_business",
            url="https://agency.example",
            value_proposition="Brand strategy services for scaling companies.",
            brand_idea="Sharper positioning through evidence-led strategy.",
            expectations={
                "offer": {"must_include": ["brand strategy services"]},
                "audience": {"must_include": ["scaling companies"]},
                "differentiation": {"must_include": ["evidence-led strategy"]},
                "frictions": {"must_acknowledge": ["thin"], "require_counter_evidence": True},
                "evidence_traceability": {"require_traceable_sources": True, "forbid_source_types": ["noise"]},
                "entity_separation": {"forbid_press_as_declared_mission": True},
            },
        ),
        _case(
            "product-subdomain",
            archetype="parent_brand_product_surface",
            url="https://lab.example.com",
            value_proposition="AI assistant product for teams under Example Parent.",
            brand_idea="Parent-backed product lab for practical AI assistance.",
            entity_type="product",
            parent_brand="Example Parent",
            expectations={
                "offer": {"must_include": ["AI assistant product"]},
                "audience": {"must_include": ["teams"]},
                "differentiation": {"must_include": ["parent-backed"]},
                "frictions": {"must_acknowledge": ["thin"], "require_counter_evidence": True},
                "evidence_traceability": {"require_traceable_sources": True, "forbid_source_types": ["noise"]},
                "entity_separation": {"require_parent_context": True},
            },
        ),
        _case(
            "press-context",
            archetype="founder_press_heavy",
            url="https://pressy.example",
            value_proposition="Planning software for founder-led teams.",
            brand_idea="Founder-led planning with operational discipline.",
        ),
        _case(
            "noise-heavy",
            archetype="noise_heavy_site",
            url="https://noise.example",
            value_proposition="Prediction platform for crypto traders.",
            brand_idea="Trading signals without page-feed chrome.",
            expectations={
                "offer": {"must_include": ["prediction platform"]},
                "audience": {"must_include": ["crypto traders"]},
                "differentiation": {"must_include": ["trading signals"]},
                "frictions": {"must_acknowledge": ["thin"], "require_counter_evidence": True},
                "evidence_traceability": {"require_traceable_sources": True, "forbid_source_types": ["noise"]},
                "entity_separation": {"forbid_press_as_declared_mission": True},
            },
        ),
    ]

    report = build_strategic_quality_report(cases)

    assert report["version"] == "tldr_brand3_strategic_quality_v0_1"
    assert report["case_count"] == 7
    assert report["total_score"] >= 90.0
    assert set(report["dimension_scores"]) == {
        "audience",
        "differentiation",
        "entity_separation",
        "evidence_traceability",
        "frictions",
        "offer",
        "personality",
        "vision",
    }
    assert all(not case["failures"] for case in report["case_evaluations"])


def test_strategic_quality_report_detects_real_strategic_regressions() -> None:
    bad_case = _case(
        "bad-langchain",
        archetype="multiproduct_saas",
        url="https://langchain.example",
        value_proposition="LangSmith only observability product.",
        brand_idea="Navigation feed article chrome.",
        source_type="noise",
        expectations={
            "offer": {
                "must_include": ["agent engineering platform"],
                "must_not_include": ["LangSmith only"],
            },
            "audience": {"must_include": ["AI teams"]},
            "differentiation": {"must_include": ["reliability layer"], "must_not_include": ["chrome"]},
            "frictions": {"must_acknowledge": ["mission"], "require_counter_evidence": True},
            "evidence_traceability": {"require_traceable_sources": True, "forbid_source_types": ["noise"]},
            "entity_separation": {
                "company_offer_must_not_include": ["LangSmith only"],
                "forbid_press_as_declared_mission": True,
            },
        },
    )
    bad_case["analyst_tldr"]["tldr_brand3"]["mission"] = _block(
        "The founder says the company will define the future of agents.",
        source_url="https://press.example/story",
        source_type="press_or_founder",
        claim_type="declared",
    )
    bad_case["research_pack"]["source_map"]["https://press.example/story"] = _source(
        "https://press.example/story",
        "press_or_founder",
    )
    bad_case["research_pack"]["analyzed_urls"].append("https://press.example/story")

    report = build_strategic_quality_report([bad_case])
    failures = " ".join(report["case_evaluations"][0]["failures"])

    assert report["total_score"] < 70.0
    assert "offer_missing_required_term" in failures
    assert "offer_contains_forbidden_term" in failures
    assert "audience_missing_required_term" in failures
    assert "forbidden_source_type" in failures
    assert "product_offer_used_as_company_offer" in failures
    assert "founder_press_as_declared_mission" in failures
    assert report["taxonomy_counts"]["founder_press_as_declared_mission"] == 1
    assert report["recommendations"]


def test_strategic_quality_runner_writes_artifacts(tmp_path: Path) -> None:
    report = run_strategic_quality_evaluation(
        cases_path=DEFAULT_STRATEGIC_QUALITY_CASES_PATH,
        out_dir=tmp_path,
    )

    json_path = tmp_path / "strategic_quality.json"
    md_path = tmp_path / "strategic_quality.md"

    assert report["version"] == "tldr_brand3_strategic_quality_v0_1"
    assert report["case_count"] >= 4
    assert json_path.exists()
    assert md_path.exists()
    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert written == report
    markdown = md_path.read_text(encoding="utf-8")
    assert "# TLDR Brand3 strategic quality evaluation" in markdown
    assert "## Dimension Scores" in markdown
    assert build_strategic_quality_markdown_report(report) == markdown


def test_strategic_quality_cases_can_be_derived_from_benchmark_dataset() -> None:
    dataset = json.loads(DEFAULT_DATASET_PATH.read_text(encoding="utf-8"))

    cases = build_strategic_quality_cases_from_benchmark(dataset)
    report = build_strategic_quality_report(cases)

    assert {case["source_url"] for case in cases} == {
        "https://base44.com",
        "https://creatify.ai/es/",
        "https://lab.naturaumana.ai",
    }
    assert report["case_count"] == 3
    assert report["taxonomy_counts"]


def test_strategic_quality_gate_fails_on_low_dimension_and_critical_taxonomy() -> None:
    report = {
        "total_score": 91.0,
        "dimension_scores": {"offer": 82.0, "differentiation": 78.0},
        "taxonomy_counts": {"founder_press_as_declared_mission": 1},
    }

    gate = evaluate_strategic_quality_gate(report)

    assert not gate["passed"]
    assert any("dimension differentiation" in failure for failure in gate["failures"])
    assert any("founder_press_as_declared_mission" in failure for failure in gate["failures"])


def test_strategic_quality_cli_gate_returns_failure_for_default_fixture_set(tmp_path: Path) -> None:
    exit_code = main([
        "--strategic-quality",
        "--strategic-quality-gate",
        "--out-dir",
        str(tmp_path),
    ])

    assert exit_code == 2


def test_strategic_quality_cli_gate_can_pass_with_relaxed_thresholds(tmp_path: Path) -> None:
    exit_code = main([
        "--strategic-quality",
        "--strategic-quality-gate",
        "--strategic-quality-min-total",
        "70",
        "--strategic-quality-min-dimension",
        "70",
        "--out-dir",
        str(tmp_path),
    ])

    assert exit_code == 0


def test_strategic_quality_cli_gate_can_use_benchmark_outputs(tmp_path: Path) -> None:
    exit_code = main([
        "--strategic-quality",
        "--strategic-quality-from-benchmark",
        "--strategic-quality-gate",
        "--out-dir",
        str(tmp_path),
    ])

    assert exit_code == 2
    written = json.loads((tmp_path / "strategic_quality.json").read_text(encoding="utf-8"))
    assert written["case_count"] == 3
