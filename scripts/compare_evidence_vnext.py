from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import BRAND3_DB_PATH
from src.research.evidence_vnext import compare_legacy_current_and_vnext_from_snapshot
from src.research.evidence_vnext_report import (
    _print_changed_fields,
    _print_gate_reasons,
    build_batch_report,
    render_batch_report_markdown,
)
from src.storage.sqlite_store import SQLiteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare current evidence graph outputs against isolated evidence vNext outputs.",
    )
    parser.add_argument("run_ids", nargs="*", type=int, help="Brand Audit run IDs to compare.")
    parser.add_argument("--db", type=Path, default=Path(BRAND3_DB_PATH), help="SQLite database path.")
    parser.add_argument("--limit", type=int, default=8, help="Compare latest completed runs when run IDs are omitted.")
    parser.add_argument("--json", action="store_true", help="Emit full JSON artifacts.")
    parser.add_argument("--report-json", type=Path, help="Write compact batch report JSON.")
    parser.add_argument("--report-md", type=Path, help="Write compact batch report Markdown.")
    args = parser.parse_args(argv)

    store = SQLiteStore(str(args.db))
    try:
        run_ids = args.run_ids or _latest_run_ids(store, args.limit)
        results = []
        for run_id in run_ids:
            snapshot = store.get_run_snapshot(run_id)
            if snapshot is None:
                print(f"run {run_id}: not found")
                continue
            results.append(compare_legacy_current_and_vnext_from_snapshot(snapshot))
    finally:
        store.close()

    report = build_batch_report(results, db_path=str(args.db))
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.report_md:
        args.report_md.parent.mkdir(parents=True, exist_ok=True)
        args.report_md.write_text(render_batch_report_markdown(report), encoding="utf-8")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    for result in results:
        comparison = result["vnext_comparison"]
        summary = comparison["summary"]
        gate = result["vnext_gate"]["summary"]
        scorecard = summary["scorecard"]
        print(
            f"run={comparison['run_id']} brand={comparison['brand_name']} "
            f"status={scorecard['status']} "
            f"accepted={gate['accepted_count']} review={gate['review_required_count']} rejected={gate['rejected_count']} "
            f"reclassified_noise={summary['reclassified_to_noise_count']} "
            f"claim_delta={summary['claim_delta']} noise_delta={summary['noise_delta']} "
            f"changed={summary['changed_count']} lost={summary['lost_count']} material_lost={summary['material_lost_count']}"
        )
        _print_gate_reasons(gate)
        _print_changed_fields(comparison)
    return 0


def _latest_run_ids(store: SQLiteStore, limit: int) -> list[int]:
    rows = store.conn.execute(
        """
        SELECT id
        FROM runs
        WHERE completed_at IS NOT NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [int(row["id"]) for row in rows]


if __name__ == "__main__":
    raise SystemExit(main())
