#!/usr/bin/env python3
"""Run the evidence vNext LLM semantic classifier in shadow mode.

This script does not mutate runs, scoring, prompts, or persisted evidence. It is
for validating the optional LLM classifier against existing Brand Audit
snapshots.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from src.config import BRAND3_DB_PATH, BRAND3_EVIDENCE_LLM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.research.evidence_semantic_llm import build_llm_semantic_assessment
from src.research.evidence_vnext import (
    build_evidence_vnext_packet_from_snapshot,
    build_evidence_vnext_semantic_assessment,
)
from src.storage.sqlite_store import SQLiteStore


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    store = SQLiteStore(str(args.db))
    try:
        run_ids = args.run_ids or (
            _latest_distinct_run_ids(store, args.limit) if args.distinct_brands else _latest_run_ids(store, args.limit)
        )
        rows = []
        for run_id in run_ids:
            started = time.monotonic()
            snapshot = store.get_run_snapshot(run_id)
            if snapshot is None:
                rows.append({"run_id": run_id, "status": "not_found", "elapsed_seconds": _elapsed(started)})
                continue
            packet = build_evidence_vnext_packet_from_snapshot(snapshot)
            heuristic = build_evidence_vnext_semantic_assessment(packet)
            llm = build_llm_semantic_assessment(packet, llm=_llm_for_args(args), enabled=True)
            row = _row(packet=packet, heuristic=heuristic, llm=llm)
            row["elapsed_seconds"] = _elapsed(started)
            rows.append(row)
    finally:
        store.close()

    payload = {
        "version": "evidence_llm_shadow_run_v0_1",
        "runtime_effect": False,
        "prompt_effect": False,
        "persistence_effect": False,
        "db_path": str(args.db),
        "rows": rows,
        "summary": _summary(rows),
    }
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(_markdown(payload), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(
                "run={run_id} brand={brand_name} status={status} model={model} accepted={accepted} "
                "heuristic_material={heuristic_material} llm_material={llm_material} "
                "class_delta={class_delta} materiality_delta={materiality_delta} transport={transport} batches={batches} attempts={attempts} retries={retries} elapsed={elapsed}s reason={reason}".format(
                    run_id=row.get("run_id"),
                    brand_name=row.get("brand_name") or "",
                    status=row.get("llm_status") or row.get("status") or "",
                    model=row.get("llm_model") or "",
                    transport=row.get("llm_transport") or "",
                    accepted=row.get("accepted_count") or 0,
                    heuristic_material=row.get("heuristic_accepted_material") or 0,
                    llm_material=row.get("llm_accepted_material") or 0,
                    class_delta=row.get("semantic_class_disagreement_count") or 0,
                    materiality_delta=row.get("materiality_disagreement_count") or 0,
                    batches=row.get("llm_batch_count") or 0,
                    attempts=row.get("llm_attempt_count") or 0,
                    retries=row.get("llm_retry_count") or 0,
                    elapsed=row.get("elapsed_seconds") or 0,
                    reason=row.get("llm_reason") or "",
                )
            )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_ids", nargs="*", type=int, help="Brand Audit run IDs.")
    parser.add_argument("--db", type=Path, default=Path(BRAND3_DB_PATH), help="SQLite database path.")
    parser.add_argument("--limit", type=int, default=3, help="Use latest completed runs when IDs are omitted.")
    parser.add_argument("--distinct-brands", action="store_true", help="When IDs are omitted, keep only the latest run per brand/url key.")
    parser.add_argument("--no-cache", action="store_true", help="Bypass persistent LLM cache for live timing and stability measurements.")
    parser.add_argument("--json", action="store_true", help="Print JSON payload.")
    parser.add_argument("--output-json", type=Path, help="Write JSON artifact.")
    parser.add_argument("--output-md", type=Path, help="Write Markdown artifact.")
    return parser.parse_args(argv)


def _llm_for_args(args: argparse.Namespace):
    if not args.no_cache:
        return None
    llm = LLMAnalyzer(model=BRAND3_EVIDENCE_LLM_MODEL)
    llm.use_cache = False
    return llm


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


def _latest_distinct_run_ids(store: SQLiteStore, limit: int) -> list[int]:
    rows = store.conn.execute(
        """
        SELECT id
        FROM runs
        WHERE completed_at IS NOT NULL
        ORDER BY id DESC
        LIMIT ?
        """,
        (max(limit * 10, 50),),
    ).fetchall()
    seen: set[str] = set()
    run_ids: list[int] = []
    for row in rows:
        run_id = int(row["id"])
        snapshot = store.get_run_snapshot(run_id)
        key = _brand_key(snapshot) if isinstance(snapshot, dict) else f"run:{run_id}"
        if key in seen:
            continue
        seen.add(key)
        run_ids.append(run_id)
        if len(run_ids) >= limit:
            break
    return run_ids


def _brand_key(snapshot: dict[str, Any]) -> str:
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    url = str(run.get("url") or "").strip().lower()
    brand_name = str(run.get("brand_name") or "").strip().lower()
    if url:
        return url.removeprefix("https://").removeprefix("http://").removeprefix("www.").rstrip("/")
    return brand_name or "unknown"


def _row(*, packet, heuristic: dict[str, Any], llm: dict[str, Any]) -> dict[str, Any]:
    heuristic_by_id = {
        str(item.get("observation_id") or ""): item
        for item in heuristic.get("assessments") or []
        if isinstance(item, dict)
    }
    llm_by_id = {
        str(item.get("observation_id") or ""): item
        for item in llm.get("assessments") or []
        if isinstance(item, dict)
    }
    class_delta = 0
    materiality_delta = 0
    disagreements: list[dict[str, Any]] = []
    for observation_id, item in llm_by_id.items():
        baseline = heuristic_by_id.get(observation_id)
        if not baseline:
            continue
        class_changed = item.get("semantic_class") != baseline.get("semantic_class")
        materiality_changed = item.get("materiality") != baseline.get("materiality")
        if class_changed:
            class_delta += 1
        if materiality_changed:
            materiality_delta += 1
        if class_changed or materiality_changed:
            disagreements.append(
                {
                    "observation_id": observation_id,
                    "heuristic_class": baseline.get("semantic_class") or "",
                    "llm_class": item.get("semantic_class") or "",
                    "heuristic_materiality": baseline.get("materiality") or "",
                    "llm_materiality": item.get("materiality") or "",
                    "llm_reason_codes": list(item.get("reason_codes") or []),
                }
            )
    return {
        "run_id": packet.run_id,
        "brand_name": packet.brand_name,
        "url": packet.url,
        "accepted_count": len(packet.accepted),
        "llm_status": llm.get("status") or "",
        "llm_model": llm.get("model") or "",
        "llm_transport": llm.get("transport") or "",
        "llm_reason": llm.get("reason") or "",
        "llm_detail": llm.get("detail") or "",
        "llm_attempt_count": llm.get("attempt_count") or 0,
        "llm_batch_count": llm.get("batch_count") or 0,
        "llm_retry_count": llm.get("retry_count") or 0,
        "heuristic_accepted_material": (heuristic.get("summary") or {}).get("accepted_material_count") or 0,
        "heuristic_accepted_weak": (heuristic.get("summary") or {}).get("accepted_weak_count") or 0,
        "llm_accepted_material": (llm.get("summary") or {}).get("accepted_material_count") or 0,
        "llm_accepted_weak": (llm.get("summary") or {}).get("accepted_weak_count") or 0,
        "semantic_class_disagreement_count": class_delta,
        "materiality_disagreement_count": materiality_delta,
        "disagreements": disagreements[:10],
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    transports: dict[str, int] = {}
    for row in rows:
        status = str(row.get("llm_status") or row.get("status") or "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        transport = str(row.get("llm_transport") or "")
        if transport:
            transports[transport] = transports.get(transport, 0) + 1
    return {
        "run_count": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "transport_counts": dict(sorted(transports.items())),
        "semantic_class_disagreement_count": sum(int(row.get("semantic_class_disagreement_count") or 0) for row in rows),
        "materiality_disagreement_count": sum(int(row.get("materiality_disagreement_count") or 0) for row in rows),
        "total_batches": sum(int(row.get("llm_batch_count") or 0) for row in rows),
        "total_attempts": sum(int(row.get("llm_attempt_count") or 0) for row in rows),
        "total_retries": sum(int(row.get("llm_retry_count") or 0) for row in rows),
        "total_elapsed_seconds": round(sum(float(row.get("elapsed_seconds") or 0.0) for row in rows), 2),
    }


def _elapsed(started: float) -> float:
    return round(time.monotonic() - started, 2)


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Evidence LLM Shadow",
        "",
        f"- Runtime effect: `{str(bool(payload.get('runtime_effect'))).lower()}`",
        f"- Prompt effect: `{str(bool(payload.get('prompt_effect'))).lower()}`",
        f"- Persistence effect: `{str(bool(payload.get('persistence_effect'))).lower()}`",
        "",
        "## Summary",
        "",
    ]
    summary = payload.get("summary") or {}
    for key, value in summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Rows", "", "| Run | Brand | LLM status | Model | Transport | Accepted | Heuristic material | LLM material | Class delta | Materiality delta | Batches | Attempts | Retries | Seconds | Reason |", "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"])
    for row in payload.get("rows") or []:
        lines.append(
            "| {run_id} | {brand_name} | {status} | {model} | {transport} | {accepted} | {hm} | {lm} | {cd} | {md} | {batches} | {attempts} | {retries} | {seconds} | {reason} |".format(
                run_id=row.get("run_id") or "",
                brand_name=row.get("brand_name") or "",
                status=row.get("llm_status") or row.get("status") or "",
                model=row.get("llm_model") or "",
                transport=row.get("llm_transport") or "",
                accepted=row.get("accepted_count") or 0,
                hm=row.get("heuristic_accepted_material") or 0,
                lm=row.get("llm_accepted_material") or 0,
                cd=row.get("semantic_class_disagreement_count") or 0,
                md=row.get("materiality_disagreement_count") or 0,
                batches=row.get("llm_batch_count") or 0,
                attempts=row.get("llm_attempt_count") or 0,
                retries=row.get("llm_retry_count") or 0,
                seconds=row.get("elapsed_seconds") or 0,
                reason=row.get("llm_reason") or "",
            )
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
