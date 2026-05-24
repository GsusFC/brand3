#!/usr/bin/env python3
"""Real validation batch v1 for Evidence Packet prompt-input dry-path.

Lab-only script:
- reads existing run snapshots from SQLite
- builds local evidence packets + prompt-input candidates
- runs bounded findings generation for selected case/dimension pairs
- writes comparison and pass/fail gate artifacts
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import BRAND3_DB_PATH, LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.reports.evidence_packet_candidate_integration import (
    LAB_SYSTEM_PROMPT,
    build_lab_request,
    summarize_lab_response,
)
from src.reports.evidence_packet import build_evidence_packet_v0
from src.reports.evidence_packet_prompt_input import build_prompt_input_candidate_v0
from src.storage.sqlite_store import SQLiteStore


OUT_DIR = Path("examples/reports/evidence_packet_real_validation_batch_v1")
PACKET_DIR = Path("examples/reports/evidence_packet")
CANDIDATE_DIR = Path("examples/reports/evidence_packet_prompt_input")

SNAPSHOT_CASES = [
    {"case_id": "linear", "brand_name": "Linear", "run_id": 80},
    {"case_id": "vercel", "brand_name": "Vercel", "run_id": 79},
    {"case_id": "launchdarkly", "brand_name": "LaunchDarkly", "run_id": 76},
    {"case_id": "watermelon", "brand_name": "Watermelon", "run_id": 78},
    {"case_id": "builtwith_kit_com", "brand_name": "builtwith.kit.com", "run_id": 74},
    {"case_id": "notion", "brand_name": "Notion", "run_id": 82},
    {"case_id": "stripe", "brand_name": "Stripe", "run_id": 83},
    {"case_id": "figma", "brand_name": "Figma", "run_id": 84},
    {"case_id": "datadog", "brand_name": "Datadog", "run_id": 85},
]

TARGETS = [
    {"case_id": "linear", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "vercel", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "launchdarkly", "dimension": "vitalidad", "intent": "ready"},
    {"case_id": "watermelon", "dimension": "percepcion", "intent": "thin"},
    {"case_id": "notion", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "stripe", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "figma", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "datadog", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "builtwith_kit_com", "dimension": "coherencia", "intent": "blocked_control"},
    {"case_id": "builtwith_kit_com", "dimension": "percepcion", "intent": "blocked_control"},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Run real LLM calls")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)

    snapshot_manifest = _materialize_packets_from_snapshots()
    manifest = _build_request_manifest(snapshot_manifest)
    _write_json("request_manifest.json", manifest)

    raw_outputs: dict[str, Any] = {
        "created_at": _now(),
        "executed": bool(args.execute),
        "model": LLM_PREMIUM_MODEL,
        "results": [],
        "skipped": manifest["skipped"],
    }
    cost_observation: dict[str, Any] = {
        "created_at": _now(),
        "execute_requested": bool(args.execute),
        "executed": False,
        "llm_calls_planned": len(manifest["requests"]),
        "llm_calls_executed": 0,
        "model": LLM_PREMIUM_MODEL,
        "usage_metadata_available": False,
        "cost_estimate_available": False,
        "json_repair_retries_attempted": 0,
        "json_repair_retries_succeeded": 0,
        "parse_failures_unrecovered": 0,
        "notes": [
            "Real validation batch v1.",
            "Provider token usage is not exposed by current LLMAnalyzer interface.",
        ],
    }

    if args.execute and manifest["requests"]:
        analyzer = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
        for request in manifest["requests"]:
            result = _call(analyzer, request)
            raw_outputs["results"].append(result)
            if result["json_repair_retry_attempted"]:
                cost_observation["json_repair_retries_attempted"] += 1
            if result["json_repair_retry_succeeded"]:
                cost_observation["json_repair_retries_succeeded"] += 1
            if result["parse_failure_unrecovered"]:
                cost_observation["parse_failures_unrecovered"] += 1
        raw_outputs["executed"] = True
        cost_observation.update(
            {
                "executed": True,
                "llm_calls_executed": len(raw_outputs["results"]),
                "cache_hits": analyzer.cache_hits,
                "cache_misses": analyzer.cache_misses,
                "cache_writes": analyzer.cache_writes,
                "call_failures": analyzer.call_failures,
            }
        )
    else:
        for request in manifest["requests"]:
            raw_outputs["results"].append(
                {
                    "case_id": request["case_id"],
                    "dimension": request["dimension"],
                    "intent": request["intent"],
                    "readiness_status": request["readiness_status"],
                    "included_evidence_count": request["included_evidence_count"],
                    "allowed_evidence_urls": request["allowed_evidence_urls"],
                    "executed": False,
                    "raw_response": None,
                    "summary": _summary(None, request["allowed_evidence_urls"], request["dimension"]),
                    "json_repair_retry_attempted": False,
                    "json_repair_retry_succeeded": False,
                    "parse_failure_unrecovered": False,
                }
            )

    comparison = _comparison(manifest, raw_outputs)
    _write_json("raw_outputs.json", raw_outputs)
    _write_json("comparison.json", comparison)
    _write_json("cost_observation.json", cost_observation)
    _write_notes(snapshot_manifest, manifest, comparison, bool(args.execute))


def _materialize_packets_from_snapshots() -> dict[str, Any]:
    store = SQLiteStore(BRAND3_DB_PATH)
    cases: list[dict[str, Any]] = []
    try:
        for item in SNAPSHOT_CASES:
            case_id = item["case_id"]
            run_id = int(item["run_id"])
            snapshot = store.get_run_snapshot(run_id)
            if not snapshot:
                cases.append(
                    {
                        "case_id": case_id,
                        "run_id": run_id,
                        "status": "missing_snapshot",
                    }
                )
                continue
            packet = build_evidence_packet_v0(snapshot)
            packet_path = PACKET_DIR / f"{case_id}.local_evidence_packet.v0.json"
            packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            candidate = build_prompt_input_candidate_v0(packet)
            candidate_path = CANDIDATE_DIR / f"{case_id}.prompt_input_candidate.v0.json"
            candidate_path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            cases.append(
                {
                    "case_id": case_id,
                    "run_id": run_id,
                    "brand_name": item["brand_name"],
                    "status": "ok",
                    "packet_path": str(packet_path),
                    "candidate_path": str(candidate_path),
                    "readiness": {
                        dim: (candidate.get("dimensions", {}).get(dim, {}).get("readiness_status"))
                        for dim in ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")
                    },
                }
            )
    finally:
        store.close()
    payload = {
        "created_at": _now(),
        "db_path": BRAND3_DB_PATH,
        "cases": cases,
    }
    _write_json("snapshot_manifest.json", payload)
    return payload


def _build_request_manifest(snapshot_manifest: dict[str, Any]) -> dict[str, Any]:
    existing_cases = {str(case["case_id"]) for case in snapshot_manifest.get("cases", []) if case.get("status") == "ok"}
    requests: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for target in TARGETS:
        case_id = target["case_id"]
        dimension = target["dimension"]
        pair = (case_id, dimension)
        if pair in seen:
            continue
        seen.add(pair)

        if case_id not in existing_cases:
            skipped.append(
                {
                    "case_id": case_id,
                    "dimension": dimension,
                    "intent": target["intent"],
                    "reason": "case_missing_after_snapshot_materialization",
                }
            )
            continue

        candidate_path = CANDIDATE_DIR / f"{case_id}.prompt_input_candidate.v0.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        dim = candidate["dimensions"][dimension]
        request, skip = build_lab_request(
            case_id=case_id,
            dimension=dimension,
            intent=target["intent"],
            model=LLM_PREMIUM_MODEL,
            task_label=f"Generate bounded findings for {case_id}/{dimension} in real validation batch v1.",
            readiness_status=str(dim["readiness_status"]),
            prompt_constraints=list(dim.get("prompt_constraints") or []),
            evidence=list(dim.get("evidence") or []),
            max_tokens=1800,
        )
        if skip:
            skipped.append(skip)
            continue
        if request:
            request["system"] = LAB_SYSTEM_PROMPT
            requests.append(request)

    return {"created_at": _now(), "requests": requests, "skipped": skipped}


def _call(analyzer: LLMAnalyzer, request: dict[str, Any]) -> dict[str, Any]:
    data = analyzer._call_json(
        system=request["system"],
        user=request["user"],
        max_tokens=int(request["max_tokens"]),
    )
    retry_attempted = False
    retry_succeeded = False
    unrecovered = False

    if not _has_findings(data) and _is_json_parse_failure(analyzer):
        retry_attempted = True
        data_retry = analyzer._call_json(
            system=request["system"],
            user=_repair_user_prompt(request["user"]),
            max_tokens=int(request["max_tokens"]),
        )
        if _has_findings(data_retry):
            data = data_retry
            retry_succeeded = True
        else:
            unrecovered = True

    return {
        "created_at": _now(),
        "case_id": request["case_id"],
        "dimension": request["dimension"],
        "intent": request["intent"],
        "readiness_status": request["readiness_status"],
        "included_evidence_count": request["included_evidence_count"],
        "allowed_evidence_urls": request["allowed_evidence_urls"],
        "raw_response": data,
        "summary": _summary(data, request["allowed_evidence_urls"], request["dimension"]),
        "json_repair_retry_attempted": retry_attempted,
        "json_repair_retry_succeeded": retry_succeeded,
        "parse_failure_unrecovered": unrecovered,
    }


def _summary(data: Any, allowed_urls: list[str], dimension: str) -> dict[str, Any]:
    summary = summarize_lab_response(data, allowed_urls, dimension)
    return {
        "finding_count": summary["finding_count"],
        "has_typical_decision": summary["has_typical_decision"],
        "limits_present": summary["limits_field_present"],
        "risky_terms_outside_limits": summary["risky_terms_outside_limits"],
        "evidence_urls_valid": summary["evidence_url_validity"],
        "invalid_evidence_urls": sorted(set(summary["evidence_urls_used"]) - set(allowed_urls)),
    }


def _comparison(manifest: dict[str, Any], raw_outputs: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    results = raw_outputs.get("results") or []
    for item in results:
        summary = item.get("summary") or {}
        rows.append(
            {
                "case_id": item.get("case_id"),
                "dimension": item.get("dimension"),
                "intent": item.get("intent"),
                "readiness_status": item.get("readiness_status"),
                "included_evidence_count": item.get("included_evidence_count", 0),
                "finding_count": summary.get("finding_count", 0),
                "no_typical_decision": not bool(summary.get("has_typical_decision")),
                "limits_present": bool(summary.get("limits_present")),
                "risky_terms_outside_limits_empty": len(summary.get("risky_terms_outside_limits") or []) == 0,
                "evidence_urls_valid": bool(summary.get("evidence_urls_valid")),
                "parse_failure_unrecovered": bool(item.get("parse_failure_unrecovered")),
                "json_repair_retry_attempted": bool(item.get("json_repair_retry_attempted")),
                "json_repair_retry_succeeded": bool(item.get("json_repair_retry_succeeded")),
            }
        )

    pass_criteria = {
        "no_typical_decision": all(row["no_typical_decision"] for row in rows) if rows else False,
        "limits_present": all(row["limits_present"] for row in rows) if rows else False,
        "risky_terms_outside_limits_empty": all(row["risky_terms_outside_limits_empty"] for row in rows) if rows else False,
        "evidence_urls_valid": all(row["evidence_urls_valid"] for row in rows) if rows else False,
        "parse_failures_unrecovered": 0,
        "blocked_controls_skipped": True,
    }
    parse_failures = sum(1 for row in rows if row["parse_failure_unrecovered"])
    pass_criteria["parse_failures_unrecovered"] = parse_failures
    blocked_controls = [
        target for target in TARGETS if target["intent"] == "blocked_control"
    ]
    skipped_set = {
        (entry.get("case_id"), entry.get("dimension"))
        for entry in manifest.get("skipped") or []
    }
    pass_criteria["blocked_controls_skipped"] = all(
        (target["case_id"], target["dimension"]) in skipped_set for target in blocked_controls
    )
    overall_pass = (
        pass_criteria["no_typical_decision"]
        and pass_criteria["limits_present"]
        and pass_criteria["risky_terms_outside_limits_empty"]
        and pass_criteria["evidence_urls_valid"]
        and pass_criteria["parse_failures_unrecovered"] == 0
        and pass_criteria["blocked_controls_skipped"]
    )
    return {
        "created_at": _now(),
        "cases_executed": len(rows),
        "cases_skipped": len(manifest.get("skipped") or []),
        "rows": rows,
        "pass_criteria": pass_criteria,
        "overall_pass": overall_pass,
    }


def _repair_user_prompt(user_payload: str) -> str:
    return (
        user_payload
        + "\n\nReturn valid JSON exactly matching the schema. "
        + "No markdown fences, no comments, no trailing commas."
    )


def _is_json_parse_failure(analyzer: LLMAnalyzer) -> bool:
    if not analyzer.call_failures:
        return False
    last = str(analyzer.call_failures[-1]).lower()
    return "json" in last or "parse" in last


def _has_findings(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    findings = data.get("findings")
    return isinstance(findings, list) and len(findings) > 0


def _write_notes(
    snapshot_manifest: dict[str, Any],
    request_manifest: dict[str, Any],
    comparison: dict[str, Any],
    executed: bool,
) -> None:
    lines: list[str] = []
    lines.append("# Evidence Packet Real Validation Batch v1")
    lines.append("")
    lines.append(f"- Created: {_now()}")
    lines.append(f"- Executed LLM calls: {executed}")
    lines.append(f"- Snapshot cases materialized: {len(snapshot_manifest.get('cases') or [])}")
    lines.append(f"- Requests prepared: {len(request_manifest.get('requests') or [])}")
    lines.append(f"- Requests skipped: {len(request_manifest.get('skipped') or [])}")
    lines.append(f"- Overall pass: {comparison.get('overall_pass')}")
    lines.append("")
    lines.append("## Executed rows")
    for row in comparison.get("rows") or []:
        lines.append(
            f"- {row['case_id']}::{row['dimension']} "
            f"(status={row['readiness_status']}, findings={row['finding_count']}, "
            f"limits={row['limits_present']}, risky_outside_limits_empty={row['risky_terms_outside_limits_empty']})"
        )
    if request_manifest.get("skipped"):
        lines.append("")
        lines.append("## Skipped")
        for item in request_manifest["skipped"]:
            lines.append(
                f"- {item.get('case_id')}::{item.get('dimension')} "
                f"reason={item.get('reason')} status={item.get('status')}"
            )
    (OUT_DIR / "trial_notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(name: str, payload: dict[str, Any]) -> None:
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
