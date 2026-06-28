#!/usr/bin/env python3
"""Build a readable report from an SV9 Flow local eval payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SV9_FLOW_DECISION_REPORT_VERSION = "sv9-flow-decision-report-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_json", help="Path to JSON produced by scripts/sv9_flow_local_eval.py")
    parser.add_argument("--output", default="", help="Optional report output path")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(Path(args.eval_json).read_text(encoding="utf-8"))
    report = build_decision_report(payload)
    if args.format == "json":
        rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    else:
        rendered = render_markdown_report(report)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def build_decision_report(eval_payload: dict[str, Any]) -> dict[str, Any]:
    runs = [_summarize_run(run) for run in eval_payload.get("runs") or [] if isinstance(run, dict)]
    return {
        "schema_version": SV9_FLOW_DECISION_REPORT_VERSION,
        "source_schema_version": eval_payload.get("schema_version"),
        "db_path": eval_payload.get("db_path"),
        "run_count": len(runs),
        "summary": _summarize_runs(runs),
        "runs": runs,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# SV9 Flow Decision Report",
        "",
        f"- schema: `{report.get('schema_version')}`",
        f"- source: `{report.get('source_schema_version')}`",
        f"- db: `{report.get('db_path')}`",
        f"- runs: `{report.get('run_count')}`",
        "",
        "## Summary",
    ]
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    lines.extend(
        [
            f"- stable block decisions: `{summary.get('stable_block_decision_runs')}/{summary.get('run_count')}`",
            f"- stable detected blocks: `{summary.get('stable_detected_runs')}/{summary.get('run_count')}`",
            f"- stable tile effects: `{summary.get('stable_tile_effect_runs')}/{summary.get('run_count')}`",
            f"- textual drift runs: `{summary.get('textual_drift_runs')}`",
            "",
        ]
    )
    for run in report.get("runs") or []:
        if not isinstance(run, dict):
            continue
        lines.extend(_render_run(run))
    return "\n".join(lines).rstrip()


def _summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_count": len(runs),
        "stable_block_decision_runs": sum(1 for run in runs if run.get("same_block_detection_decisions") is True),
        "stable_detected_runs": sum(1 for run in runs if run.get("same_detected_blocks") is True),
        "stable_tile_effect_runs": sum(1 for run in runs if run.get("same_tile_effects") is True),
        "textual_drift_runs": [run.get("run_id") for run in runs if run.get("same_block_content_hashes") is False],
        "changed_block_detection_runs": [
            {
                "run_id": run.get("run_id"),
                "blocks": run.get("changed_block_detection_decisions") or [],
            }
            for run in runs
            if run.get("same_block_detection_decisions") is False
        ],
    }


def _summarize_run(run: dict[str, Any]) -> dict[str, Any]:
    stability = run.get("flow_llm_stability") if isinstance(run.get("flow_llm_stability"), dict) else {}
    flow_runs = [item for item in run.get("flow_llm") or [] if isinstance(item, dict)]
    cached = run.get("cached_pass1") if isinstance(run.get("cached_pass1"), dict) else {}
    return {
        "run_id": run.get("run_id"),
        "brand_name": _first_value(flow_runs, "brand_name") or cached.get("brand_name"),
        "url": _first_value(flow_runs, "url") or cached.get("url"),
        "repeat_count": stability.get("repeat_count", len(flow_runs)),
        "same_block_detection_decisions": stability.get("same_block_detection_decisions"),
        "same_detected_blocks": stability.get("same_detected_blocks"),
        "same_tile_effects": stability.get("same_tile_effects"),
        "same_block_content_hashes": stability.get("same_block_content_hashes"),
        "changed_block_detection_decisions": stability.get("changed_block_detection_decisions") or [],
        "changed_content_blocks": stability.get("changed_content_blocks") or [],
        "flow_decisions": [_decision_snapshot(item) for item in flow_runs],
        "flow_effects": [item.get("tile_signal_effects") or {} for item in flow_runs],
        "flow_detected_blocks": [item.get("detected_blocks") or [] for item in flow_runs],
        "cached_effects": cached.get("tile_signal_effects") or {},
    }


def _decision_snapshot(flow_run: dict[str, Any]) -> dict[str, Any]:
    decisions = flow_run.get("block_detection_decisions")
    if not isinstance(decisions, list):
        decisions = []
    return {
        "outcomes": {
            str(item.get("block")): str(item.get("outcome"))
            for item in decisions
            if isinstance(item, dict) and item.get("block")
        },
        "limitations": {
            str(item.get("block")): str(item.get("limitation_code") or "")
            for item in decisions
            if isinstance(item, dict) and item.get("block")
        },
        "negative_terms": {
            str(item.get("block")): [str(term) for term in item.get("weaken_terms") or []]
            for item in decisions
            if isinstance(item, dict) and item.get("weaken_terms")
        },
        "support_terms": {
            str(item.get("block")): [str(term) for term in item.get("support_terms") or []]
            for item in decisions
            if isinstance(item, dict) and item.get("support_terms")
        },
    }


def _render_run(run: dict[str, Any]) -> list[str]:
    lines = [
        f"## Run {run.get('run_id')} - {run.get('brand_name') or ''}",
        f"- url: `{run.get('url') or ''}`",
        f"- repeats: `{run.get('repeat_count')}`",
        f"- stable decisions: `{run.get('same_block_detection_decisions')}`",
        f"- stable detected blocks: `{run.get('same_detected_blocks')}`",
        f"- stable tile effects: `{run.get('same_tile_effects')}`",
        f"- stable text hashes: `{run.get('same_block_content_hashes')}`",
    ]
    changed_decisions = run.get("changed_block_detection_decisions") or []
    changed_text = run.get("changed_content_blocks") or []
    if changed_decisions:
        lines.append(f"- changed decision blocks: `{', '.join(changed_decisions)}`")
    if changed_text:
        lines.append(f"- changed text blocks: `{', '.join(changed_text)}`")
    snapshots = run.get("flow_decisions") or []
    for index, snapshot in enumerate(snapshots, start=1):
        if not isinstance(snapshot, dict):
            continue
        outcomes = snapshot.get("outcomes") if isinstance(snapshot.get("outcomes"), dict) else {}
        limitations = snapshot.get("limitations") if isinstance(snapshot.get("limitations"), dict) else {}
        negatives = snapshot.get("negative_terms") if isinstance(snapshot.get("negative_terms"), dict) else {}
        lines.append(f"- repeat {index} decisions: `{_compact_mapping(outcomes)}`")
        non_empty_limitations = {key: value for key, value in limitations.items() if value}
        if non_empty_limitations:
            lines.append(f"- repeat {index} limitations: `{_compact_mapping(non_empty_limitations)}`")
        if negatives:
            lines.append(f"- repeat {index} negative terms: `{_compact_mapping(negatives)}`")
    lines.append("")
    return lines


def _compact_mapping(value: dict[str, Any]) -> str:
    if not value:
        return ""
    parts = []
    for key in sorted(value):
        item = value[key]
        if isinstance(item, list):
            rendered = ", ".join(str(part) for part in item)
        else:
            rendered = str(item)
        parts.append(f"{key}: {rendered}")
    return " | ".join(parts)


def _first_value(items: list[dict[str, Any]], key: str) -> Any:
    for item in items:
        value = item.get(key)
        if value:
            return value
    return None


if __name__ == "__main__":
    raise SystemExit(main())
