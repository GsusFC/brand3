"""SV9 shadow replay: score historical Brand Audit runs with the SV9 engine.

Step 0 of the SV9 implementation order (design doc section 16): the engine runs
in shadow over persisted snapshots — no collection, no public surface, no V5
mutation. Output: sv9_* tables plus a V5-vs-SV9 comparison table where the
biggest divergences are the first human calibration batch.

Usage:
  ./.venv/bin/python scripts/sv9_shadow_replay.py --limit 20
  ./.venv/bin/python scripts/sv9_shadow_replay.py --run-id 175
  ./.venv/bin/python scripts/sv9_shadow_replay.py --limit 50 --skip-existing
  ./.venv/bin/python scripts/sv9_shadow_replay.py --limit 20 --markdown out.md

LLM detection/evaluation responses are cached in the shared llm_cache table,
so re-running over the same snapshots is cheap.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import BRAND3_DB_PATH
from src.storage.sqlite_store import SQLiteStore
from src.sv9.models import Sv9ScanResult
from src.sv9.rubric import PRESENTATION_ORDER, RUBRIC_VERSION
from src.sv9.service import detect_for_snapshot, run_sv9_from_audit_snapshot
from src.sv9.store import Sv9Store


def _candidate_run_ids(store: SQLiteStore, *, run_id: int | None, limit: int) -> list[int]:
    if run_id is not None:
        return [run_id]
    runs = store.list_runs(limit=limit)
    return [int(r["id"]) for r in runs if r.get("completed_at")]


def _replay_run(
    store: SQLiteStore,
    sv9_store: Sv9Store,
    run_id: int,
) -> tuple[Sv9ScanResult, int] | None:
    snapshot = store.get_run_snapshot(run_id)
    if snapshot is None:
        print(f"  run #{run_id}: no snapshot, skipped")
        return None
    detection = sv9_store.get_detection(run_id)
    if detection is None:
        detection = detect_for_snapshot(snapshot)
        sv9_store.save_detection(run_id, detection)
    result = run_sv9_from_audit_snapshot(snapshot, magnetism_result=detection)
    scan_id = sv9_store.save_scan(result)
    return result, scan_id


def _comparison_rows(
    store: SQLiteStore,
    results: list[tuple[int, Sv9ScanResult, int]],
) -> list[dict[str, Any]]:
    rows = []
    for run_id, result, scan_id in results:
        snapshot_run = store.conn.execute(
            "SELECT composite_score FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        v5 = snapshot_run["composite_score"] if snapshot_run else None
        v5_value = round(float(v5), 1) if v5 is not None else None
        delta = round(result.brand3_score - v5_value, 1) if v5_value is not None else None
        rows.append(
            {
                "run_id": run_id,
                "scan_id": scan_id,
                "brand": result.brand_name,
                "v5_composite": v5_value,
                "sv9_score": result.brand3_score,
                "delta": delta,
                "magnetism_capped": result.magnetism_capped,
                "needs_review": result.needs_review,
                "complete": result.is_complete,
                "not_detected": ",".join(result.not_detected) or "-",
                "not_evaluated": ",".join(result.not_evaluated) or "-",
            }
        )
    rows.sort(key=lambda r: -(abs(r["delta"]) if r["delta"] is not None else -1))
    return rows


def _format_table(rows: list[dict[str, Any]], *, markdown: bool = False) -> str:
    headers = [
        "run", "scan", "brand", "V5", "SV9", "delta",
        "cap", "review", "complete", "not_detected", "not_evaluated",
    ]
    lines = []
    if markdown:
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join("---" for _ in headers) + "|")
    else:
        lines.append("  ".join(f"{h:<14}" for h in headers))
    for row in rows:
        cells = [
            str(row["run_id"]),
            str(row["scan_id"]),
            str(row["brand"])[:24],
            str(row["v5_composite"]),
            str(row["sv9_score"]),
            str(row["delta"]),
            "x2cap" if row["magnetism_capped"] else "-",
            "REVIEW" if row["needs_review"] else "-",
            "yes" if row["complete"] else "PARTIAL",
            row["not_detected"],
            row["not_evaluated"],
        ]
        if markdown:
            lines.append("| " + " | ".join(cells) + " |")
        else:
            lines.append("  ".join(f"{c:<14}" for c in cells))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="SV9 shadow replay over historical runs")
    parser.add_argument("--run-id", type=int, default=None, help="Replay a single run")
    parser.add_argument("--limit", type=int, default=20, help="How many recent runs to replay")
    parser.add_argument("--db-path", default=BRAND3_DB_PATH)
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip runs that already have an SV9 scan for the current rubric version",
    )
    parser.add_argument("--markdown", default=None, help="Also write the comparison table to this .md file")
    args = parser.parse_args()

    store = SQLiteStore(args.db_path)
    sv9_store = Sv9Store(args.db_path)
    results: list[tuple[int, Sv9ScanResult, int]] = []
    try:
        run_ids = _candidate_run_ids(store, run_id=args.run_id, limit=args.limit)
        if not run_ids:
            print("No completed runs found to replay.")
            return 1
        print(f"SV9 shadow replay · rubric {RUBRIC_VERSION} · {len(run_ids)} run(s)")

        for run_id in run_ids:
            if args.skip_existing:
                existing = sv9_store.get_scan_for_run(run_id)
                if existing and existing.get("rubric_version") == RUBRIC_VERSION:
                    print(f"  run #{run_id}: already scanned (scan #{existing['id']}), skipped")
                    continue
            print(f"  run #{run_id}: evaluating...")
            replayed = _replay_run(store, sv9_store, run_id)
            if replayed is None:
                continue
            result, scan_id = replayed
            results.append((run_id, result, scan_id))
            flags = []
            if result.magnetism_capped:
                flags.append("magnetism capped")
            if result.needs_review:
                flags.append("coherencia review")
            if not result.is_complete:
                flags.append(f"partial ({len(result.not_evaluated)} not evaluated)")
            flag_text = f"  [{'; '.join(flags)}]" if flags else ""
            print(
                f"  run #{run_id}: SV9 {result.brand3_score}/100 "
                f"(scan #{scan_id}){flag_text}"
            )

        if not results:
            print("Nothing replayed.")
            return 0

        rows = _comparison_rows(store, results)
        print("\nV5 vs SV9 (sorted by |delta|; the top rows are the first calibration batch):\n")
        print(_format_table(rows))

        component_lines = []
        for run_id, result, _scan_id in results:
            scores = " ".join(
                f"{key}={result.components[key].score if result.components[key].status == 'scored' else result.components[key].status}"
                for key in PRESENTATION_ORDER
            )
            component_lines.append(f"  run #{run_id} {result.brand_name}: {scores}")
        print("\nComponent detail:")
        print("\n".join(component_lines))

        if args.markdown:
            Path(args.markdown).write_text(
                f"# SV9 shadow replay · {RUBRIC_VERSION}\n\n" + _format_table(rows, markdown=True) + "\n",
                encoding="utf-8",
            )
            print(f"\nComparison table written to {args.markdown}")
        return 0
    finally:
        store.close()
        sv9_store.close()


if __name__ == "__main__":
    raise SystemExit(main())
