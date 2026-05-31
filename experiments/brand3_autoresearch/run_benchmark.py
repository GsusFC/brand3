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
BLOCK_WEIGHTS = {
    "core_purpose": 1.5,
    "magnetism": 1.0,
    "value_proposition": 2.0,
    "personality": 1.0,
    "brand_idea": 1.5,
    "attributes": 1.0,
    "values": 1.0,
    "mission": 2.0,
    "vision": 1.25,
}
CRITICAL_BLOCKS = {"core_purpose", "value_proposition", "brand_idea", "mission"}


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


def apply_single_candidate_override(
    dataset: dict[str, Any],
    *,
    candidate_file: Path | None,
    candidate_slug: str | None,
) -> dict[str, Any]:
    if candidate_file is None or not candidate_file.exists():
        return dataset
    override_slug = (candidate_slug or candidate_file.stem).strip()
    if not override_slug:
        return dataset
    candidate_obj = load_json(candidate_file)
    override = _candidate_tldr(candidate_obj)
    if override is None:
        return dataset

    updated = deepcopy(dataset)
    for case in updated.get("cases") or []:
        if not isinstance(case, dict):
            continue
        if str(case.get("slug") or "").strip() != override_slug:
            continue
        case["analyst_tldr"] = override
        case.setdefault("candidate_source", {})
        if isinstance(case["candidate_source"], dict):
            case["candidate_source"]["path"] = str(candidate_file)
        break
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


def case_delta_summary(report: dict[str, Any], *, limit: int = 3) -> dict[str, list[dict[str, Any]]]:
    deltas: list[dict[str, Any]] = []
    for case in report.get("case_evaluations") or []:
        if not isinstance(case, dict):
            continue
        delta = case.get("delta_average", {}).get("strategic_usefulness")
        if not isinstance(delta, (int, float)):
            continue
        deltas.append(
            {
                "source_url": case.get("source_url"),
                "delta": round(float(delta), 2),
                "scanner_available": bool(case.get("scanner_available")),
            }
        )
    improvements = sorted((row for row in deltas if row["delta"] > 0), key=lambda row: row["delta"], reverse=True)
    regressions = sorted((row for row in deltas if row["delta"] < 0), key=lambda row: row["delta"])
    return {
        "improvements": improvements[:limit],
        "regressions": regressions[:limit],
    }


def candidate_variant_score(payload: dict[str, Any]) -> tuple[float, float, float]:
    decision = payload["decision"]
    report = payload["report"]
    retain_bonus = 1.0 if decision.get("retain") else 0.0
    weighted_total = 0.0
    weighted_count = 0.0
    critical_total = 0.0
    critical_count = 0.0
    regression_penalty = 0.0
    critical_regression_penalty = 0.0
    regression_blocks = 0.0

    for block_summary in report.get("block_summaries") or []:
        if not isinstance(block_summary, dict):
            continue
        block = str(block_summary.get("block") or "")
        weight = float(BLOCK_WEIGHTS.get(block, 1.0))
        analyst_average = block_summary.get("analyst_average") or {}
        analyst_strategic = analyst_average.get("strategic_usefulness")
        if isinstance(analyst_strategic, (int, float)):
            score = float(analyst_strategic)
            weighted_total += weight * score
            weighted_count += weight
            if block in CRITICAL_BLOCKS:
                critical_total += weight * score
                critical_count += weight
        delta = block_summary.get("delta_average", {}).get("strategic_usefulness")
        if isinstance(delta, (int, float)) and delta < 0:
            penalty = weight * abs(float(delta))
            regression_penalty += penalty
            regression_blocks += 1.0
            if block in CRITICAL_BLOCKS:
                critical_regression_penalty += penalty

    weighted_average = weighted_total / weighted_count if weighted_count else float("-inf")
    critical_average = critical_total / critical_count if critical_count else weighted_average
    structural_noise_delta = decision.get("structural_noise_delta")
    noise_bonus = float(structural_noise_delta) * 0.15 if isinstance(structural_noise_delta, (int, float)) else 0.0
    score = (
        (weighted_average * 0.6)
        + (critical_average * 0.4)
        + noise_bonus
        - (regression_penalty * 0.03)
        - (critical_regression_penalty * 0.15)
        - (regression_blocks * 0.1)
    )
    return (retain_bonus, score, -critical_regression_penalty)


def evaluate_candidate_variant(
    *,
    dataset: dict[str, Any],
    gold: dict[str, Any],
    candidate_dir: Path | None = None,
    candidate_file: Path | None = None,
    candidate_slug: str | None = None,
) -> dict[str, Any]:
    updated = apply_single_candidate_override(dataset, candidate_file=candidate_file, candidate_slug=candidate_slug)
    updated = apply_candidate_overrides(updated, candidate_dir if candidate_dir and candidate_dir.exists() else None)
    report = build_evaluation_report(updated, gold)
    decision = decision_from_report(report)
    return {
        "report": report,
        "decision": decision,
        "case_delta_summary": case_delta_summary(report),
    }


def resolve_candidate_slug(candidate_file: Path | None, candidate_slug: str | None, fallback_slug: str | None = None) -> str | None:
    slug = (candidate_slug or fallback_slug or (candidate_file.stem if candidate_file is not None else "")).strip()
    return slug or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Brand3 AutoResearch benchmark.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD_PATH)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    parser.add_argument("--candidate-dir-b", type=Path, default=None)
    parser.add_argument("--candidate-file", type=Path, default=None)
    parser.add_argument("--candidate-slug", type=str, default=None)
    parser.add_argument("--candidate-file-b", type=Path, default=None)
    parser.add_argument("--candidate-slug-b", type=str, default=None)
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
    payload: dict[str, Any]
    if args.candidate_dir_b is not None or args.candidate_file_b is not None:
        candidate_a_slug = resolve_candidate_slug(args.candidate_file, args.candidate_slug)
        candidate_b_slug = resolve_candidate_slug(args.candidate_file_b, args.candidate_slug_b, args.candidate_slug)
        variant_a = evaluate_candidate_variant(
            dataset=dataset,
            gold=gold,
            candidate_dir=args.candidate_dir,
            candidate_file=args.candidate_file,
            candidate_slug=candidate_a_slug,
        )
        variant_b = evaluate_candidate_variant(
            dataset=dataset,
            gold=gold,
            candidate_dir=args.candidate_dir_b or args.candidate_dir,
            candidate_file=args.candidate_file_b,
            candidate_slug=candidate_b_slug,
        )
        score_a = candidate_variant_score(variant_a)
        score_b = candidate_variant_score(variant_b)
        if score_a > score_b:
            winner = "a"
        elif score_b > score_a:
            winner = "b"
        else:
            winner = "tie"
        payload = {
            "compare": {
                "winner": winner,
                "score_a": list(score_a),
                "score_b": list(score_b),
                "candidate_a": {
                    "file": str(args.candidate_file) if args.candidate_file else None,
                    "dir": str(args.candidate_dir) if args.candidate_dir else None,
                    "slug": candidate_a_slug,
                },
                "candidate_b": {
                    "file": str(args.candidate_file_b) if args.candidate_file_b else None,
                    "dir": str(args.candidate_dir_b or args.candidate_dir) if (args.candidate_dir_b or args.candidate_dir) else None,
                    "slug": candidate_b_slug,
                },
            },
            "variant_a": variant_a,
            "variant_b": variant_b,
            "exported_scan_path": str(exported_scan_path) if exported_scan_path else None,
        }
    else:
        variant = evaluate_candidate_variant(
            dataset=dataset,
            gold=gold,
            candidate_dir=args.candidate_dir,
            candidate_file=args.candidate_file,
            candidate_slug=resolve_candidate_slug(args.candidate_file, args.candidate_slug),
        )
        payload = {
            "report": variant["report"],
            "decision": variant["decision"],
            "case_delta_summary": variant["case_delta_summary"],
            "exported_scan_path": str(exported_scan_path) if exported_scan_path else None,
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path = args.markdown or (args.output_dir / "report.md")
    markdown_report = build_markdown_report(payload["report"] if "report" in payload else payload["variant_a"]["report"])
    if "compare" in payload:
        compare = payload["compare"]
        markdown_report = "\n".join(
            [
                "# TLDR Brand3 Research Pack comparison",
                "",
                f"- Winner: `{compare['winner']}`",
                f"- Candidate A score: `{compare['score_a']}`",
                f"- Candidate B score: `{compare['score_b']}`",
                "",
                "## Candidate A",
                "",
                build_markdown_report(payload["variant_a"]["report"]).rstrip(),
                "",
                "## Candidate B",
                "",
                build_markdown_report(payload["variant_b"]["report"]).rstrip(),
                "",
            ]
        )
    markdown_path.write_text(markdown_report, encoding="utf-8")

    if args.emit_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if "compare" in payload:
            compare = payload["compare"]
            print(f"winner: {compare['winner']}")
            print(f"- candidate_a_score: {compare['score_a']}")
            print(f"- candidate_b_score: {compare['score_b']}")
            if compare["candidate_a"].get("dir") or compare["candidate_b"].get("dir"):
                print(f"- candidate_a_dir: {compare['candidate_a'].get('dir')}")
                print(f"- candidate_b_dir: {compare['candidate_b'].get('dir')}")
        else:
            decision = payload["decision"]
            print(f"decision: {decision['decision']}")
        if exported_scan_path:
            print(f"- exported_scan: {exported_scan_path}")
        if "compare" in payload:
            for label, variant in (("A", payload["variant_a"]), ("B", payload["variant_b"])):
                print(f"- candidate_{label.lower()} decision: {variant['decision']['decision']}")
                for reason in variant["decision"]["reasons"]:
                    print(f"  - {reason}")
                if variant["case_delta_summary"]["improvements"]:
                    print("  - Top improvements:")
                    for item in variant["case_delta_summary"]["improvements"]:
                        print(f"    - {item['source_url']}: {item['delta']:+.2f}")
                if variant["case_delta_summary"]["regressions"]:
                    print("  - Top regressions:")
                    for item in variant["case_delta_summary"]["regressions"]:
                        print(f"    - {item['source_url']}: {item['delta']:+.2f}")
        else:
            for reason in payload["decision"]["reasons"]:
                print(f"- {reason}")
            if payload["case_delta_summary"]["improvements"]:
                print("- Top improvements:")
                for item in payload["case_delta_summary"]["improvements"]:
                    print(f"  - {item['source_url']}: {item['delta']:+.2f}")
            if payload["case_delta_summary"]["regressions"]:
                print("- Top regressions:")
                for item in payload["case_delta_summary"]["regressions"]:
                    print(f"  - {item['source_url']}: {item['delta']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
