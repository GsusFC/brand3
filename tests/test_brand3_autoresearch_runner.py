from __future__ import annotations

import json
from pathlib import Path

from experiments.brand3_autoresearch.run_benchmark import decision_from_report
from src.reports.tldr_brand3_research_pack_evaluation import build_evaluation_report


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_benchmark_runner_decides_with_existing_report() -> None:
    dataset = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/dataset.json"))
    gold = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/gold.json"))

    report = build_evaluation_report(dataset, gold)
    decision = decision_from_report(report)

    assert decision["decision"] in {"retain", "revert"}
    assert "scanner_average" in decision
    assert "analyst_average" in decision
    assert decision["case_count"] == len(report["case_evaluations"])
