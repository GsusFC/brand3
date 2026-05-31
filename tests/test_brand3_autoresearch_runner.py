from __future__ import annotations

import json
from pathlib import Path

from experiments.brand3_autoresearch.run_benchmark import (
    apply_candidate_overrides,
    decision_from_report,
    export_scan_candidate,
)
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


def test_apply_candidate_overrides_replaces_matching_case(tmp_path: Path) -> None:
    dataset = _load_json(Path("examples/benchmarks/tldr_brand3_research_pack/dataset.json"))
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    (candidate_dir / "base44.json").write_text(
        json.dumps({"payload": {"tldr_brand3": {"value_proposition": {"detected": True}}}}, ensure_ascii=False),
        encoding="utf-8",
    )

    updated = apply_candidate_overrides(dataset, candidate_dir)
    base44 = next(case for case in updated["cases"] if case["slug"] == "base44")

    assert base44["analyst_tldr"]["tldr_brand3"]["value_proposition"]["detected"] is True
    assert base44["candidate_source"]["path"].endswith("base44.json")


def test_export_scan_candidate_writes_output(tmp_path: Path) -> None:
    scan_file = tmp_path / "scan.json"
    scan_file.write_text(
        json.dumps(
            {
                "id": 99,
                "brand_name": "Nike",
                "url": "https://nike.com",
                "raw_payload": json.dumps(
                    {
                        "tldr_brand3": {
                            "magnetism": {"content": "Just Do It"},
                        }
                    },
                    ensure_ascii=False,
                ),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "candidate" / "nike.json"

    exported = export_scan_candidate(scan_id=None, scan_file=scan_file, output=output)

    assert exported == output
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["metadata"]["source"] == "magnetism_scan"
    assert written["payload"]["tldr_brand3"]["magnetism"]["content"] == "Just Do It"
