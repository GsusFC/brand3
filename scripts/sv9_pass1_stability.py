#!/usr/bin/env python3
"""Probe Pass 1 stability on fixed audit snapshots."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from src.config import BRAND3_DB_PATH
from src.services.magnetism_service import load_brand_audit_snapshot
from src.sv9.detection_trace import detection_fingerprint, diff_tldr_brand3
from src.sv9.service import detect_for_snapshot
from src.sv9.store import Sv9Store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_ids", nargs="+", type=int)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--db-path", default=BRAND3_DB_PATH)
    parser.add_argument("--output", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary: dict[str, object] = {
        "schema_version": "sv9-pass1-stability-v1",
        "iterations": args.iterations,
        "runs": [],
    }
    with Sv9Store(args.db_path) as store:
        for run_id in args.run_ids:
            snapshot = load_brand_audit_snapshot(run_id, db_path=args.db_path)
            samples = []
            for index in range(args.iterations):
                payload = detect_for_snapshot(snapshot)
                fingerprint = detection_fingerprint(payload)
                sample_id = store.record_detection_run(
                    run_id,
                    payload,
                    source="stability_probe",
                    fingerprint=fingerprint,
                )
                samples.append(
                    {
                        "sample_id": sample_id,
                        "iteration": index + 1,
                        "payload": payload,
                        "fingerprint": fingerprint,
                    }
                )
            baseline = samples[0]
            diffs_vs_first = []
            changed_path_counter: collections.Counter[str] = collections.Counter()
            changed_block_counter: collections.Counter[str] = collections.Counter()
            for sample in samples[1:]:
                diffs = diff_tldr_brand3(baseline["payload"], sample["payload"])
                diffs_vs_first.append(
                    {
                        "sample_id": sample["sample_id"],
                        "iteration": sample["iteration"],
                        "diff_count": len(diffs),
                        "diffs": diffs,
                    }
                )
                for diff in diffs:
                    path = str(diff.get("path") or "")
                    if not path:
                        continue
                    changed_path_counter[path] += 1
                    changed_block_counter[path.split(".", 1)[0]] += 1
            summary["runs"].append(
                {
                    "run_id": run_id,
                    "sample_ids": [sample["sample_id"] for sample in samples],
                    "tldr_hashes": [sample["fingerprint"]["tldr_hash"] for sample in samples],
                    "block_hashes": [
                        sample["fingerprint"]["block_hashes"] for sample in samples
                    ],
                    "diffs_vs_first": diffs_vs_first,
                    "top_changed_paths": [
                        {"path": path, "count": count}
                        for path, count in changed_path_counter.most_common(20)
                    ],
                    "top_changed_blocks": [
                        {"block": block, "count": count}
                        for block, count in changed_block_counter.most_common()
                    ],
                }
            )

    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
