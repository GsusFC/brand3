#!/usr/bin/env python3
"""Attach a Context.dev candidate summary JSON to a persisted Brand3 run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import BRAND3_DB_PATH
from src.storage.sqlite_store import SQLiteStore


RAW_INPUT_SOURCE = "contextdev_candidate_summary"


def main() -> int:
    args = _parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise ValueError("Context.dev candidate summary must be a JSON object.")

    store = SQLiteStore(args.db_path or BRAND3_DB_PATH)
    try:
        if not store.get_run_snapshot(args.run_id):
            raise ValueError(f"Run {args.run_id} does not exist.")
        store.save_raw_input(args.run_id, RAW_INPUT_SOURCE, summary)
    finally:
        store.close()

    print(f"Attached {RAW_INPUT_SOURCE} to run {args.run_id}")
    print(f"candidate_count={summary.get('candidate_count', 0)}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--db-path", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
