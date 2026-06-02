from __future__ import annotations

from scripts.research_pack_quality_batch import render_quality_summary_markdown, summarize_quality_reports


def test_research_pack_quality_batch_summarizes_dimension_failures() -> None:
    reports = [
        _report(1, "Strong", "pass", 91.0, {"offer": ("pass", 100), "audience": ("pass", 90)}),
        _report(2, "Weak", "fail", 54.0, {"offer": ("fail", 45), "audience": ("warn", 65)}, warnings=["missing_offer"]),
    ]

    summary = summarize_quality_reports(
        reports,
        builder="graph",
        db_path="test.db",
        min_total=75.0,
        min_dimension=60.0,
    )

    assert summary["run_count"] == 2
    assert summary["passed_count"] == 1
    assert summary["quality_status_counts"] == {"fail": 1, "pass": 1}
    assert summary["average_dimension_scores"] == {"audience": 77.5, "offer": 72.5}
    assert summary["dimension_failure_counts"] == {"audience": 1, "offer": 1}
    assert summary["runs"][1]["weak_dimensions"] == ["offer", "audience"]


def test_research_pack_quality_batch_renders_markdown_table() -> None:
    summary = summarize_quality_reports(
        [_report(1, "Pipe | Brand", "warn", 72.0, {"noise": ("warn", 70)}, warnings=["noise_terms_in_offer"])],
        builder="graph",
        db_path="test.db",
        min_total=75.0,
        min_dimension=60.0,
    )

    markdown = render_quality_summary_markdown(summary)

    assert "# BrandResearchPack Quality Batch" in markdown
    assert "| noise | 70.0 | 1 |" in markdown
    assert "Pipe \\| Brand" in markdown
    assert "noise_terms_in_offer" in markdown


def _report(
    run_id: int,
    brand: str,
    status: str,
    total_score: float,
    dimensions: dict[str, tuple[str, float]],
    *,
    warnings: list[str] | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "status": "ok",
        "brand_name": brand,
        "url": f"https://{brand.lower()}.example",
        "quality_status": status,
        "total_score": total_score,
        "gate": {"passed": status == "pass"},
        "dimensions": {
            name: {"status": dimension_status, "score": score, "reasons": []}
            for name, (dimension_status, score) in dimensions.items()
        },
        "warnings": warnings or [],
    }
