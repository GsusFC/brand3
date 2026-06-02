#!/usr/bin/env python3
"""Run Context.dev Research Pack dry-runs against local Brand3 runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.config import BRAND3_DB_PATH
from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot
from src.research.contextdev_research_pack_dry_run import build_contextdev_research_pack_dry_run
from src.research.evidence_graph import build_evidence_graph_from_snapshot
from src.research.research_pack_builder import build_brand_research_pack_from_graph
from src.storage.sqlite_store import SQLiteStore


def main() -> int:
    args = _parse_args()
    candidate_summary = json.loads(args.candidate_summary.read_text(encoding="utf-8"))
    store = SQLiteStore(str(args.db))
    try:
        run_ids = args.run_ids or _latest_run_ids(store, args.limit)
        reports = [
            _build_run_report(store, run_id, candidate_summary, builder=args.builder, mode=args.mode)
            for run_id in run_ids
        ]
    finally:
        store.close()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for report in reports:
        run_id = report.get("run_id") or "unknown"
        (args.output_dir / f"run-{run_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = _summarize_reports(reports, builder=args.builder, mode=args.mode, db_path=str(args.db))
    (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.output_dir}")
    print(f"Summary: runs={summary['run_count']} updates={summary['total_updates']} statuses={summary['status_counts']}")
    return 0


def _build_run_report(
    store: SQLiteStore,
    run_id: int,
    candidate_summary: dict[str, Any],
    *,
    builder: str,
    mode: str,
) -> dict[str, Any]:
    snapshot = store.get_run_snapshot(run_id)
    if snapshot is None:
        return {"run_id": run_id, "status": "not_found"}

    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    try:
        pack = _build_pack(snapshot, builder=builder)
        dry_run = build_contextdev_research_pack_dry_run(pack, candidate_summary, mode=mode).to_dict()
    except Exception as exc:  # pragma: no cover - defensive for ad hoc local runs.
        return {
            "run_id": run_id,
            "status": "error",
            "brand_name": str(run.get("brand_name") or ""),
            "url": str(run.get("url") or ""),
            "error": str(exc),
        }

    return {
        "run_id": run_id,
        "status": "ok",
        "builder": builder,
        "mode": mode,
        "brand_name": str(run.get("brand_name") or ""),
        "url": str(run.get("url") or ""),
        "pack_entity_type": dry_run["original_pack"].get("entity_type"),
        "pack_parent_brand": dry_run["original_pack"].get("parent_brand"),
        "field_update_count": len(dry_run["field_updates"]),
        "promotion_status_counts": dry_run["promotion_report"]["status_counts"],
        "field_updates": dry_run["field_updates"],
        "dry_run": dry_run,
    }


def _build_pack(snapshot: dict[str, Any], *, builder: str):
    if builder == "legacy":
        return build_brand_research_pack_from_snapshot(snapshot)
    graph = build_evidence_graph_from_snapshot(snapshot)
    return build_brand_research_pack_from_graph(graph)


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


def _summarize_reports(reports: list[dict[str, Any]], *, builder: str, mode: str, db_path: str) -> dict[str, Any]:
    status_counts = {"promotable": 0, "review_required": 0, "blocked": 0}
    total_updates = 0
    rows = []
    for report in reports:
        if report.get("status") != "ok":
            rows.append({"run_id": report.get("run_id"), "status": report.get("status"), "updates": 0})
            continue
        total_updates += int(report.get("field_update_count") or 0)
        for key, value in (report.get("promotion_status_counts") or {}).items():
            status_counts[key] = status_counts.get(key, 0) + int(value or 0)
        rows.append(
            {
                "run_id": report.get("run_id"),
                "status": report.get("status"),
                "brand_name": report.get("brand_name"),
                "url": report.get("url"),
                "updates": report.get("field_update_count"),
                "promotion_status_counts": report.get("promotion_status_counts"),
            }
        )
    return {
        "version": "contextdev_run_pack_dry_run_batch_v0_1",
        "builder": builder,
        "mode": mode,
        "db_path": db_path,
        "run_count": len(reports),
        "ok_count": sum(1 for report in reports if report.get("status") == "ok"),
        "total_updates": total_updates,
        "status_counts": status_counts,
        "runs": rows,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_ids", nargs="*", type=int, help="Run IDs to evaluate. Defaults to latest completed runs.")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--db", type=Path, default=Path(BRAND3_DB_PATH))
    parser.add_argument("--builder", choices=("graph", "legacy"), default="graph")
    parser.add_argument("--mode", choices=("full", "visual_only"), default="full")
    parser.add_argument("--candidate-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("out/contextdev_run_pack_dry_run"))
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
