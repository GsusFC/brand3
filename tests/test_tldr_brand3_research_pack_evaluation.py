from __future__ import annotations

import json
from pathlib import Path

from src.config import BRAND3_DB_PATH
from src.reports.tldr_brand3_research_pack_evaluation import (
    DEFAULT_DATASET_PATH,
    DEFAULT_GOLD_PATH,
    build_evaluation_report,
    build_markdown_report,
    run_evaluation,
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_evaluation_report_is_deterministic_and_writes_artifacts(tmp_path: Path) -> None:
    dataset = _load_json(DEFAULT_DATASET_PATH)
    gold = _load_json(DEFAULT_GOLD_PATH)

    before_mtime = Path(BRAND3_DB_PATH).stat().st_mtime
    report_one = build_evaluation_report(dataset, gold)
    md_one = build_markdown_report(report_one)
    report_three = run_evaluation(
        dataset_path=DEFAULT_DATASET_PATH,
        gold_path=DEFAULT_GOLD_PATH,
        out_dir=tmp_path,
    )
    after_mtime = Path(BRAND3_DB_PATH).stat().st_mtime

    report_two = build_evaluation_report(dataset, gold)
    md_two = build_markdown_report(report_two)

    assert before_mtime == after_mtime
    assert report_one == report_two
    assert report_one == report_three
    assert md_one == md_two
    json_path = tmp_path / "evaluation.json"
    md_path = tmp_path / "evaluation.md"
    assert json_path.exists()
    assert md_path.exists()

    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert written["version"] == "tldr_brand3_research_pack_evaluation_v0_1"
    assert written["case_count"] == 7
    assert len(written["block_summaries"]) == 9
    assert "https://base44.com" in {case["source_url"] for case in written["case_evaluations"]}
    assert any(case["source_url"] == "https://www.heygen.com" and not case["scanner_available"] for case in written["case_evaluations"])

    markdown = md_path.read_text(encoding="utf-8")
    assert "# TLDR Brand3 Research Pack evaluation" in markdown
    assert "## Case summary" in markdown
    assert "## Block summary" in markdown
    assert "## Detailed case tables" in markdown


def test_evaluation_report_contains_useful_comparison_fields() -> None:
    dataset = _load_json(DEFAULT_DATASET_PATH)
    gold = _load_json(DEFAULT_GOLD_PATH)
    report = build_evaluation_report(dataset, gold)
    by_url = {case["source_url"]: case for case in report["case_evaluations"]}

    base44 = by_url["https://base44.com"]
    bokeroon = by_url["https://bokeroon.com"]
    heygen = by_url["https://www.heygen.com"]

    assert base44["manual_notes"]
    assert base44["gold_summary"]
    assert base44["block_comparisons"][0]["scanner_metrics"]["strategic_usefulness"] is not None
    assert base44["block_comparisons"][0]["analyst_metrics"]["strategic_usefulness"] is not None
    assert base44["scanner_taxonomy_counts"]
    assert base44["analyst_taxonomy_counts"]

    assert bokeroon["differences_summary"]
    assert bokeroon["scanner_taxonomy_counts"] is not None
    assert bokeroon["analyst_taxonomy_counts"] is not None
    assert all("block" in block for block in bokeroon["block_comparisons"])

    assert not heygen["scanner_available"]
    assert heygen["scanner_average"]["strategic_usefulness"] is None
    assert heygen["analyst_average"]["strategic_usefulness"] is not None
