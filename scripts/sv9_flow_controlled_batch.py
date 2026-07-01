#!/usr/bin/env python3
"""Run a controlled SV9 Flow calibration batch from persisted Brand Audit snapshots."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sv9_flow_calibration_loop import build_calibration_packet, write_calibration_packet
from scripts.sv9_flow_shadow_run import _load_env_file
from scripts.sv9_flow_sv9_batch_report import build_batch_report, render_markdown_report
from scripts.sv9_flow_sv9_shadow_eval import build_flow_sv9_shadow_eval
from src.config import BRAND3_DB_PATH
from src.storage.sqlite_store import SQLiteStore


DEFAULT_PROVIDER_CALL_LIMIT = 300


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", dest="run_ids", action="append", type=int, default=[])
    parser.add_argument("--run-ids", dest="run_id_csv", default="", help="Comma-separated run IDs.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cohort-name", default="controlled_batch")
    parser.add_argument("--db-path", default=BRAND3_DB_PATH)
    parser.add_argument("--env-file", default="")
    parser.add_argument("--provider-call-limit", type=int, default=DEFAULT_PROVIDER_CALL_LIMIT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env_file:
        _load_env_file(args.env_file)
    run_ids = _parse_run_ids(args)
    if not run_ids:
        raise SystemExit("No run IDs provided.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    compare_paths: list[str] = []
    payloads: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    stopped_reason = ""
    provider_calls = 0

    store = SQLiteStore(args.db_path)
    try:
        for index, run_id in enumerate(run_ids, start=1):
            snapshot = store.get_run_snapshot(run_id)
            if snapshot is None:
                raise SystemExit(f"missing snapshot for run {run_id}")
            envelope = {
                "source": f"sqlite:{args.db_path}",
                "source_run_id": run_id,
                "snapshot": snapshot,
            }
            run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
            brand = str(run.get("brand_name") or run.get("url") or run_id)
            print(f"[{index}/{len(run_ids)}] running {brand} run_id={run_id}", flush=True)
            payload = build_flow_sv9_shadow_eval(envelope, include_full=False, compare_legacy=True)
            out_path = output_dir / f"{_slug(brand)}_{run_id}_sv9_shadow_compare.json"
            out_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            compare_paths.append(str(out_path))
            payloads.append(payload)
            batch_report = build_batch_report(payloads, sources=compare_paths)
            latest = (batch_report.get("runs") or [{}])[-1]
            cost = build_calibration_packet(payloads, sources=compare_paths).get("cost_observation") or {}
            observed = cost.get("observed_llm_usage") if isinstance(cost.get("observed_llm_usage"), dict) else {}
            provider_calls = int(observed.get("provider_calls") or 0)
            manifest.append(
                {
                    "run_id": run_id,
                    "brand_name": payload.get("brand_name"),
                    "url": payload.get("url"),
                    "output": str(out_path),
                    "assessment": latest.get("assessment"),
                    "assessment_kind": latest.get("assessment_kind"),
                    "score_delta": latest.get("score_delta"),
                    "provider_calls_so_far": provider_calls,
                }
            )
            print(
                "[{}/{}] wrote {} brand={} delta={:+} assessment={} kind={} provider_calls={}".format(
                    index,
                    len(run_ids),
                    out_path,
                    payload.get("brand_name"),
                    latest.get("score_delta") or 0,
                    latest.get("assessment"),
                    latest.get("assessment_kind"),
                    provider_calls,
                ),
                flush=True,
            )
            if latest.get("assessment_kind") == "technical_blocker":
                stopped_reason = f"technical_blocker:{payload.get('brand_name')}"
                break
            if provider_calls >= args.provider_call_limit:
                stopped_reason = f"provider_call_limit_reached:{provider_calls}>={args.provider_call_limit}"
                break
    finally:
        store.close()

    batch_report = build_batch_report(payloads, sources=compare_paths)
    (output_dir / "batch_report.json").write_text(
        json.dumps(batch_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "batch_report.md").write_text(render_markdown_report(batch_report) + "\n", encoding="utf-8")
    packet = build_calibration_packet(
        payloads,
        sources=compare_paths,
        cohort_name=args.cohort_name,
    )
    write_calibration_packet(packet, output_dir / "calibration_loop")
    summary = {
        "schema_version": "sv9-flow-controlled-batch-v1",
        "cohort_name": args.cohort_name,
        "requested_run_count": len(run_ids),
        "completed_run_count": len(payloads),
        "stopped_reason": stopped_reason,
        "provider_call_limit": args.provider_call_limit,
        "provider_calls": provider_calls,
        "batch_summary": batch_report.get("summary") or {},
        "manifest": manifest,
    }
    (output_dir / "controlled_batch_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _parse_run_ids(args: argparse.Namespace) -> list[int]:
    run_ids = list(args.run_ids or [])
    if args.run_id_csv:
        run_ids.extend(int(item.strip()) for item in args.run_id_csv.split(",") if item.strip())
    return run_ids


def _slug(value: object) -> str:
    text = str(value or "").lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "brand"


if __name__ == "__main__":
    raise SystemExit(main())
