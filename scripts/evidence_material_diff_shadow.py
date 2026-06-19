#!/usr/bin/env python3
"""Run material-diff LLM shadow review over saved vNext batch artifacts.

The script reads local ``vnext_*.json`` files produced by
``scripts/evidence_vnext_remote_batch.py``. It does not call the scanner, mutate
production data, or change vNext promotion decisions.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from src.config import BRAND3_EVIDENCE_LLM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.research.evidence_material_diff_llm import build_material_diff_llm_shadow


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    input_files = _input_files(args)
    if not input_files:
        raise SystemExit("No vnext JSON files found.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    llm = None
    if args.execute:
        llm = LLMAnalyzer(model=args.model)
        if args.no_cache:
            llm.use_cache = False

    rows: list[dict[str, Any]] = []
    for path in input_files:
        started = time.monotonic()
        payload = json.loads(path.read_text(encoding="utf-8"))
        report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
        result = build_material_diff_llm_shadow(report, llm=llm, enabled=bool(args.execute))
        result["elapsed_seconds"] = _elapsed(started)
        result["source_file"] = str(path)
        run_ids = sorted({int(item["run_id"]) for item in result.get("candidates") or [] if item.get("run_id") is not None})
        result["run_ids"] = run_ids
        if result.get("candidate_count"):
            (output_dir / f"material_diff_shadow_{path.stem.removeprefix('vnext_')}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        row = _row(result)
        rows.append(row)
        print(
            "file={file} runs={runs} status={status} candidates={candidates} assessments={assessments} verdicts={verdicts} elapsed={elapsed}s".format(
                file=path.name,
                runs=",".join(str(item) for item in run_ids) or "-",
                status=row["status"],
                candidates=row["candidate_count"],
                assessments=row["assessment_count"],
                verdicts=row["verdict_counts"],
                elapsed=row["elapsed_seconds"],
            )
        )

    batch = {
        "version": "evidence_material_diff_shadow_batch_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "execute": bool(args.execute),
        "model": args.model,
        "input_files": [str(path) for path in input_files],
        "rows": rows,
        "summary": _summary(rows),
    }
    (output_dir / "material_diff_shadow_summary.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "material_diff_shadow_summary.md").write_text(_markdown(batch), encoding="utf-8")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch-dir",
        type=Path,
        help="Directory containing vnext_*.json files.",
    )
    parser.add_argument(
        "--input-json",
        action="append",
        type=Path,
        default=[],
        help="Specific vnext JSON file. May be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out/evidence_vnext/material_diff_shadow"),
        help="Directory for shadow artifacts.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Call the configured LLM. Omit for deterministic dry-run candidate inventory.",
    )
    parser.add_argument("--model", default=BRAND3_EVIDENCE_LLM_MODEL, help="LLM model name.")
    parser.add_argument("--no-cache", action="store_true", help="Bypass persistent LLM cache for timing/stability checks.")
    return parser.parse_args(argv)


def _input_files(args: argparse.Namespace) -> list[Path]:
    paths = list(args.input_json or [])
    if args.batch_dir:
        paths.extend(sorted(Path(args.batch_dir).glob("vnext_*.json")))
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = Path(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def _row(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    repair_plan = result.get("repair_plan") if isinstance(result.get("repair_plan"), list) else []
    decision_packets = result.get("decision_packets") if isinstance(result.get("decision_packets"), list) else []
    return {
        "source_file": result.get("source_file") or "",
        "run_ids": list(result.get("run_ids") or []),
        "status": result.get("status") or "",
        "reason": result.get("reason") or "",
        "model": result.get("model") or "",
        "transport": result.get("transport") or "",
        "candidate_count": int(result.get("candidate_count") or 0),
        "assessment_count": int(result.get("assessment_count") or 0),
        "attempt_count": int(result.get("attempt_count") or 0),
        "retry_count": int(result.get("retry_count") or 0),
        "elapsed_seconds": float(result.get("elapsed_seconds") or 0.0),
        "verdict_counts": dict(summary.get("verdict_counts") or {}),
        "material_risk_counts": dict(summary.get("material_risk_counts") or {}),
        "source_trust_counts": dict(summary.get("source_trust_counts") or {}),
        "repair_action_counts": dict(summary.get("repair_action_counts") or {}),
        "repair_plan": repair_plan,
        "decision_packet_count": int(summary.get("decision_packet_count") or 0),
        "decision_packet_action_counts": dict(summary.get("decision_packet_action_counts") or {}),
        "decision_packets": decision_packets,
        "auto_clear_candidate_count": int(summary.get("auto_clear_candidate_count") or 0),
        "auto_clear_candidate_ids": list(summary.get("auto_clear_candidate_ids") or []),
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    risk_counts: Counter[str] = Counter()
    trust_counts: Counter[str] = Counter()
    repair_action_counts: Counter[str] = Counter()
    decision_packet_action_counts: Counter[str] = Counter()
    for row in rows:
        status_counts.update([str(row.get("status") or "unknown")])
        verdict_counts.update(row.get("verdict_counts") or {})
        risk_counts.update(row.get("material_risk_counts") or {})
        trust_counts.update(row.get("source_trust_counts") or {})
        repair_action_counts.update(row.get("repair_action_counts") or {})
        decision_packet_action_counts.update(row.get("decision_packet_action_counts") or {})
    return {
        "file_count": len(rows),
        "candidate_count": sum(int(row.get("candidate_count") or 0) for row in rows),
        "assessment_count": sum(int(row.get("assessment_count") or 0) for row in rows),
        "auto_clear_candidate_count": sum(int(row.get("auto_clear_candidate_count") or 0) for row in rows),
        "status_counts": _count_dict(status_counts),
        "verdict_counts": _count_dict(verdict_counts),
        "material_risk_counts": _count_dict(risk_counts),
        "source_trust_counts": _count_dict(trust_counts),
        "repair_action_counts": _count_dict(repair_action_counts),
        "decision_packet_count": sum(int(row.get("decision_packet_count") or 0) for row in rows),
        "decision_packet_action_counts": _count_dict(decision_packet_action_counts),
        "total_attempts": sum(int(row.get("attempt_count") or 0) for row in rows),
        "total_retries": sum(int(row.get("retry_count") or 0) for row in rows),
        "total_elapsed_seconds": round(sum(float(row.get("elapsed_seconds") or 0.0) for row in rows), 2),
    }


def _markdown(batch: dict[str, Any]) -> str:
    summary = batch.get("summary") or {}
    lines = [
        "# Evidence Material Diff LLM Shadow",
        "",
        f"- Runtime effect: `{str(bool(batch.get('runtime_effect'))).lower()}`",
        f"- Prompt effect: `{str(bool(batch.get('prompt_effect'))).lower()}`",
        f"- Persistence effect: `{str(bool(batch.get('persistence_effect'))).lower()}`",
        f"- Execute: `{str(bool(batch.get('execute'))).lower()}`",
        f"- Model: `{batch.get('model') or ''}`",
        "",
        "## Summary",
        "",
    ]
    for key in [
        "file_count",
        "candidate_count",
        "assessment_count",
        "auto_clear_candidate_count",
        "status_counts",
        "verdict_counts",
        "material_risk_counts",
        "source_trust_counts",
        "repair_action_counts",
        "decision_packet_count",
        "decision_packet_action_counts",
        "total_attempts",
        "total_retries",
        "total_elapsed_seconds",
    ]:
        lines.append(f"- `{key}`: `{summary.get(key)}`")
    lines.extend(["", "## Rows", ""])
    lines.append("| Runs | Status | Candidates | Assessments | Verdicts | Auto-clear candidates |")
    lines.append("| --- | --- | ---: | ---: | --- | ---: |")
    for row in batch.get("rows") or []:
        lines.append(
            "| {runs} | {status} | {candidates} | {assessments} | {verdicts} | {auto_clear} |".format(
                runs=", ".join(str(item) for item in row.get("run_ids") or []) or "-",
                status=_md_cell(row.get("status") or ""),
                candidates=row.get("candidate_count") or 0,
                assessments=row.get("assessment_count") or 0,
                verdicts=_md_cell(str(row.get("verdict_counts") or {})),
                auto_clear=row.get("auto_clear_candidate_count") or 0,
            )
        )
    repair_rows = [
        repair
        for row in batch.get("rows") or []
        for repair in row.get("repair_plan") or []
        if isinstance(repair, dict)
    ]
    if repair_rows:
        lines.extend(["", "## Repair Plan", ""])
        lines.append("| Run | Brand | Action | Lane | Trust | Risk | Fields |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for repair in repair_rows:
            lines.append(
                "| {run_id} | {brand} | {action} | {lane} | {trust} | {risk} | {fields} |".format(
                    run_id=repair.get("run_id") or "",
                    brand=_md_cell(repair.get("brand_name") or ""),
                    action=_md_cell(repair.get("action") or ""),
                    lane=_md_cell(repair.get("lane") or ""),
                    trust=_md_cell(repair.get("source_trust") or ""),
                    risk=_md_cell(repair.get("material_risk") or ""),
                    fields=_md_cell(", ".join(repair.get("affected_material_fields") or [])),
                )
            )
    packet_rows = [
        packet
        for row in batch.get("rows") or []
        for packet in row.get("decision_packets") or []
        if isinstance(packet, dict)
    ]
    if packet_rows:
        lines.extend(["", "## Decision Packets", ""])
        lines.append("| Run | Brand | Recommended decision | Requires recompute | Allowed decisions |")
        lines.append("| --- | --- | --- | --- | --- |")
        for packet in packet_rows:
            lines.append(
                "| {run_id} | {brand} | {decision} | {recompute} | {allowed} |".format(
                    run_id=packet.get("run_id") or "",
                    brand=_md_cell(packet.get("brand_name") or ""),
                    decision=_md_cell(packet.get("recommended_decision") or ""),
                    recompute=str(bool(packet.get("requires_recompute"))).lower(),
                    allowed=_md_cell(", ".join(packet.get("allowed_decisions") or [])),
                )
            )
    lines.append("")
    return "\n".join(lines)


def _count_dict(counter: Counter[str]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0]))}


def _md_cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _elapsed(started: float) -> float:
    return round(time.monotonic() - started, 2)


if __name__ == "__main__":
    raise SystemExit(main())
