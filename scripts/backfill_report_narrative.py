"""Explicit operator tool to persist rich report narrative for selected runs.

This script intentionally requires run IDs. It never runs as part of public
report reads and never performs automatic mass backfills.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import BRAND3_DB_PATH
from src.features.llm_analyzer import LLMAnalyzer
from src.reports.dossier import (
    REPORT_NARRATIVE_SOURCE,
    build_report_narrative_payload,
)
from src.storage.sqlite_store import SQLiteStore


def backfill_run(store: SQLiteStore, run_id: int, *, dry_run: bool = False) -> dict:
    snapshot = store.get_run_snapshot(run_id)
    if not snapshot:
        raise ValueError(f"run_id={run_id} not found")

    payload = build_report_narrative_payload(snapshot, analyzer=LLMAnalyzer())
    summary = {
        "run_id": run_id,
        "brand": (snapshot.get("run") or {}).get("brand_name"),
        "source": REPORT_NARRATIVE_SOURCE,
        "dry_run": dry_run,
        "synthesis_chars": len(payload.get("synthesis_prose") or ""),
        "dimension_count": len(payload.get("findings_by_dimension") or {}),
    }
    if not dry_run:
        store.save_raw_input(run_id, REPORT_NARRATIVE_SOURCE, payload)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_ids", nargs="+", type=int)
    parser.add_argument("--db", default=str(BRAND3_DB_PATH))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    store = SQLiteStore(str(Path(args.db)))
    try:
        summaries = [
            backfill_run(store, run_id, dry_run=args.dry_run)
            for run_id in args.run_ids
        ]
    finally:
        store.close()

    print(json.dumps({"backfilled": summaries}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
