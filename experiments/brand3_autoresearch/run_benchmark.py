"""Run the Brand3 AutoResearch benchmark and emit a retain/revert decision."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
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
from experiments.brand3_autoresearch.export_candidate import (  # noqa: E402
    default_output_path as default_candidate_output_path,
    load_scan_source,
    normalize_scan_payload,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT / "runs"
DEFAULT_CANDIDATE_DIR = ROOT / "candidate"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_payload(candidate_obj: Any) -> dict[str, Any]:
    if isinstance(candidate_obj, dict) and isinstance(candidate_obj.get("payload"), dict):
        return candidate_obj["payload"]
    return candidate_obj if isinstance(candidate_obj, dict) else {}


def _candidate_tldr(candidate_obj: Any) -> dict[str, Any] | None:
    candidate = candidate_payload(candidate_obj)
    if isinstance(candidate.get("analyst_tldr"), dict) and isinstance(candidate["analyst_tldr"].get("tldr_brand3"), dict):
        return candidate["analyst_tldr"]
    if isinstance(candidate.get("tldr_brand3"), dict):
        return {"tldr_brand3": candidate["tldr_brand3"]}
    return None


def _candidate_override_for_case(case: dict[str, Any], candidate_dir: Path | None) -> dict[str, Any] | None:
    if candidate_dir is None:
        return None
    slug = str(case.get("slug") or "").strip()
    if not slug:
        return None
    candidate_path = candidate_dir / f"{slug}.json"
    if not candidate_path.exists():
        return None
    candidate_obj = load_json(candidate_path)
    return _candidate_tldr(candidate_obj)


def apply_candidate_overrides(dataset: dict[str, Any], candidate_dir: Path | None) -> dict[str, Any]:
    if candidate_dir is None:
        return dataset
    updated = deepcopy(dataset)
    for case in updated.get("cases") or []:
        if not isinstance(case, dict):
            continue
        override = _candidate_override_for_case(case, candidate_dir)
        if override is not None:
            case["analyst_tldr"] = override
            case.setdefault("candidate_source", {})
            if isinstance(case["candidate_source"], dict):
                case["candidate_source"]["path"] = str(candidate_dir / f"{case.get('slug')}.json")
    return updated


def export_scan_candidate(
    *,
    scan_id: int | None,
    scan_file: Path | None,
    output: Path | None,
) -> Path | None:
    if scan_id is None and scan_file is None:
        return None
    scan_source = load_scan_source(scan_id=scan_id, scan_file=scan_file)
    candidate = normalize_scan_payload(scan_source)
    output_path = output or default_candidate_output_path(scan_source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


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
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    parser.add_argument("--scan-id", type=int, default=None)
    parser.add_argument("--scan-file", type=Path, default=None)
    parser.add_argument("--scan-output", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", action="store_true", dest="emit_json")
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args()

    exported_scan_path = export_scan_candidate(scan_id=args.scan_id, scan_file=args.scan_file, output=args.scan_output)
    dataset = load_json(args.dataset)
    gold = load_json(args.gold)
    dataset = apply_candidate_overrides(dataset, args.candidate_dir if args.candidate_dir.exists() else None)
    report = build_evaluation_report(dataset, gold)
    decision = decision_from_report(report)
    payload = {
        "report": report,
        "decision": decision,
        "exported_scan_path": str(exported_scan_path) if exported_scan_path else None,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path = args.markdown or (args.output_dir / "report.md")
    markdown_path.write_text(build_markdown_report(report), encoding="utf-8")

    if args.emit_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"decision: {decision['decision']}")
        if exported_scan_path:
            print(f"- exported_scan: {exported_scan_path}")
        for reason in decision["reasons"]:
            print(f"- {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
