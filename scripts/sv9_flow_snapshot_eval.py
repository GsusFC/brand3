#!/usr/bin/env python3
"""Evaluate SV9 Flow repeats from a fixed audit snapshot JSON.

This validates the evidence-first flow without relying on Pass 1/TLDR. The
input can be a raw Brand Audit snapshot or the Scanner API
`/audit-snapshot?full=true` envelope, whose snapshot is stored under `debug`,
or a deploy-selected envelope whose snapshot is stored under `snapshot`.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable

from scripts.sv9_flow_local_eval import _compact_shadow_payload, compare_flow_repeats
from scripts.sv9_flow_shadow_run import _load_env_file, build_shadow_flow_for_run

SV9_FLOW_SNAPSHOT_EVAL_VERSION = "sv9-flow-snapshot-eval-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_json")
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--env-file", default="")
    parser.add_argument("--disable-llm-cache", action="store_true")
    parser.add_argument("--full-runs", action="store_true")
    parser.add_argument("--output", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env_file:
        _load_env_file(args.env_file)
    if args.disable_llm_cache:
        os.environ["BRAND3_LLM_CACHE_ENABLED"] = "false"

    envelope = json.loads(Path(args.snapshot_json).read_text(encoding="utf-8"))
    report = build_snapshot_eval(
        envelope,
        repeat=args.repeat,
        include_full_runs=args.full_runs,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def build_snapshot_eval(
    envelope: dict[str, Any],
    *,
    repeat: int = 2,
    include_full_runs: bool = False,
    shadow_builder: Callable[..., dict[str, Any]] = build_shadow_flow_for_run,
) -> dict[str, Any]:
    snapshot, run_id = snapshot_and_run_id_from_envelope(envelope)
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}

    def load_snapshot_fn(_run_id: int, db_path: str) -> dict[str, Any]:
        return snapshot

    payloads = [
        shadow_builder(
            run_id,
            db_path="snapshot_json",
            interpretation_source="flow-llm",
            load_snapshot_fn=load_snapshot_fn,
            get_cached_detection_fn=lambda _run_id, _db_path: None,
            visual_signature_fn=lambda _snapshot: None,
            report_only=False,
        )
        for _ in range(max(1, int(repeat)))
    ]
    return {
        "schema_version": SV9_FLOW_SNAPSHOT_EVAL_VERSION,
        "source_run_id": run_id,
        "brand_name": run.get("brand_name"),
        "url": run.get("url"),
        "repeat": len(payloads),
        "stability": compare_flow_repeats(payloads),
        "runs": payloads if include_full_runs else [_compact_shadow_payload(payload) for payload in payloads],
    }


def snapshot_and_run_id_from_envelope(envelope: dict[str, Any]) -> tuple[dict[str, Any], int]:
    if isinstance(envelope.get("debug"), dict):
        snapshot = envelope["debug"]
    elif isinstance(envelope.get("snapshot"), dict):
        snapshot = envelope["snapshot"]
    else:
        snapshot = envelope
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    run_id = int(envelope.get("source_run_id") or run.get("id") or 0)
    if run_id <= 0:
        raise ValueError("missing source_run_id/run.id")
    return snapshot, run_id


if __name__ == "__main__":
    raise SystemExit(main())
