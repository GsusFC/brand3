#!/usr/bin/env python3
"""Evaluate SV9 Flow candidates against local Brand3 DB runs.

This is a validation harness, not a product scanner. It reads existing local
audit runs, compares cached Pass 1 against optional flow-LLM runs, and writes a
reproducible JSON report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from scripts.sv9_flow_shadow_run import build_shadow_flow_for_run, _load_env_file
from src.config import BRAND3_DB_PATH

SV9_FLOW_LOCAL_EVAL_VERSION = "sv9-flow-local-eval-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_ids", nargs="+", type=int)
    parser.add_argument("--db-path", default=BRAND3_DB_PATH)
    parser.add_argument("--output", default="")
    parser.add_argument("--env-file", default="")
    parser.add_argument(
        "--include-flow-llm",
        action="store_true",
        help="Also run the experimental flow-LLM interpretation.",
    )
    parser.add_argument(
        "--flow-repeat",
        type=int,
        default=1,
        help="Number of flow-LLM repeats per run when --include-flow-llm is set.",
    )
    parser.add_argument(
        "--disable-llm-cache",
        action="store_true",
        help="Disable LLM cache for flow-LLM repeats to measure live drift.",
    )
    parser.add_argument(
        "--full-candidates",
        action="store_true",
        help="Include full candidate payloads. Default stores compact reports only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env_file:
        _load_env_file(args.env_file)
    if args.disable_llm_cache:
        os.environ["BRAND3_LLM_CACHE_ENABLED"] = "false"

    payload = build_local_eval(
        args.run_ids,
        db_path=args.db_path,
        include_flow_llm=args.include_flow_llm,
        flow_repeat=args.flow_repeat,
        report_only=not args.full_candidates,
    )
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def build_local_eval(
    run_ids: list[int],
    *,
    db_path: str = BRAND3_DB_PATH,
    include_flow_llm: bool = False,
    flow_repeat: int = 1,
    report_only: bool = True,
    shadow_builder: Callable[..., dict[str, Any]] = build_shadow_flow_for_run,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for run_id in run_ids:
        cached = shadow_builder(
            run_id,
            db_path=db_path,
            interpretation_source="cached-pass1",
            report_only=report_only,
        )
        run_payload: dict[str, Any] = {
            "run_id": run_id,
            "cached_pass1": _compact_shadow_payload(cached),
        }
        if include_flow_llm:
            flow_runs = [
                shadow_builder(
                    run_id,
                    db_path=db_path,
                    interpretation_source="flow-llm",
                    report_only=False,
                )
                for _ in range(max(1, int(flow_repeat)))
            ]
            run_payload["flow_llm"] = [_compact_shadow_payload(item) for item in flow_runs]
            run_payload["flow_llm_stability"] = compare_flow_repeats(flow_runs)
        runs.append(run_payload)

    return {
        "schema_version": SV9_FLOW_LOCAL_EVAL_VERSION,
        "db_path": db_path,
        "include_flow_llm": bool(include_flow_llm),
        "flow_repeat": max(1, int(flow_repeat)) if include_flow_llm else 0,
        "runs": runs,
        "summary": summarize_eval_runs(runs),
    }


def compare_flow_repeats(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    compact = [_compact_shadow_payload(payload) for payload in payloads]
    if not compact:
        return {
            "repeat_count": 0,
            "same_detected_blocks": True,
            "same_tile_effects": True,
            "same_block_content_hashes": True,
            "changed_content_blocks": [],
        }
    baseline = compact[0]
    baseline_blocks = set(baseline["detected_blocks"])
    baseline_effects = baseline["tile_signal_effects"]
    baseline_hashes = baseline["block_content_hashes"]
    changed_blocks: set[str] = set()
    same_detected = True
    same_effects = True
    same_hashes = True
    for item in compact[1:]:
        if set(item["detected_blocks"]) != baseline_blocks:
            same_detected = False
        if item["tile_signal_effects"] != baseline_effects:
            same_effects = False
        if item["block_content_hashes"] != baseline_hashes:
            same_hashes = False
            for block, digest in item["block_content_hashes"].items():
                if baseline_hashes.get(block) != digest:
                    changed_blocks.add(block)
            for block in set(baseline_hashes) - set(item["block_content_hashes"]):
                changed_blocks.add(block)
    return {
        "repeat_count": len(compact),
        "same_detected_blocks": same_detected,
        "same_tile_effects": same_effects,
        "same_block_content_hashes": same_hashes,
        "changed_content_blocks": sorted(changed_blocks),
    }


def summarize_eval_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    flow_runs = [run for run in runs if run.get("flow_llm")]
    unstable_detected = []
    unstable_effects = []
    textual_drift = []
    for run in flow_runs:
        stability = run.get("flow_llm_stability") or {}
        run_id = run.get("run_id")
        if stability.get("same_detected_blocks") is False:
            unstable_detected.append(run_id)
        if stability.get("same_tile_effects") is False:
            unstable_effects.append(run_id)
        if stability.get("same_block_content_hashes") is False:
            textual_drift.append(
                {
                    "run_id": run_id,
                    "blocks": stability.get("changed_content_blocks") or [],
                }
            )
    return {
        "run_count": len(runs),
        "flow_llm_run_count": len(flow_runs),
        "flow_llm_unstable_detected_run_ids": unstable_detected,
        "flow_llm_unstable_tile_effect_run_ids": unstable_effects,
        "flow_llm_textual_drift": textual_drift,
    }


def _compact_shadow_payload(payload: dict[str, Any]) -> dict[str, Any]:
    report = payload.get("report") if isinstance(payload.get("report"), dict) else {}
    candidate = payload.get("candidate") if isinstance(payload.get("candidate"), dict) else {}
    interpretation = candidate.get("interpretation") if isinstance(candidate.get("interpretation"), dict) else {}
    blocks = interpretation.get("blocks") if isinstance(interpretation.get("blocks"), dict) else {}
    detected_blocks = [
        block
        for block, value in sorted(blocks.items())
        if isinstance(value, dict) and value.get("detected") is True
    ]
    block_content_hashes = {
        block: _text_hash(str(blocks[block].get("content") or ""))
        for block in detected_blocks
    }
    return {
        "source_run_id": payload.get("source_run_id"),
        "detection_source": payload.get("detection_source"),
        "interpretation_source": payload.get("interpretation_source"),
        "visual_signature_present": payload.get("visual_signature_present"),
        "brand_name": report.get("brand_name"),
        "url": report.get("url"),
        "tile_signal_effects": report.get("tile_signal_effects") or {},
        "tile_signal_effects_by_component": report.get("tile_signal_effects_by_component") or {},
        "counts": report.get("counts") or {},
        "limitations": report.get("limitations") or [],
        "detected_blocks": detected_blocks,
        "block_content_hashes": block_content_hashes,
        "llm_status": (payload.get("llm_payload") or {}).get("status")
        if isinstance(payload.get("llm_payload"), dict)
        else None,
        "llm_detected_count": (payload.get("llm_payload") or {}).get("detected_count")
        if isinstance(payload.get("llm_payload"), dict)
        else None,
        "llm_block_failures": (payload.get("llm_payload") or {}).get("block_failures")
        if isinstance(payload.get("llm_payload"), dict)
        else None,
    }


def _text_hash(value: str) -> str:
    return hashlib.sha256(" ".join(value.split()).encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
