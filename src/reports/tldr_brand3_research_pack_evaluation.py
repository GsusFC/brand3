"""Deterministic evaluation for the TLDR Brand3 research-pack benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.reports.tldr_brand3_research_pack_evaluation_support import (
    DEFAULT_DATASET_PATH,
    DEFAULT_GOLD_PATH,
    DEFAULT_OUT_DIR,
    DEFAULT_STRATEGIC_QUALITY_CASES_PATH,
    _avg_metric,
    _delta_metric,
    _load_json,
    _render_table,
    _truncate,
    build_evaluation_report,
)
from src.reports.tldr_brand3_research_pack_strategic_quality import (
    build_strategic_quality_cases_from_benchmark,
    build_strategic_quality_markdown_report,
    build_strategic_quality_report,
    evaluate_strategic_quality_gate,
    run_strategic_quality_evaluation,
)


def _fmt_num(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}"


def _fmt_delta(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}"


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
    lines.extend(
        [
            f"- Legacy scanner strategic usefulness: `{_fmt_num(scanner_strategy)}`",
            f"- Analyst Pass strategic usefulness: `{_fmt_num(analyst_strategy)}`",
            f"- Delta: `{_fmt_delta(delta_strategy)}`",
            "",
        ]
    )

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
        lines.append(
            _render_table(
                ["block", "gold", "scanner", "analyst", "scanner score", "analyst score", "delta", "scanner tags", "analyst tags"],
                rows,
            )
        )
        lines.append("")
    lines.append("## Taxonomy counts")
    lines.append("")
    taxonomy_rows = []
    all_taxa = sorted(
        set(report["benchmark_taxonomy_counts"].keys())
        | set(report["taxonomy_counts"]["scanner"].keys())
        | set(report["taxonomy_counts"]["analyst"].keys())
    )
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


def write_evaluation_artifacts(report: dict[str, Any], out_dir: Path = DEFAULT_OUT_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "evaluation.json"
    md_path = out_dir / "evaluation.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(build_markdown_report(report), encoding="utf-8")
    return json_path, md_path


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
    report = run_evaluation(
        dataset_path=Path(args.dataset),
        gold_path=Path(args.gold),
        out_dir=Path(args.out_dir),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"JSON: {(Path(args.out_dir) / 'evaluation.json').resolve()}")
    print(f"Markdown: {(Path(args.out_dir) / 'evaluation.md').resolve()}")
    return 0
