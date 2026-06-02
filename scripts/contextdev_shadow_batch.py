#!/usr/bin/env python3
"""Attach a Context.dev summary and render shadow reports for multiple runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.contextdev_attach_candidate_summary_to_run import RAW_INPUT_SOURCE
from scripts.contextdev_shadow_report import _build_report, _run_shadow_report, render_markdown
from src.config import BRAND3_DB_PATH
from src.storage.sqlite_store import SQLiteStore


def main() -> int:
    args = _parse_args()
    runs = _load_runs(args.runs_file)
    summary = _load_summary(args.summary)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    reports = run_batch(
        runs=runs,
        summary=summary,
        output_dir=output_dir,
        db_path=args.db_path or BRAND3_DB_PATH,
        attach=not args.no_attach,
        force_attach=args.force_attach,
    )
    index = _build_index(reports)
    (output_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "index.md").write_text(render_index_markdown(index), encoding="utf-8")
    print(f"Wrote {output_dir / 'index.json'}")
    print(f"Wrote {output_dir / 'index.md'}")
    print(f"Summary: runs={index['run_count']} evaluated={index['evaluated_count']} updates={index['total_updates']}")
    return 0


def run_batch(
    *,
    runs: list[dict[str, Any]],
    summary: dict[str, Any],
    output_dir: Path,
    db_path: str,
    attach: bool,
    force_attach: bool,
) -> list[dict[str, Any]]:
    reports = []
    if attach:
        _attach_summary_to_runs(
            runs=runs,
            summary=summary,
            db_path=db_path,
            force_attach=force_attach,
        )

    for item in runs:
        run_id = _run_id(item)
        report = _build_report(_run_shadow_report(run_id, db_path=db_path))
        label = str(item.get("label") or f"run-{run_id}")
        report["selection"] = {
            "label": label,
            "expected_brand": item.get("brand"),
            "expected_url": item.get("url"),
        }
        (output_dir / f"{label}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (output_dir / f"{label}.md").write_text(render_markdown(report), encoding="utf-8")
        reports.append(report)
    return reports


def render_index_markdown(index: dict[str, Any]) -> str:
    lines = [
        "# Context.dev Shadow Batch",
        "",
        f"- Runs: `{index['run_count']}`",
        f"- Evaluated: `{index['evaluated_count']}`",
        f"- Total updates: `{index['total_updates']}`",
        "",
        "| Run | Brand | Status | Updates | Promotable | Review | Blocked |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in index["runs"]:
        counts = row.get("status_counts") or {}
        lines.append(
            "| {run_id} | {brand} | {status} | {updates} | {promotable} | {review} | {blocked} |".format(
                run_id=row.get("run_id"),
                brand=row.get("brand_name"),
                status=row.get("shadow_status"),
                updates=row.get("field_update_count"),
                promotable=counts.get("promotable", 0),
                review=counts.get("review_required", 0),
                blocked=counts.get("blocked", 0),
            )
        )
    return "\n".join(lines).strip() + "\n"


def _attach_summary_to_runs(
    *,
    runs: list[dict[str, Any]],
    summary: dict[str, Any],
    db_path: str,
    force_attach: bool,
) -> None:
    store = SQLiteStore(db_path)
    try:
        for item in runs:
            run_id = _run_id(item)
            snapshot = store.get_run_snapshot(run_id)
            if snapshot is None:
                raise ValueError(f"Run {run_id} does not exist.")
            if not force_attach and _has_contextdev_summary(snapshot):
                continue
            store.save_raw_input(run_id, RAW_INPUT_SOURCE, summary)
    finally:
        store.close()


def _build_index(reports: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    total_updates = 0
    evaluated_count = 0
    for report in reports:
        shadow = report.get("shadow") if isinstance(report.get("shadow"), dict) else {}
        update_count = int(shadow.get("field_update_count") or 0)
        total_updates += update_count
        if shadow.get("status") == "evaluated":
            evaluated_count += 1
        rows.append(
            {
                "run_id": report.get("run_id"),
                "label": (report.get("selection") or {}).get("label"),
                "brand_name": report.get("brand_name"),
                "url": report.get("url"),
                "shadow_status": shadow.get("status"),
                "field_update_count": update_count,
                "status_counts": shadow.get("status_counts") or {},
                "tldr_generation_mode": report.get("tldr_generation_mode"),
            }
        )
    return {
        "version": "contextdev_shadow_batch_v0_1",
        "run_count": len(reports),
        "evaluated_count": evaluated_count,
        "total_updates": total_updates,
        "runs": rows,
    }


def _has_contextdev_summary(snapshot: dict[str, Any]) -> bool:
    return any(item.get("source") == RAW_INPUT_SOURCE for item in snapshot.get("raw_inputs") or [] if isinstance(item, dict))


def _load_runs(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Runs file must be a JSON array.")
    runs = [item for item in raw if isinstance(item, dict)]
    if not runs:
        raise ValueError("Runs file does not contain any run objects.")
    for item in runs:
        _run_id(item)
    return runs


def _load_summary(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Context.dev summary must be a JSON object.")
    return raw


def _run_id(item: dict[str, Any]) -> int:
    value = item.get("run_id")
    if value is None:
        raise ValueError(f"Run object is missing run_id: {item}")
    return int(value)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-file", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("out/contextdev_shadow_batch"))
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--no-attach", action="store_true")
    parser.add_argument("--force-attach", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
