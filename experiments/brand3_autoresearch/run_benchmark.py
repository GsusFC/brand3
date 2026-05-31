"""Run the Brand3 AutoResearch benchmark and emit a retain/revert decision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.reports.tldr_brand3_research_pack_evaluation import (  # noqa: E402
    DEFAULT_DATASET_PATH,
    DEFAULT_GOLD_PATH,
    build_evaluation_report,
    build_markdown_report,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT / "runs"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def decision_from_report(report: dict[str, Any]) -> dict[str, Any]:
    case_evaluations = report.get("case_evaluations") or []
    block_summaries = report.get("block_summaries") or []
    taxonomy_counts = report.get("taxonomy_counts") or {}

    scanner_average = {}
    analyst_average = {}
    for metric in ("strategic_usefulness", "evidence_correctness", "block_answer_quality", "claim_type_correctness", "confidence_reasonableness", "noise_avoidance"):
        scanner_values = [case.get("scanner_average", {}).get(metric) for case in case_evaluations if case.get("scanner_average", {}).get(metric) is not None]
        analyst_values = [case.get("analyst_average", {}).get(metric) for case in case_evaluations if case.get("analyst_average", {}).get(metric) is not None]
        if scanner_values:
            scanner_average[metric] = round(sum(float(v) for v in scanner_values) / len(scanner_values), 2)
        else:
            scanner_average[metric] = None
        if analyst_values:
            analyst_average[metric] = round(sum(float(v) for v in analyst_values) / len(analyst_values), 2)
        else:
            analyst_average[metric] = None

    scanner_strategic = scanner_average.get("strategic_usefulness")
    analyst_strategic = analyst_average.get("strategic_usefulness")
    structural_noise_delta = (
        int((taxonomy_counts.get("scanner") or {}).get("structural_noise_selected", 0))
        - int((taxonomy_counts.get("analyst") or {}).get("structural_noise_selected", 0))
    )

    retain = False
    reasons: list[str] = []
    if scanner_strategic is not None and analyst_strategic is not None and analyst_strategic >= scanner_strategic:
        retain = True
        reasons.append("Analyst Pass is at least as strong as the scanner on average strategic usefulness.")
    else:
        reasons.append("Analyst Pass does not beat the scanner on average strategic usefulness.")

    if structural_noise_delta > 0:
        reasons.append("Analyst Pass reduces structural noise relative to the scanner.")
    elif structural_noise_delta < 0:
        retain = False
        reasons.append("Analyst Pass leaks more structural noise than the scanner.")
    else:
        reasons.append("Structural noise is tied between scanner and analyst.")

    worst_block = None
    worst_delta = 0.0
    for block_summary in block_summaries:
        delta = block_summary.get("delta_average", {}).get("strategic_usefulness")
        if isinstance(delta, (int, float)) and delta < worst_delta:
            worst_delta = float(delta)
            worst_block = block_summary.get("block")
    if worst_block and worst_delta < -5:
        retain = False
        reasons.append(f"Worst block regression is too large on {worst_block} ({worst_delta:+.1f}).")

    return {
        "decision": "retain" if retain else "revert",
        "retain": retain,
        "reasons": reasons,
        "scanner_average": scanner_average,
        "analyst_average": analyst_average,
        "structural_noise_delta": structural_noise_delta,
        "case_count": len(case_evaluations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Brand3 AutoResearch benchmark.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", action="store_true", dest="emit_json")
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args()

    dataset = load_json(args.dataset)
    gold = load_json(args.gold)
    report = build_evaluation_report(dataset, gold)
    decision = decision_from_report(report)
    payload = {
        "report": report,
        "decision": decision,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path = args.markdown or (args.output_dir / "report.md")
    markdown_path.write_text(build_markdown_report(report), encoding="utf-8")

    if args.emit_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"decision: {decision['decision']}")
        for reason in decision["reasons"]:
            print(f"- {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
