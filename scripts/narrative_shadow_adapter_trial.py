#!/usr/bin/env python3
"""Lab-only narrative shadow adapter trial (non-runtime)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import BRAND3_DB_PATH
from src.config import LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.reports.evidence_packet import build_evidence_packet_v0
from src.reports.evidence_packet_prompt_input import build_prompt_input_candidate_v0
from src.reports.narrative_shadow_adapter import (
    build_shadow_narrative_request,
    parse_shadow_narrative_response,
)
from src.storage.sqlite_store import SQLiteStore


INPUT_MANIFEST = Path("examples/reports/evidence_packet_candidate_integration_dry_path_v2_1/request_manifest.json")
BASELINE_COMPARISON = Path("examples/reports/evidence_packet_candidate_integration_dry_path_v2_1/comparison.json")
OUT_DIR = Path("examples/reports/narrative_shadow_adapter_trial")
REVIEW_MD = Path("docs/brand3_narrative_shadow_adapter_trial_review.md")
REVIEW_JSON = Path("docs/brand3_narrative_shadow_adapter_trial_review.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--run-id", type=int, default=None, help="Optional run_id filter for a single case slice.")
    parser.add_argument(
        "--source",
        choices=("benchmark", "run"),
        default="benchmark",
        help="benchmark: use v2.1 request manifest, run: build ad-hoc manifest from a run snapshot.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_manifest = _load_source_manifest(args.source, args.run_id)
    baseline = json.loads(BASELINE_COMPARISON.read_text()) if BASELINE_COMPARISON.exists() else {}

    manifest = _build_manifest(source_manifest, run_id=args.run_id)
    _write_json("request_manifest.json", manifest)

    raw_outputs: dict[str, Any] = {
        "created_at": _now(),
        "executed": bool(args.execute),
        "model": LLM_PREMIUM_MODEL,
        "source_manifest": str(INPUT_MANIFEST) if args.source == "benchmark" else f"run_snapshot:{args.run_id}",
        "run_id_filter": args.run_id,
        "source_mode": args.source,
        "results": [],
        "skipped": manifest["skipped"],
    }
    cost_observation: dict[str, Any] = {
        "created_at": _now(),
        "execute_requested": bool(args.execute),
        "executed": False,
        "llm_calls_planned": len(manifest["requests"]),
        "llm_calls_executed": 0,
        "source_mode": args.source,
        "model": LLM_PREMIUM_MODEL,
        "usage_metadata_available": False,
        "cost_estimate_available": False,
        "notes": [
            "Narrative shadow adapter trial over candidate dry-path v2.1 manifest."
            if args.source == "benchmark"
            else f"Narrative shadow adapter ad-hoc trial from run snapshot {args.run_id}."
        ],
        "json_repair_retries_attempted": 0,
        "json_repair_retries_succeeded": 0,
        "parse_failures_unrecovered": 0,
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
                    "created_at": _now(),
                    "case_id": request["case_id"],
                    "dimension": request["dimension"],
                    "intent": request["intent"],
                    "readiness_status": request["readiness_status"],
                    "included_evidence_count": request["included_evidence_count"],
                    "allowed_evidence_urls": request["allowed_evidence_urls"],
                    "group_id": request.get("group_id"),
                    "source_type": request.get("source_type"),
                    "run_id": request.get("run_id"),
                    "executed": False,
                    "raw_response": None,
                    "summary": parse_shadow_narrative_response(None, request["allowed_evidence_urls"], request["dimension"]),
                    "json_repair_retry_attempted": False,
                    "json_repair_retry_succeeded": False,
                    "parse_failure_unrecovered": False,
                }
            )

    comparison = _comparison(manifest, raw_outputs, baseline)
    _write_json("raw_outputs.json", raw_outputs)
    _write_json("comparison.json", comparison)
    _write_json("cost_observation.json", cost_observation)
    _write_notes(manifest, comparison, bool(args.execute))
    _write_review(comparison, cost_observation)


def _build_manifest(source_manifest: dict[str, Any], *, run_id: int | None = None) -> dict[str, Any]:
    requests: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = list(source_manifest.get("skipped") or [])
    for row in source_manifest.get("requests") or []:
        if run_id is not None and int(row.get("run_id") or -1) != run_id:
            continue
        request, skip = build_shadow_narrative_request(row, model=LLM_PREMIUM_MODEL)
        if skip:
            skipped.append(skip)
            continue
        if request:
            requests.append(request)
    if run_id is not None:
        filtered: list[dict[str, Any]] = []
        for item in skipped:
            value = item.get("run_id")
            if value is None:
                continue
            try:
                if int(value) == run_id:
                    filtered.append(item)
            except Exception:
                continue
        skipped = filtered
    return {
        "created_at": _now(),
        "source_created_at": source_manifest.get("created_at"),
        "run_id_filter": run_id,
        "source_mode": source_manifest.get("source_mode", "benchmark"),
        "source_reference": source_manifest.get("source_reference"),
        "requests": requests,
        "skipped": skipped,
    }


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
        "group_id": request.get("group_id"),
        "source_type": request.get("source_type"),
        "run_id": request.get("run_id"),
        "raw_response": data,
        "summary": parse_shadow_narrative_response(data, request["allowed_evidence_urls"], request["dimension"]),
        "json_repair_retry_attempted": retry_attempted,
        "json_repair_retry_succeeded": retry_succeeded,
        "parse_failure_unrecovered": unrecovered,
    }


def _comparison(manifest: dict[str, Any], raw_outputs: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    baseline_per_case = (baseline.get("per_case") if isinstance(baseline, dict) else {}) or {}
    results = raw_outputs["results"]
    per_case: dict[str, Any] = {}
    delta_non_regressive = True

    for result in results:
        key = f"{result['case_id']}::{result['dimension']}"
        summary = result["summary"] or {}
        baseline_summary = (((baseline_per_case.get(key) or {}).get("summary")) or {})
        baseline_flags = {
            "has_typical_decision": bool(baseline_summary.get("has_typical_decision")),
            "limits_field_present": bool(baseline_summary.get("limits_field_present")),
            "risky_terms_outside_limits_empty": len(list(baseline_summary.get("risky_terms_outside_limits") or [])) == 0,
            "evidence_url_validity": bool(baseline_summary.get("evidence_url_validity")),
        }
        current_flags = {
            "has_typical_decision": bool(summary.get("has_typical_decision")),
            "limits_field_present": bool(summary.get("limits_field_present")),
            "risky_terms_outside_limits_empty": len(list(summary.get("risky_terms_outside_limits") or [])) == 0,
            "evidence_url_validity": bool(summary.get("evidence_url_validity")),
        }
        # non-regression: do not get worse than baseline in any gate.
        current_non_regressive = (
            (baseline_flags["has_typical_decision"] or (not current_flags["has_typical_decision"]))
            and (current_flags["limits_field_present"] >= baseline_flags["limits_field_present"])
            and (current_flags["risky_terms_outside_limits_empty"] >= baseline_flags["risky_terms_outside_limits_empty"])
            and (current_flags["evidence_url_validity"] >= baseline_flags["evidence_url_validity"])
        )
        delta_non_regressive = delta_non_regressive and bool(current_non_regressive)

        per_case[key] = {
            "case_id": result["case_id"],
            "dimension": result["dimension"],
            "group_id": result.get("group_id"),
            "run_id": result.get("run_id"),
            "intent": result["intent"],
            "readiness_status": result["readiness_status"],
            "included_evidence_count": result["included_evidence_count"],
            "summary": summary,
            "json_repair_retry_attempted": result["json_repair_retry_attempted"],
            "json_repair_retry_succeeded": result["json_repair_retry_succeeded"],
            "parse_failure_unrecovered": result["parse_failure_unrecovered"],
            "baseline_summary": baseline_summary,
            "delta_non_regressive": bool(current_non_regressive),
        }

    executed = bool(raw_outputs.get("executed"))
    parse_failures_unrecovered = sum(1 for result in results if result["parse_failure_unrecovered"])
    if executed and results:
        pass_flags = {
            "no_typical_decision": all(not bool((result["summary"] or {}).get("has_typical_decision")) for result in results),
            "limits_present": all(bool((result["summary"] or {}).get("limits_field_present")) for result in results),
            "risky_terms_outside_limits_empty": all(
                len(list((result["summary"] or {}).get("risky_terms_outside_limits") or [])) == 0 for result in results
            ),
            "evidence_urls_valid": all(bool((result["summary"] or {}).get("evidence_url_validity")) for result in results),
            "blocked_controls_skipped": _controls_skipped(manifest["skipped"]),
            "thin_cases_qualified": _thin_cases_qualified(results),
            "parse_failures_unrecovered_zero": parse_failures_unrecovered == 0,
            "delta_non_regressive_vs_v2_1": delta_non_regressive,
        }
    else:
        pass_flags = {
            "no_typical_decision": None,
            "limits_present": None,
            "risky_terms_outside_limits_empty": None,
            "evidence_urls_valid": None,
            "blocked_controls_skipped": _controls_skipped(manifest["skipped"]),
            "thin_cases_qualified": None,
            "parse_failures_unrecovered_zero": None,
            "delta_non_regressive_vs_v2_1": None,
        }

    return {
        "created_at": _now(),
        "executed": executed,
        "requests_executed": len(results),
        "requests_skipped": len(manifest["skipped"]),
        "parse_failures_unrecovered": parse_failures_unrecovered,
        "per_case": per_case,
        "pass_flags": pass_flags,
        "trial_pass": all(value is True for value in pass_flags.values()) if executed else None,
        "manual_review_required": True,
        "baseline_source": str(BASELINE_COMPARISON),
    }


def _controls_skipped(skipped: list[dict[str, Any]]) -> bool:
    controls = {(str(item.get("case_id") or ""), str(item.get("dimension") or "")) for item in skipped}
    expected = {
        ("synthesia", "diferenciacion"),
        ("dogstudio", "diferenciacion"),
        ("builtwith_kit_com", "coherencia"),
        ("builtwith_kit_com", "percepcion"),
    }
    return expected.issubset(controls)


def _thin_cases_qualified(results: list[dict[str, Any]]) -> bool:
    thin_rows = [result for result in results if str(result.get("readiness_status") or "") == "thin"]
    if not thin_rows:
        return True
    for row in thin_rows:
        summary = row.get("summary") or {}
        if int(summary.get("finding_count") or 0) > 2:
            return False
        if len(list(summary.get("risky_terms_outside_limits") or [])) != 0:
            return False
    return True


def _has_findings(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    findings = data.get("findings")
    return isinstance(findings, list) and len(findings) > 0


def _is_json_parse_failure(analyzer: LLMAnalyzer) -> bool:
    if not analyzer.call_failures:
        return False
    last = analyzer.call_failures[-1]
    return bool(last.get("json_parse_error"))


def _repair_user_prompt(user_payload: str) -> str:
    return (
        f"{user_payload}\n\n"
        "STRICT OUTPUT REQUIREMENT:\n"
        "- Return ONE valid JSON object only.\n"
        "- No markdown, no code fences, no comments, no trailing commas.\n"
        "- Escape all quotes inside string values.\n"
    )


def _write_json(name: str, payload: dict[str, Any]) -> None:
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _write_notes(manifest: dict[str, Any], comparison: dict[str, Any], executed: bool) -> None:
    (OUT_DIR / "trial_notes.md").write_text(
        f"""# Narrative Shadow Adapter Trial

Status: {'executed' if executed else 'prepared only'}
Source manifest: `{manifest.get('source_reference') or INPUT_MANIFEST}`
Baseline comparison: `{BASELINE_COMPARISON}`
Source mode: `{manifest.get('source_mode', 'benchmark')}`
Run filter: `{manifest.get('run_id_filter')}`

Executable requests: {len(manifest['requests'])}
Skipped controls: {len(manifest['skipped'])}
Trial pass: {comparison['trial_pass']}
Parse failures unrecovered: {comparison['parse_failures_unrecovered']}
Delta non-regressive vs v2.1: {comparison['pass_flags'].get('delta_non_regressive_vs_v2_1')}

This is lab-only. No runtime or production prompt changes.
"""
    )


def _write_review(comparison: dict[str, Any], cost_observation: dict[str, Any]) -> None:
    REVIEW_MD.write_text(
        "\n".join(
            [
                "# Brand3 Narrative Shadow Adapter Trial Review",
                "",
                f"- Executed: `{comparison['executed']}`",
                f"- Requests executed: `{comparison['requests_executed']}`",
                f"- Requests skipped: `{comparison['requests_skipped']}`",
                f"- Trial pass: `{comparison['trial_pass']}`",
                "",
                "## Pass Flags",
                f"- `{comparison['pass_flags']}`",
                "",
                "## Cost/robustness",
                f"- `json_repair_retries_attempted`: `{cost_observation.get('json_repair_retries_attempted')}`",
                f"- `json_repair_retries_succeeded`: `{cost_observation.get('json_repair_retries_succeeded')}`",
                f"- `parse_failures_unrecovered`: `{cost_observation.get('parse_failures_unrecovered')}`",
                "",
                "Decision gate: " + ("PASS" if comparison.get("trial_pass") else "FAIL"),
                "",
                "Lab-only. No runtime integration.",
            ]
        )
        + "\n"
    )
    REVIEW_JSON.write_text(
        json.dumps(
            {
                "created_at": _now(),
                "executed": comparison["executed"],
                "requests_executed": comparison["requests_executed"],
                "requests_skipped": comparison["requests_skipped"],
                "trial_pass": comparison["trial_pass"],
                "pass_flags": comparison["pass_flags"],
                "parse_failures_unrecovered": comparison["parse_failures_unrecovered"],
                "baseline_source": comparison["baseline_source"],
                "source_mode": cost_observation.get("source_mode"),
                "cost_observation": {
                    "json_repair_retries_attempted": cost_observation.get("json_repair_retries_attempted"),
                    "json_repair_retries_succeeded": cost_observation.get("json_repair_retries_succeeded"),
                    "parse_failures_unrecovered": cost_observation.get("parse_failures_unrecovered"),
                    "llm_calls_executed": cost_observation.get("llm_calls_executed"),
                    "model": cost_observation.get("model"),
                },
                "manual_review_required": True,
                "runtime_effect": False,
                "prompt_rollout": False,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_source_manifest(source_mode: str, run_id: int | None) -> dict[str, Any]:
    if source_mode == "benchmark":
        payload = json.loads(INPUT_MANIFEST.read_text())
        payload["source_mode"] = "benchmark"
        payload["source_reference"] = str(INPUT_MANIFEST)
        return payload
    if run_id is None:
        raise SystemExit("--run-id is required when --source=run")
    return _build_ad_hoc_manifest_from_run(run_id)


def _build_ad_hoc_manifest_from_run(run_id: int) -> dict[str, Any]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
    finally:
        store.close()
    if not snapshot:
        raise SystemExit(f"run_id {run_id} not found")

    packet = build_evidence_packet_v0(snapshot)
    candidate = build_prompt_input_candidate_v0(packet)
    requests: list[dict[str, Any]] = []

    case_id = str(candidate.get("case_id") or f"run_{run_id}")
    for dimension, data in (candidate.get("dimensions") or {}).items():
        requests.append(_candidate_row(case_id=case_id, run_id=run_id, dimension=dimension, data=data))

    return {
        "created_at": _now(),
        "source_mode": "run",
        "source_reference": f"run_snapshot:{run_id}",
        "run_id": run_id,
        "requests": requests,
        "skipped": [],
    }


def _candidate_row(*, case_id: str, run_id: int, dimension: str, data: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "task": f"Generate bounded findings for {case_id}/{dimension} from ad-hoc run_id={run_id}.",
        "prompt_rules": list(data.get("prompt_constraints") or []),
        "included_evidence": list(data.get("evidence") or []),
    }
    return {
        "case_id": case_id,
        "dimension": dimension,
        "intent": "ad_hoc_run",
        "readiness_status": str(data.get("readiness_status") or "abstain"),
        "group_id": "ad_hoc",
        "source_type": "run_snapshot",
        "run_id": run_id,
        "user": json.dumps(payload, ensure_ascii=False),
    }


if __name__ == "__main__":
    main()
