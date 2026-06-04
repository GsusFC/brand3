from __future__ import annotations

from scripts.research_pack_rollout_batch import render_rollout_summary_markdown, summarize_rollout_reports


def test_research_pack_rollout_batch_summarizes_cohort_metrics() -> None:
    summary = summarize_rollout_reports(
        [
            _report(1, "sklum", "promotable", "company", ["offer"], gained=2, lost=0, changed=4, critical_losses=[]),
            _report(2, "example.com", "blocked", "company", ["company_summary", "offer"], gained=1, lost=3, changed=2, critical_losses=["offer"]),
            _report(3, "lab", "review_required", "product", [], gained=3, lost=0, changed=1, critical_losses=["entity_type"]),
        ],
        db_path="test.db",
    )

    assert summary["run_count"] == 3
    assert summary["promotion_status_counts"] == {
        "blocked": 1,
        "promotable": 1,
        "review_required": 1,
    }
    assert summary["critical_loss_counts"] == {"entity_type": 1, "offer": 1}
    company_cohort = next(row for row in summary["cohort_metrics"] if row["cohort"] == "company:10-24")
    assert company_cohort["run_count"] == 2
    assert company_cohort["promotable_count"] == 1
    assert company_cohort["blocked_count"] == 1
    assert company_cohort["promotion_rate"] == 0.5


def test_research_pack_rollout_batch_renders_markdown_tables() -> None:
    summary = summarize_rollout_reports(
        [
            _report(1, "Pipe | Brand", "promotable", "company", ["offer"], gained=2, lost=0, changed=4, critical_losses=[]),
        ],
        db_path="test.db",
    )

    markdown = render_rollout_summary_markdown(summary)

    assert "# Research Pack Rollout" in markdown
    assert "Pipe \\| Brand" in markdown
    assert "company:10-24" in markdown
    assert "## Cohorts" in markdown
    assert "## Runs" in markdown


def _report(
    run_id: int,
    brand: str,
    promotion_status: str,
    entity_type: str,
    lost_fields: list[str],
    *,
    gained: int,
    lost: int,
    changed: int,
    critical_losses: list[str],
) -> dict:
    summary = {
        "gained_count": gained,
        "lost_count": lost,
        "changed_count": changed,
        "lost_fields": lost_fields,
        "entity_type_changed": "entity_type" in critical_losses,
        "parent_brand_changed": "parent_brand" in critical_losses,
    }
    return {
        "run_id": run_id,
        "status": "ok",
        "brand_name": brand,
        "url": f"https://{brand.lower().replace(' ', '')}.example",
        "cohort": f"{entity_type}:10-24",
        "graph_summary": {"source_count": 12, "claim_count": 30},
        "comparison": {"summary": summary},
        "promotion_report": {"decisions": [{"status": promotion_status}]},
        "promotion_status": promotion_status,
        "gained_count": gained,
        "lost_count": lost,
        "changed_count": changed,
        "critical_losses": critical_losses,
    }
