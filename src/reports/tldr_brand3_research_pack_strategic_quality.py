"""Strategic quality evaluation for the TLDR Brand3 research pack."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

from src.reports.tldr_brand3_research_pack_strategic_quality_support import (
    BlockComparison,
    CaseComparison,
    DEFAULT_DATASET_PATH,
    DEFAULT_GOLD_PATH,
    DEFAULT_OUT_DIR,
    DEFAULT_STRATEGIC_QUALITY_CASES_PATH,
    TLDR_KEYS,
    _all_block_text,
    _avg_metric,
    _block_answer,
    _build_recommendations,
    _check_entity_separation,
    _check_frictions,
    _check_text_expectation,
    _check_traceability,
    _compare_block,
    _count_tags,
    _count_taxonomy,
    _delta_metric,
    _evaluate_strategic_quality_case,
    _fmt_delta,
    _fmt_num,
    _list,
    _load_json,
    _normalize_text,
    _normalize_tokens,
    _render_table,
    _str_list,
    _text_similarity,
    _truncate,
)


def build_strategic_quality_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_reports = [_evaluate_strategic_quality_case(case) for case in cases]
    dimension_scores: dict[str, float] = {}
    dimensions = ["offer", "audience", "differentiation", "personality", "vision", "frictions", "evidence_traceability", "entity_separation"]
    for dimension in dimensions:
        scores = [
            row["score"]
            for case in case_reports
            for row in case["dimension_results"]
            if row["dimension"] == dimension
        ]
        dimension_scores[dimension] = round(mean(scores), 2) if scores else 100.0

    taxonomy_counts: dict[str, int] = {}
    for case in case_reports:
        for failure in case["failures"]:
            tag = failure.split(":", 1)[0]
            taxonomy_counts[tag] = taxonomy_counts.get(tag, 0) + 1
    taxonomy_counts = dict(sorted(taxonomy_counts.items(), key=lambda item: (-item[1], item[0])))

    return {
        "version": "tldr_brand3_strategic_quality_v0_1",
        "case_count": len(case_reports),
        "case_evaluations": case_reports,
        "dimension_scores": dict(sorted(dimension_scores.items())),
        "taxonomy_counts": taxonomy_counts,
        "total_score": round(mean(dimension_scores.values()), 2) if dimension_scores else 0.0,
        "recommendations": _strategic_quality_recommendations(taxonomy_counts),
    }


def build_strategic_quality_cases_from_benchmark(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    strategic_case_urls = {
        "https://base44.com",
        "https://creatify.ai/es/",
        "https://lab.naturaumana.ai",
    }
    cases: list[dict[str, Any]] = []
    for case in dataset.get("cases") or []:
        if not isinstance(case, dict):
            continue
        source_url = str(case.get("source_url") or "")
        if source_url not in strategic_case_urls:
            continue
        analyst_tldr = case.get("analyst_tldr") if isinstance(case.get("analyst_tldr"), dict) else {}
        tldr = analyst_tldr.get("tldr_brand3") if isinstance(analyst_tldr.get("tldr_brand3"), dict) else {}
        value_answer = str((tldr.get("value_proposition") or {}).get("answer") or "")
        idea_answer = str((tldr.get("brand_idea") or {}).get("answer") or "")
        cases.append(
            {
                "slug": str(case.get("slug") or source_url),
                "source_url": source_url,
                "archetype": str(case.get("source_kind") or "benchmark"),
                "research_pack": case.get("research_pack") or {},
                "analyst_tldr": analyst_tldr,
                "strategic_expectations": {
                    "offer": {"must_include_any": [[_first_significant_token(value_answer)]]},
                    "audience": {"must_include_any": [["teams", "users", "founders", "creators", "customers", "brands", "people"]]},
                    "differentiation": {"must_include_any": [[_first_significant_token(idea_answer)]]},
                    "frictions": {"must_acknowledge": ["thin", "absent", "missing", "unclear"], "require_counter_evidence": False},
                    "evidence_traceability": {"require_traceable_sources": True, "forbid_source_types": ["noise"]},
                    "entity_separation": {"forbid_press_as_declared_mission": True},
                },
            }
        )
    return cases


def build_strategic_quality_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# TLDR Brand3 strategic quality evaluation",
        "",
        f"- Cases evaluated: `{report['case_count']}`",
        f"- Total score: `{_fmt_num(float(report['total_score']))}`",
        "",
        "## Dimension Scores",
        "",
    ]
    rows = [
        [dimension, _fmt_num(float(score))]
        for dimension, score in sorted((report.get("dimension_scores") or {}).items())
    ]
    lines.append(_render_table(["dimension", "score"], rows))
    lines.extend(["", "## Taxonomy Counts", ""])
    taxonomy_rows = [[tag, str(count)] for tag, count in (report.get("taxonomy_counts") or {}).items()]
    lines.append(_render_table(["taxonomy", "count"], taxonomy_rows) if taxonomy_rows else "No taxonomy failures.")
    lines.extend(["", "## Recommendations", ""])
    for item in report.get("recommendations") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Cases", ""])
    for case in report.get("case_evaluations") or []:
        lines.append(f"- `{case['slug']}`: `{_fmt_num(float(case['total_score']))}`; failures={len(case['failures'])}")
    return "\n".join(lines).rstrip() + "\n"


def write_evaluation_artifacts(report: dict[str, Any], out_dir: Path = DEFAULT_OUT_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "evaluation.json"
    md_path = out_dir / "strategic_quality.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(build_strategic_quality_markdown_report(report), encoding="utf-8")
    return json_path, md_path


def build_markdown_report(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# TLDR Brand3 Research Pack evaluation",
        "",
        f"- Dataset version: `{report['dataset_version']}`",
        f"- Gold version: `{report['gold_version']}`",
        f"- Cases evaluated: `{report['case_count']}`",
        "",
        "## Summary",
    ]
    scanner_strategy = _avg_metric([case["scanner_average"] for case in report["case_evaluations"] if case["scanner_available"]], "strategic_usefulness")
    analyst_strategy = _avg_metric([case["analyst_average"] for case in report["case_evaluations"]], "strategic_usefulness")
    delta_strategy = _delta_metric(analyst_strategy, scanner_strategy)
    lines.extend([
        f"- Legacy scanner strategic usefulness: `{_fmt_num(scanner_strategy)}`",
        f"- Analyst Pass strategic usefulness: `{_fmt_num(analyst_strategy)}`",
        f"- Delta: `{_fmt_delta(delta_strategy)}`",
        "",
    ])
    top_block_gains = sorted(
        (
            (summary["block"], summary["delta_average"]["strategic_usefulness"])
            for summary in report["block_summaries"]
            if summary["delta_average"]["strategic_usefulness"] is not None
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    if top_block_gains:
        lines.append("### Biggest block gains")
        for block, delta in top_block_gains[:3]:
            lines.append(f"- `{block}`: `{_fmt_delta(delta)}`")
        lines.append("")
    worsening_cases = [
        case for case in report["case_evaluations"]
        if case["scanner_available"]
        and case["delta_average"]["strategic_usefulness"] is not None
        and case["delta_average"]["strategic_usefulness"] < 0
    ]
    lines.append("### Cases where the Analyst Pass worsens")
    if worsening_cases:
        for case in worsening_cases:
            lines.append(f"- `{case['source_url']}`: `{_fmt_delta(case['delta_average']['strategic_usefulness'])}`")
    else:
        lines.append("- None in this benchmark set.")
    lines.append("")
    lines.append("### Next adjustments")
    for item in report["recommendations"]:
        lines.append(f"- {item}")
    lines.append("")
    case_rows = []
    for case in report["case_evaluations"]:
        case_rows.append([
            case["source_url"].replace("https://", ""),
            _fmt_num(case["scanner_average"]["strategic_usefulness"]) if case["scanner_available"] else "n/a",
            _fmt_num(case["analyst_average"]["strategic_usefulness"]),
            _fmt_delta(case["delta_average"]["strategic_usefulness"]) if case["scanner_available"] else "n/a",
            ", ".join(case["benchmark_taxonomy"][:3]) or "—",
            ", ".join(sorted(case["scanner_taxonomy_counts"].keys())[:3]) or "—",
            ", ".join(sorted(case["analyst_taxonomy_counts"].keys())[:3]) or "—",
        ])
    lines.extend([
        "## Case summary",
        "",
        _render_table(
            ["case", "scanner", "analyst", "delta", "benchmark taxonomy", "scanner taxonomy", "analyst taxonomy"],
            case_rows,
        ),
        "",
    ])
    block_rows = []
    for summary in report["block_summaries"]:
        block_rows.append([
            summary["block"],
            _fmt_num(summary["scanner_average"]["strategic_usefulness"]),
            _fmt_num(summary["analyst_average"]["strategic_usefulness"]),
            _fmt_delta(summary["delta_average"]["strategic_usefulness"]),
            _fmt_delta(summary["delta_average"]["noise_avoidance"]),
        ])
    lines.extend([
        "## Block summary",
        "",
        _render_table(["block", "scanner", "analyst", "delta", "noise delta"], block_rows),
        "",
    ])
    lines.append("## Detailed case tables")
    lines.append("")
    for case in report["case_evaluations"]:
        lines.append(f"### `{case['source_url']}`")
        lines.append("")
        lines.append(f"{case['manual_notes']}")
        lines.append("")
        lines.append(f"Gold summary: {case['gold_summary']}")
        if case["differences_summary"]:
            lines.append(f"Dataset difference note: {case['differences_summary']}")
        lines.append("")
        rows = []
        for block in case["block_comparisons"]:
            rows.append([
                block["block"],
                _truncate(block["gold_answer"], 58),
                _truncate(block["scanner_answer"], 58),
                _truncate(block["analyst_answer"], 58),
                _fmt_num(block["scanner_metrics"]["strategic_usefulness"]) if block["scanner_metrics"]["strategic_usefulness"] is not None else "n/a",
                _fmt_num(block["analyst_metrics"]["strategic_usefulness"]) if block["analyst_metrics"]["strategic_usefulness"] is not None else "n/a",
                _fmt_delta(
                    (
                        block["analyst_metrics"]["strategic_usefulness"] - block["scanner_metrics"]["strategic_usefulness"]
                    )
                    if block["scanner_metrics"]["strategic_usefulness"] is not None and block["analyst_metrics"]["strategic_usefulness"] is not None
                    else None
                ),
                ", ".join(block["scanner_taxonomy"]) or "—",
                ", ".join(block["analyst_taxonomy"]) or "—",
            ])
        lines.append(_render_table(["block", "gold", "scanner", "analyst", "scanner score", "analyst score", "delta", "scanner tags", "analyst tags"], rows))
        lines.append("")
    lines.append("## Taxonomy counts")
    lines.append("")
    taxonomy_rows = []
    all_taxa = sorted(set(report["benchmark_taxonomy_counts"].keys()) | set(report["taxonomy_counts"]["scanner"].keys()) | set(report["taxonomy_counts"]["analyst"].keys()))
    for tag in all_taxa:
        taxonomy_rows.append([
            tag,
            str(report["benchmark_taxonomy_counts"].get(tag, 0)),
            str(report["taxonomy_counts"]["scanner"].get(tag, 0)),
            str(report["taxonomy_counts"]["analyst"].get(tag, 0)),
        ])
    if taxonomy_rows:
        lines.append(_render_table(["taxonomy", "benchmark", "scanner", "analyst"], taxonomy_rows))
    else:
        lines.append("No taxonomy tags were detected.")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_evaluation(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    gold_path: Path = DEFAULT_GOLD_PATH,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> dict[str, Any]:
    dataset = _load_json(dataset_path)
    gold = _load_json(gold_path)
    report = build_evaluation_report(dataset, gold)
    write_evaluation_artifacts(report, out_dir=out_dir)
    return report


def build_evaluation_report(dataset: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    gold_cases = gold.get("cases") or {}
    case_evaluations: list[CaseComparison] = []
    for case in dataset.get("cases") or []:
        source_url = str(case.get("source_url") or "")
        gold_case = gold_cases.get(source_url)
        if not isinstance(gold_case, dict):
            continue
        gold_blocks = gold_case.get("blocks") or {}
        scanner_tldr = (case.get("scanner_current_tldr") or {}).get("tldr_brand3") if case.get("scanner_current_tldr") else None
        analyst_tldr = (case.get("analyst_tldr") or {}).get("tldr_brand3") if case.get("analyst_tldr") else None
        block_comparisons: list[BlockComparison] = []
        for block_name in TLDR_KEYS:
            gold_block = gold_blocks.get(block_name) or {}
            scanner_block = scanner_tldr.get(block_name) if isinstance(scanner_tldr, dict) else None
            analyst_block = analyst_tldr.get(block_name) if isinstance(analyst_tldr, dict) else None
            block_comparisons.append(
                _compare_block(
                    case=case,
                    block_name=block_name,
                    gold_block=gold_block,
                    scanner_block=scanner_block,
                    analyst_block=analyst_block,
                )
            )
        scanner_rows = [block.scanner_metrics for block in block_comparisons if block.scanner_metrics["strategic_usefulness"] is not None]
        analyst_rows = [block.analyst_metrics for block in block_comparisons if block.analyst_metrics["strategic_usefulness"] is not None]
        benchmark_taxonomy = sorted(set([str(tag) for tag in ((case.get("differences") or {}).get("error_taxonomy") or [])]) | set([str(tag) for tag in (gold_case.get("error_taxonomy") or [])]))
        scanner_average = {metric: _avg_metric(scanner_rows, metric) for metric in ["evidence_correctness", "block_answer_quality", "claim_type_correctness", "confidence_reasonableness", "noise_avoidance", "strategic_usefulness"]}
        analyst_average = {metric: _avg_metric(analyst_rows, metric) for metric in ["evidence_correctness", "block_answer_quality", "claim_type_correctness", "confidence_reasonableness", "noise_avoidance", "strategic_usefulness"]}
        delta_average = {metric: _delta_metric(analyst_average.get(metric), scanner_average.get(metric)) for metric in analyst_average}
        case_evaluations.append(
            CaseComparison(
                source_url=source_url,
                slug=str(case.get("slug") or source_url),
                source_kind=str(case.get("source_kind") or ""),
                brand_audit_run_id=case.get("brand_audit_run_id"),
                magnetism_scan_id=case.get("magnetism_scan_id"),
                manual_notes=str(case.get("manual_notes") or ""),
                gold_summary=str(gold_case.get("summary") or ""),
                differences_summary=str((case.get("differences") or {}).get("summary") or ""),
                scanner_available=bool(case.get("scanner_current_tldr")),
                benchmark_taxonomy=benchmark_taxonomy,
                scanner_average=scanner_average,
                analyst_average=analyst_average,
                delta_average=delta_average,
                block_comparisons=block_comparisons,
                benchmark_taxonomy_counts=_count_tags(benchmark_taxonomy),
                scanner_taxonomy_counts=_count_taxonomy(block_comparisons, "scanner"),
                analyst_taxonomy_counts=_count_taxonomy(block_comparisons, "analyst"),
            )
        )
    block_summaries: list[dict[str, Any]] = []
    for block_name in TLDR_KEYS:
        scanner_rows: list[dict[str, float | None]] = []
        analyst_rows: list[dict[str, float | None]] = []
        for case in case_evaluations:
            block = next(item for item in case.block_comparisons if item.block == block_name)
            if block.scanner_metrics["strategic_usefulness"] is not None:
                scanner_rows.append(block.scanner_metrics)
            if block.analyst_metrics["strategic_usefulness"] is not None:
                analyst_rows.append(block.analyst_metrics)
        scanner_average = {metric: _avg_metric(scanner_rows, metric) for metric in ["evidence_correctness", "block_answer_quality", "claim_type_correctness", "confidence_reasonableness", "noise_avoidance", "strategic_usefulness"]}
        analyst_average = {metric: _avg_metric(analyst_rows, metric) for metric in ["evidence_correctness", "block_answer_quality", "claim_type_correctness", "confidence_reasonableness", "noise_avoidance", "strategic_usefulness"]}
        block_summaries.append(
            {
                "block": block_name,
                "scanner_average": scanner_average,
                "analyst_average": analyst_average,
                "delta_average": {metric: _delta_metric(analyst_average.get(metric), scanner_average.get(metric)) for metric in analyst_average},
            }
        )
    taxonomy_counts: dict[str, dict[str, int]] = {"scanner": {}, "analyst": {}}
    for source in taxonomy_counts:
        for case in case_evaluations:
            counts = case.scanner_taxonomy_counts if source == "scanner" else case.analyst_taxonomy_counts
            for tag, value in counts.items():
                taxonomy_counts[source][tag] = taxonomy_counts[source].get(tag, 0) + value
        taxonomy_counts[source] = dict(sorted(taxonomy_counts[source].items(), key=lambda item: (-item[1], item[0])))
    benchmark_taxonomy_counts: dict[str, int] = {}
    for case in case_evaluations:
        for tag, value in case.benchmark_taxonomy_counts.items():
            benchmark_taxonomy_counts[tag] = benchmark_taxonomy_counts.get(tag, 0) + value
    benchmark_taxonomy_counts = dict(sorted(benchmark_taxonomy_counts.items(), key=lambda item: (-item[1], item[0])))
    return {
        "version": "tldr_brand3_research_pack_evaluation_v0_1",
        "dataset_version": str(dataset.get("version") or ""),
        "gold_version": str(gold.get("version") or ""),
        "blocks": TLDR_KEYS,
        "case_count": len(case_evaluations),
        "case_evaluations": [case.to_dict() for case in case_evaluations],
        "block_summaries": block_summaries,
        "benchmark_taxonomy_counts": benchmark_taxonomy_counts,
        "taxonomy_counts": taxonomy_counts,
        "recommendations": _build_recommendations(taxonomy_counts, block_summaries),
    }


def _strategic_quality_recommendations(taxonomy_counts: dict[str, int]) -> list[str]:
    recs: list[str] = []
    if any(tag.startswith("offer_") for tag in taxonomy_counts):
        recs.append("Separate the core offer from proof metrics and preserve the expected offer category.")
    if any(tag.startswith("differentiation_") for tag in taxonomy_counts):
        recs.append("Strengthen brand_idea checks so weak metaphors or generic product mechanics do not pass as differentiation.")
    if "founder_press_as_declared_mission" in taxonomy_counts:
        recs.append("Keep founder, funding, and press context out of declared mission unless owned evidence supports it.")
    if any(tag.startswith("vision_") for tag in taxonomy_counts):
        recs.append("Downgrade vision when future language is over-broad or not directly supported by owned evidence.")
    return recs or ["Strategic quality checks passed for the current fixture set."]


def _first_significant_token(text: str) -> str:
    for token in _normalize_tokens(text):
        if len(token) > 3:
            return token
    return ""


def evaluate_strategic_quality_gate(
    report: dict[str, Any],
    *,
    min_total: float = 85.0,
    min_dimension: float = 80.0,
) -> dict[str, Any]:
    failures: list[str] = []
    total = float(report.get("total_score") or 0.0)
    if total < min_total:
        failures.append(f"total_score {total:.1f} below {min_total:.1f}")
    for dimension, score_value in (report.get("dimension_scores") or {}).items():
        score = float(score_value or 0.0)
        if score <= min_dimension:
            failures.append(f"dimension {dimension} score {score:.1f} not above {min_dimension:.1f}")
    critical_taxonomy = {"founder_press_as_declared_mission", "forbidden_source_type"}
    for tag in critical_taxonomy:
        if int((report.get("taxonomy_counts") or {}).get(tag) or 0) > 0:
            failures.append(f"critical taxonomy {tag} present")
    return {"passed": not failures, "failures": failures}


def run_strategic_quality_evaluation(
    *,
    cases_path: Path = DEFAULT_STRATEGIC_QUALITY_CASES_PATH,
    out_dir: Path = DEFAULT_OUT_DIR,
    from_benchmark: bool = False,
    dataset_path: Path = DEFAULT_DATASET_PATH,
) -> dict[str, Any]:
    if from_benchmark:
        cases = build_strategic_quality_cases_from_benchmark(_load_json(dataset_path))
    else:
        payload = _load_json(cases_path)
        cases = payload.get("cases") if isinstance(payload.get("cases"), list) else []
    report = build_strategic_quality_report(cases)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "strategic_quality.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "strategic_quality.md").write_text(build_strategic_quality_markdown_report(report), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the TLDR Brand3 research-pack benchmark.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Path to the dataset JSON.")
    parser.add_argument("--gold", default=str(DEFAULT_GOLD_PATH), help="Path to the gold JSON.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for evaluation artifacts.")
    parser.add_argument("--strategic-quality", action="store_true", help="Run the strategic quality fixture evaluator.")
    parser.add_argument("--strategic-quality-from-benchmark", action="store_true", help="Derive strategic quality cases from benchmark outputs.")
    parser.add_argument("--strategic-quality-gate", action="store_true", help="Fail with code 2 when the strategic quality gate fails.")
    parser.add_argument("--strategic-quality-min-total", type=float, default=85.0)
    parser.add_argument("--strategic-quality-min-dimension", type=float, default=80.0)
    args = parser.parse_args(argv)
    if args.strategic_quality:
        report = run_strategic_quality_evaluation(
            out_dir=Path(args.out_dir),
            from_benchmark=args.strategic_quality_from_benchmark,
            dataset_path=Path(args.dataset),
        )
        gate = evaluate_strategic_quality_gate(
            report,
            min_total=args.strategic_quality_min_total,
            min_dimension=args.strategic_quality_min_dimension,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        print(f"JSON: {(Path(args.out_dir) / 'strategic_quality.json').resolve()}")
        print(f"Markdown: {(Path(args.out_dir) / 'strategic_quality.md').resolve()}")
        if args.strategic_quality_gate and not gate["passed"]:
            print(json.dumps(gate, ensure_ascii=False, indent=2, sort_keys=True))
            return 2
        return 0
    report = build_evaluation_report(_load_json(Path(args.dataset)), _load_json(Path(args.gold)))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"JSON: {(Path(args.out_dir) / 'evaluation.json').resolve()}")
    print(f"Markdown: {(Path(args.out_dir) / 'evaluation.md').resolve()}")
    return 0
