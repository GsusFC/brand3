#!/usr/bin/env python3
"""Real validation batch v2.1 with 9-case segmented matrix.

Lab-only script:
- resolves cases by canonical URL against existing local snapshots
- materializes local evidence packets + prompt-input candidates
- runs bounded findings generation for selected dimensions
- writes segmented metrics and pass/fail artifacts
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.config import BRAND3_DB_PATH, LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.reports.evidence_packet import build_evidence_packet_v0
from src.reports.evidence_packet_candidate_integration import (
    LAB_SYSTEM_PROMPT,
    build_lab_request,
    summarize_lab_response,
)
from src.reports.evidence_packet_prompt_input import build_prompt_input_candidate_v0
from src.storage.sqlite_store import SQLiteStore


OUT_DIR = Path("examples/reports/evidence_packet_real_validation_batch_v2_1")
PACKET_DIR = Path("examples/reports/evidence_packet")
CANDIDATE_DIR = Path("examples/reports/evidence_packet_prompt_input")
REVIEW_MD = Path("docs/brand3_evidence_packet_real_validation_batch_v2_1_review.md")
REVIEW_JSON = Path("docs/brand3_evidence_packet_real_validation_batch_v2_1_review.json")

GROUP_PREFERENCE = {
    "group_a": ["diferenciacion"],
    "group_b": ["percepcion", "coherencia"],
    "group_c": ["diferenciacion"],
}
EXECUTABLE_STATUSES = {"ready", "thin"}
TARGET_GROUP_SIZE = 3


CASE_MATRIX = {
    "group_a": {
        "name": "Deeptech / scientific systems",
        "primary": [
            {"case_id": "lightmatter", "brand_name": "Lightmatter", "canonical_url": "https://lightmatter.co"},
            {"case_id": "celestial_ai", "brand_name": "Celestial AI", "canonical_url": "https://www.celestial.ai"},
            {"case_id": "synthesia", "brand_name": "Synthesia", "canonical_url": "https://www.synthesia.io"},
        ],
        "backups": [
            {"case_id": "sentry", "brand_name": "Sentry", "canonical_url": "https://sentry.io"},
            {"case_id": "temporal", "brand_name": "Temporal", "canonical_url": "https://temporal.io"},
            {"case_id": "supabase", "brand_name": "Supabase", "canonical_url": "https://supabase.com"},
            {"case_id": "linear", "brand_name": "Linear", "canonical_url": "https://linear.app"},
            {"case_id": "vercel", "brand_name": "Vercel", "canonical_url": "https://vercel.com"},
        ],
    },
    "group_b": {
        "name": "Product / system identity",
        "primary": [
            {"case_id": "raycast", "brand_name": "Raycast", "canonical_url": "https://www.raycast.com"},
            {"case_id": "retool", "brand_name": "Retool", "canonical_url": "https://retool.com"},
            {"case_id": "cron", "brand_name": "Cron", "canonical_url": "https://cron.com"},
        ],
        "backups": [
            {"case_id": "launchdarkly", "brand_name": "LaunchDarkly", "canonical_url": "https://launchdarkly.com"},
            {"case_id": "watermelon", "brand_name": "Watermelon", "canonical_url": "https://watermelon.sh"},
            {"case_id": "iris", "brand_name": "Iris", "canonical_url": "https://irisdesign.dev"},
        ],
    },
    "group_c": {
        "name": "Expressive / visual language",
        "primary": [
            {"case_id": "locomotive", "brand_name": "Locomotive", "canonical_url": "https://locomotive.ca"},
            {"case_id": "bakken_baeck", "brand_name": "Bakken & Baeck", "canonical_url": "https://bakkenbaeck.com"},
            {"case_id": "dogstudio", "brand_name": "Dogstudio", "canonical_url": "https://dogstudio.co"},
        ],
        "backups": [
            {"case_id": "spooky", "brand_name": "Spooky", "canonical_url": "https://spooky.design"},
            {"case_id": "stipple", "brand_name": "Stipple", "canonical_url": "https://www.stipple.sh"},
            {"case_id": "vexture", "brand_name": "Vexture", "canonical_url": "https://www.miva.com/vexture-search"},
        ],
    },
}

BLOCKED_CONTROLS = [
    {"case_id": "builtwith_kit_com", "dimension": "coherencia"},
    {"case_id": "builtwith_kit_com", "dimension": "percepcion"},
]


@dataclass
class ResolvedCase:
    group_id: str
    case_id: str
    brand_name: str
    canonical_url: str
    source_type: str  # primary|backup
    run_id: int
    run_url: str


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Run real LLM calls")
    parser.add_argument(
        "--bootstrap-missing",
        action="store_true",
        help="Run missing canonical URLs through brand analysis before snapshot resolution.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)

    if args.bootstrap_missing:
        _bootstrap_missing_cases()

    run_index = _load_run_index(BRAND3_DB_PATH)
    case_matrix_payload, resolved_cases, unresolved_cases = _resolve_case_matrix(run_index)
    _write_json("case_matrix.json", case_matrix_payload)

    snapshot_manifest = _materialize_packets_from_snapshots(resolved_cases)
    request_manifest = _build_request_manifest(snapshot_manifest)
    _write_json("request_manifest.json", request_manifest)

    raw_outputs, cost_observation = _execute_or_prepare(request_manifest, args.execute)
    comparison = _build_comparison(case_matrix_payload, snapshot_manifest, request_manifest, raw_outputs)

    _write_json("snapshot_manifest.json", snapshot_manifest)
    _write_json("raw_outputs.json", raw_outputs)
    _write_json("comparison.json", comparison)
    _write_json("cost_observation.json", cost_observation)
    _write_notes(case_matrix_payload, snapshot_manifest, request_manifest, comparison, bool(args.execute))
    _write_review(case_matrix_payload, snapshot_manifest, request_manifest, comparison, cost_observation)


def _load_run_index(db_path: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT id, brand_name, url, started_at
            FROM runs
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        conn.close()
    for run_id, brand_name, url, started_at in rows:
        host = _normalized_host(url)
        if not host:
            continue
        if host in index:
            continue
        index[host] = {
            "run_id": int(run_id),
            "brand_name": str(brand_name or ""),
            "url": str(url or ""),
            "started_at": str(started_at or ""),
        }
    return index


def _bootstrap_missing_cases() -> None:
    from src.services import brand_service

    run_index = _load_run_index(BRAND3_DB_PATH)
    seen_hosts: set[str] = set()
    for group_cfg in CASE_MATRIX.values():
        for item in list(group_cfg.get("primary") or []) + list(group_cfg.get("backups") or []):
            canonical_url = item.get("canonical_url")
            host = _normalized_host(canonical_url)
            if not host or host in seen_hosts:
                continue
            seen_hosts.add(host)
            if host in run_index:
                continue
            brand_name = str(item.get("brand_name") or host)
            try:
                print(f"[bootstrap] analyzing {brand_name} ({canonical_url})")
                brand_service.run(
                    canonical_url,
                    brand_name=brand_name,
                    use_llm=True,
                    use_social=True,
                    use_competitors=True,
                    refresh=True,
                )
            except Exception as exc:  # pragma: no cover - operational path
                print(f"[bootstrap] failed {brand_name} ({canonical_url}): {exc}")


def _resolve_case_matrix(run_index: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[ResolvedCase], list[dict[str, Any]]]:
    payload_groups: dict[str, Any] = {}
    resolved: list[ResolvedCase] = []
    unresolved: list[dict[str, Any]] = []

    for group_id, group_cfg in CASE_MATRIX.items():
        primary = list(group_cfg["primary"])
        backups = list(group_cfg.get("backups") or [])
        decisions: list[dict[str, Any]] = []
        selected: list[dict[str, Any]] = []

        for item in primary:
            decision = _resolve_candidate(item, run_index, source_type="primary")
            decisions.append(decision)
            if decision["status"] == "selected":
                selected.append(decision)
                resolved.append(
                    ResolvedCase(
                        group_id=group_id,
                        case_id=decision["case_id"],
                        brand_name=decision["brand_name"],
                        canonical_url=decision["canonical_url"],
                        source_type="primary",
                        run_id=int(decision["run_id"]),
                        run_url=decision["run_url"],
                    )
                )
            else:
                unresolved.append(decision)

        # Replacement from backups to reach target group size.
        needed = max(0, TARGET_GROUP_SIZE - len(selected))
        if needed:
            for item in backups:
                decision = _resolve_candidate(item, run_index, source_type="backup")
                decisions.append(decision)
                if decision["status"] == "selected":
                    selected.append(decision)
                    resolved.append(
                        ResolvedCase(
                            group_id=group_id,
                            case_id=decision["case_id"],
                            brand_name=decision["brand_name"],
                            canonical_url=decision["canonical_url"],
                            source_type="backup",
                            run_id=int(decision["run_id"]),
                            run_url=decision["run_url"],
                        )
                    )
                    needed -= 1
                    if needed == 0:
                        break
                else:
                    unresolved.append(decision)

        payload_groups[group_id] = {
            "name": group_cfg["name"],
            "primary_count": len(primary),
            "selected_count": len(selected),
            "target_count": TARGET_GROUP_SIZE,
            "selected_primary_count": sum(1 for s in selected if s["source_type"] == "primary"),
            "selected_backup_count": sum(1 for s in selected if s["source_type"] == "backup"),
            "decisions": decisions,
            "selected": selected,
            "coverage_gap": max(0, TARGET_GROUP_SIZE - len(selected)),
        }

    payload = {
        "created_at": _now(),
        "db_path": BRAND3_DB_PATH,
        "groups": payload_groups,
        "resolved_total": len(resolved),
        "unresolved_total": len(unresolved),
    }
    return payload, resolved, unresolved


def _resolve_candidate(item: dict[str, Any], run_index: dict[str, dict[str, Any]], source_type: str) -> dict[str, Any]:
    canonical_url = item.get("canonical_url")
    base = {
        "case_id": str(item.get("case_id") or ""),
        "brand_name": str(item.get("brand_name") or ""),
        "canonical_url": canonical_url,
        "source_type": source_type,
    }
    host = _normalized_host(canonical_url)
    if not canonical_url or not host:
        return {
            **base,
            "status": "unresolved",
            "reason": "canonical_url_unresolved",
        }
    record = run_index.get(host)
    if not record:
        return {
            **base,
            "status": "unresolved",
            "reason": "no_local_snapshot_for_canonical_host",
            "canonical_host": host,
        }
    return {
        **base,
        "status": "selected",
        "canonical_host": host,
        "run_id": int(record["run_id"]),
        "run_url": str(record["url"]),
        "run_brand_name": str(record["brand_name"]),
    }


def _materialize_packets_from_snapshots(resolved_cases: list[ResolvedCase]) -> dict[str, Any]:
    store = SQLiteStore(BRAND3_DB_PATH)
    items: list[dict[str, Any]] = []
    try:
        for case in resolved_cases:
            snapshot = store.get_run_snapshot(case.run_id)
            if not snapshot:
                items.append(
                    {
                        "group_id": case.group_id,
                        "case_id": case.case_id,
                        "run_id": case.run_id,
                        "status": "missing_snapshot_payload",
                    }
                )
                continue
            packet = build_evidence_packet_v0(snapshot)
            packet_path = PACKET_DIR / f"{case.case_id}.local_evidence_packet.v0.json"
            packet_path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            candidate = build_prompt_input_candidate_v0(packet)
            candidate_path = CANDIDATE_DIR / f"{case.case_id}.prompt_input_candidate.v0.json"
            candidate_path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

            items.append(
                {
                    "group_id": case.group_id,
                    "case_id": case.case_id,
                    "source_type": case.source_type,
                    "brand_name": case.brand_name,
                    "canonical_url": case.canonical_url,
                    "run_id": case.run_id,
                    "run_url": case.run_url,
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
    return {
        "created_at": _now(),
        "db_path": BRAND3_DB_PATH,
        "cases": items,
    }


def _build_request_manifest(snapshot_manifest: dict[str, Any]) -> dict[str, Any]:
    requests: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for case in snapshot_manifest.get("cases") or []:
        if case.get("status") != "ok":
            skipped.append(
                {
                    "group_id": case.get("group_id"),
                    "case_id": case.get("case_id"),
                    "reason": "snapshot_not_materialized",
                }
            )
            continue
        case_id = str(case["case_id"])
        group_id = str(case["group_id"])
        candidate = json.loads(Path(str(case["candidate_path"])).read_text(encoding="utf-8"))
        dimension = _pick_dimension(group_id, candidate)
        dim_payload = candidate["dimensions"][dimension]
        request, skip = build_lab_request(
            case_id=case_id,
            dimension=dimension,
            intent="segmented_matrix_case",
            model=LLM_PREMIUM_MODEL,
            task_label=f"Generate bounded findings for {case_id}/{dimension} in real validation batch v2.1.",
            readiness_status=str(dim_payload["readiness_status"]),
            prompt_constraints=list(dim_payload.get("prompt_constraints") or []),
            evidence=list(dim_payload.get("evidence") or []),
            max_tokens=1800,
        )
        if skip:
            skipped.append(
                {
                    "group_id": group_id,
                    **skip,
                }
            )
            continue
        assert request is not None
        request["group_id"] = group_id
        request["source_type"] = case["source_type"]
        request["run_id"] = case["run_id"]
        request["system"] = LAB_SYSTEM_PROMPT
        requests.append(request)

    # Add blocked controls for gating validation (if candidate exists locally).
    for control in BLOCKED_CONTROLS:
        case_id = control["case_id"]
        dimension = control["dimension"]
        candidate_path = CANDIDATE_DIR / f"{case_id}.prompt_input_candidate.v0.json"
        if not candidate_path.exists():
            skipped.append(
                {
                    "group_id": "controls",
                    "case_id": case_id,
                    "dimension": dimension,
                    "reason": "control_candidate_missing",
                }
            )
            continue
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        dim_payload = candidate["dimensions"][dimension]
        request, skip = build_lab_request(
            case_id=case_id,
            dimension=dimension,
            intent="blocked_control",
            model=LLM_PREMIUM_MODEL,
            task_label=f"Control check for {case_id}/{dimension} in batch v2.1.",
            readiness_status=str(dim_payload["readiness_status"]),
            prompt_constraints=list(dim_payload.get("prompt_constraints") or []),
            evidence=list(dim_payload.get("evidence") or []),
            max_tokens=1800,
        )
        if skip:
            skipped.append({"group_id": "controls", **skip})
            continue
        # We should not execute blocked controls; if request returned, record as policy issue and skip.
        skipped.append(
            {
                "group_id": "controls",
                "case_id": case_id,
                "dimension": dimension,
                "reason": "control_not_blocked_unexpected",
                "status": dim_payload["readiness_status"],
            }
        )

    return {"created_at": _now(), "requests": requests, "skipped": skipped}


def _pick_dimension(group_id: str, candidate: dict[str, Any]) -> str:
    dims = candidate.get("dimensions") or {}
    preferred = GROUP_PREFERENCE.get(group_id) or ["diferenciacion"]
    for dim in preferred:
        status = str((dims.get(dim) or {}).get("readiness_status") or "")
        if status in EXECUTABLE_STATUSES:
            return dim
    # fallback: first preferred even if skipped later
    return preferred[0]


def _execute_or_prepare(request_manifest: dict[str, Any], execute: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_outputs: dict[str, Any] = {
        "created_at": _now(),
        "executed": bool(execute),
        "model": LLM_PREMIUM_MODEL,
        "results": [],
        "skipped": request_manifest["skipped"],
    }
    cost_observation: dict[str, Any] = {
        "created_at": _now(),
        "execute_requested": bool(execute),
        "executed": False,
        "llm_calls_planned": len(request_manifest["requests"]),
        "llm_calls_executed": 0,
        "model": LLM_PREMIUM_MODEL,
        "usage_metadata_available": False,
        "cost_estimate_available": False,
        "json_repair_retries_attempted": 0,
        "json_repair_retries_succeeded": 0,
        "parse_failures_unrecovered": 0,
        "notes": [
            "Real validation batch v2.1.",
            "Provider token usage is not exposed by current LLMAnalyzer interface.",
        ],
    }

    if execute and request_manifest["requests"]:
        analyzer = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
        for request in request_manifest["requests"]:
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
        for request in request_manifest["requests"]:
            raw_outputs["results"].append(
                {
                    "created_at": _now(),
                    "group_id": request["group_id"],
                    "case_id": request["case_id"],
                    "dimension": request["dimension"],
                    "intent": request["intent"],
                    "readiness_status": request["readiness_status"],
                    "included_evidence_count": request["included_evidence_count"],
                    "allowed_evidence_urls": request["allowed_evidence_urls"],
                    "raw_response": None,
                    "summary": _summary(None, request["allowed_evidence_urls"], request["dimension"]),
                    "json_repair_retry_attempted": False,
                    "json_repair_retry_succeeded": False,
                    "parse_failure_unrecovered": False,
                }
            )
    return raw_outputs, cost_observation


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
        "group_id": request["group_id"],
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


def _build_comparison(
    case_matrix_payload: dict[str, Any],
    snapshot_manifest: dict[str, Any],
    request_manifest: dict[str, Any],
    raw_outputs: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in raw_outputs.get("results") or []:
        summary = item.get("summary") or {}
        rows.append(
            {
                "group_id": item.get("group_id"),
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
            }
        )

    group_metrics: dict[str, Any] = {}
    for group_id, group_data in (case_matrix_payload.get("groups") or {}).items():
        group_rows = [row for row in rows if row.get("group_id") == group_id]
        readiness = {
            "ready": 0,
            "thin": 0,
            "blocked": 0,
            "abstain": 0,
            "review_required": 0,
            "other": 0,
        }
        for case in snapshot_manifest.get("cases") or []:
            if case.get("group_id") != group_id or case.get("status") != "ok":
                continue
            # status for selected dimension
            dim = _pick_dimension(group_id, json.loads(Path(str(case["candidate_path"])).read_text(encoding="utf-8")))
            status = str(case.get("readiness", {}).get(dim) or "")
            if status in readiness:
                readiness[status] += 1
            else:
                readiness["other"] += 1

        group_metrics[group_id] = {
            "name": group_data.get("name"),
            "target_count": int(group_data.get("target_count") or 0),
            "selected_count": int(group_data.get("selected_count") or 0),
            "coverage_gap": int(group_data.get("coverage_gap") or 0),
            "executed_count": len(group_rows),
            "primary_selected_count": int(group_data.get("selected_primary_count") or 0),
            "backup_selected_count": int(group_data.get("selected_backup_count") or 0),
            "readiness_distribution": readiness,
            "all_rows_pass": all(
                row["no_typical_decision"]
                and row["limits_present"]
                and row["risky_terms_outside_limits_empty"]
                and row["evidence_urls_valid"]
                and not row["parse_failure_unrecovered"]
                for row in group_rows
            )
            if group_rows
            else False,
        }

    parse_failures = sum(1 for row in rows if row["parse_failure_unrecovered"])
    skipped_controls_set = {
        (item.get("case_id"), item.get("dimension"))
        for item in request_manifest.get("skipped") or []
    }
    blocked_controls_skipped = all(
        (control["case_id"], control["dimension"]) in skipped_controls_set
        for control in BLOCKED_CONTROLS
    )

    pass_criteria = {
        "no_typical_decision": all(row["no_typical_decision"] for row in rows) if rows else False,
        "limits_present": all(row["limits_present"] for row in rows) if rows else False,
        "risky_terms_outside_limits_empty": all(row["risky_terms_outside_limits_empty"] for row in rows) if rows else False,
        "evidence_urls_valid": all(row["evidence_urls_valid"] for row in rows) if rows else False,
        "parse_failures_unrecovered": parse_failures,
        "blocked_controls_skipped": blocked_controls_skipped,
    }

    # Group-level regime criteria for v2.1 matrix.
    group_a = group_metrics.get("group_a", {})
    group_b = group_metrics.get("group_b", {})
    group_c = group_metrics.get("group_c", {})
    group_level_flags = {
        "group_a_majority_ready_low_review_pressure": (
            (group_a.get("readiness_distribution", {}).get("ready", 0) > (group_a.get("selected_count", 0) / 2))
            and (group_a.get("readiness_distribution", {}).get("review_required", 0) <= 1)
        ),
        "group_b_product_system_mixed_ready_thin": (
            group_b.get("readiness_distribution", {}).get("ready", 0)
            + group_b.get("readiness_distribution", {}).get("thin", 0)
            >= max(1, group_b.get("selected_count", 0) - 1)
        ),
        "group_c_expressive_stays_bounded": (
            group_c.get("executed_count", 0) >= 1
            and bool(group_c.get("all_rows_pass", False))
        ),
    }

    overall_pass = (
        pass_criteria["no_typical_decision"]
        and pass_criteria["limits_present"]
        and pass_criteria["risky_terms_outside_limits_empty"]
        and pass_criteria["evidence_urls_valid"]
        and pass_criteria["parse_failures_unrecovered"] == 0
        and pass_criteria["blocked_controls_skipped"]
        and all(group_level_flags.values())
    )

    return {
        "created_at": _now(),
        "executed": bool(raw_outputs.get("executed")),
        "cases_executed": len(rows),
        "cases_skipped": len(request_manifest.get("skipped") or []),
        "rows": rows,
        "group_metrics": group_metrics,
        "pass_criteria": pass_criteria,
        "group_level_flags": group_level_flags,
        "overall_pass": overall_pass,
    }


def _write_notes(
    case_matrix_payload: dict[str, Any],
    snapshot_manifest: dict[str, Any],
    request_manifest: dict[str, Any],
    comparison: dict[str, Any],
    executed: bool,
) -> None:
    lines: list[str] = []
    lines.append("# Evidence Packet Real Validation Batch v2.1")
    lines.append("")
    lines.append(f"- Created: {_now()}")
    lines.append(f"- Executed LLM calls: {executed}")
    lines.append(f"- Resolved cases: {case_matrix_payload.get('resolved_total')}")
    lines.append(f"- Unresolved cases: {case_matrix_payload.get('unresolved_total')}")
    lines.append(f"- Snapshot cases materialized: {len(snapshot_manifest.get('cases') or [])}")
    lines.append(f"- Requests prepared: {len(request_manifest.get('requests') or [])}")
    lines.append(f"- Requests skipped: {len(request_manifest.get('skipped') or [])}")
    lines.append(f"- Overall pass: {comparison.get('overall_pass')}")
    lines.append("")
    lines.append("## Group metrics")
    for group_id, metrics in (comparison.get("group_metrics") or {}).items():
        lines.append(
            f"- {group_id}: selected={metrics.get('selected_count')}, executed={metrics.get('executed_count')}, "
            f"coverage_gap={metrics.get('coverage_gap')}, all_rows_pass={metrics.get('all_rows_pass')}"
        )
    lines.append("")
    lines.append("## Executed rows")
    for row in comparison.get("rows") or []:
        lines.append(
            f"- {row['group_id']}::{row['case_id']}::{row['dimension']} "
            f"(status={row['readiness_status']}, findings={row['finding_count']})"
        )
    if request_manifest.get("skipped"):
        lines.append("")
        lines.append("## Skipped")
        for item in request_manifest["skipped"]:
            lines.append(
                f"- {item.get('group_id')}::{item.get('case_id')}::{item.get('dimension')} "
                f"reason={item.get('reason')} status={item.get('status')}"
            )
    (OUT_DIR / "trial_notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_review(
    case_matrix_payload: dict[str, Any],
    snapshot_manifest: dict[str, Any],
    request_manifest: dict[str, Any],
    comparison: dict[str, Any],
    cost_observation: dict[str, Any],
) -> None:
    group_metrics = comparison.get("group_metrics") or {}
    overall_pass = bool(comparison.get("overall_pass"))
    review_json = {
        "review": "brand3_evidence_packet_real_validation_batch_v2_1",
        "mode": "lab_only_non_runtime_non_mutating",
        "created_at": _now(),
        "case_resolution": {
            "resolved_total": case_matrix_payload.get("resolved_total"),
            "unresolved_total": case_matrix_payload.get("unresolved_total"),
            "groups": {
                gid: {
                    "selected_count": data.get("selected_count"),
                    "coverage_gap": data.get("coverage_gap"),
                    "selected_primary_count": data.get("selected_primary_count"),
                    "selected_backup_count": data.get("selected_backup_count"),
                }
                for gid, data in (case_matrix_payload.get("groups") or {}).items()
            },
        },
        "execution": {
            "llm_calls_planned": cost_observation.get("llm_calls_planned"),
            "llm_calls_executed": cost_observation.get("llm_calls_executed"),
            "parse_failures_unrecovered": cost_observation.get("parse_failures_unrecovered"),
            "json_repair_retries_attempted": cost_observation.get("json_repair_retries_attempted"),
            "json_repair_retries_succeeded": cost_observation.get("json_repair_retries_succeeded"),
        },
        "pass_criteria": comparison.get("pass_criteria"),
        "group_level_flags": comparison.get("group_level_flags"),
        "group_metrics": group_metrics,
        "overall_pass": overall_pass,
        "assessment": {
            "drift_behavior": "bounded" if comparison.get("pass_criteria", {}).get("risky_terms_outside_limits_empty") else "drift_detected",
            "blocked_review_handling_quality": "enforced" if comparison.get("pass_criteria", {}).get("blocked_controls_skipped") else "failed",
            "readiness_distribution": {gid: m.get("readiness_distribution") for gid, m in group_metrics.items()},
        },
        "decision_gate": (
            "pass_promote_as_default_lab_benchmark"
            if overall_pass
            else "fail_keep_experimental_and_document_failure_classes"
        ),
        "failure_classes": _failure_classes(comparison, case_matrix_payload),
    }
    REVIEW_JSON.write_text(json.dumps(review_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_lines = [
        "# Brand3 Evidence Packet Real Validation Batch v2.1 Review",
        "",
        f"- Overall pass: `{overall_pass}`",
        f"- Executed rows: `{comparison.get('cases_executed')}`",
        f"- Skipped rows: `{comparison.get('cases_skipped')}`",
        f"- Resolved cases: `{case_matrix_payload.get('resolved_total')}`",
        f"- Unresolved cases: `{case_matrix_payload.get('unresolved_total')}`",
        "",
        "## Group behavior",
    ]
    for gid, m in group_metrics.items():
        md_lines.append(
            f"- `{gid}`: selected={m.get('selected_count')}, executed={m.get('executed_count')}, "
            f"coverage_gap={m.get('coverage_gap')}, readiness={m.get('readiness_distribution')}"
        )
    md_lines.extend(
        [
            "",
            "## Pass criteria",
            f"- Global: `{comparison.get('pass_criteria')}`",
            f"- Group-level: `{comparison.get('group_level_flags')}`",
            "",
            "## Recommendation",
            (
                "- Promote v2.1 dry-path as default lab benchmark for pre-runtime candidate integration."
                if overall_pass
                else "- Keep v2.1 experimental. Resolve failure classes before promotion."
            ),
        ]
    )
    REVIEW_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def _failure_classes(comparison: dict[str, Any], case_matrix_payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    pass_criteria = comparison.get("pass_criteria") or {}
    if not pass_criteria.get("no_typical_decision", False):
        failures.append("drift")
    if not pass_criteria.get("blocked_controls_skipped", False):
        failures.append("gating")
    if (pass_criteria.get("parse_failures_unrecovered") or 0) != 0:
        failures.append("parse")
    coverage_gaps = [
        int(group.get("coverage_gap") or 0)
        for group in (case_matrix_payload.get("groups") or {}).values()
    ]
    if any(gap > 0 for gap in coverage_gaps):
        failures.append("url_canonicalization")
        failures.append("readiness")
    return sorted(set(failures))


def _repair_user_prompt(user_payload: str) -> str:
    return (
        user_payload
        + "\n\nReturn valid JSON exactly matching the schema. "
        + "No markdown fences, no comments, no trailing commas."
    )


def _has_findings(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    findings = data.get("findings")
    return isinstance(findings, list) and len(findings) > 0


def _is_json_parse_failure(analyzer: LLMAnalyzer) -> bool:
    if not analyzer.call_failures:
        return False
    last = str(analyzer.call_failures[-1]).lower()
    return "json" in last or "parse" in last


def _normalized_host(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _write_json(name: str, payload: dict[str, Any]) -> None:
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
