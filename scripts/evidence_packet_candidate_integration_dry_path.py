#!/usr/bin/env python3
"""Lab-only candidate integration dry-path for Evidence Packet prompt input."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.reports.evidence_packet_candidate_integration import (
    LAB_SYSTEM_PROMPT,
    build_lab_request,
    summarize_lab_response,
)


OUT_DIR = Path("examples/reports/evidence_packet_candidate_integration_dry_path")
INPUT_DIR = Path("examples/reports/evidence_packet_prompt_input")
PREVIOUS_DIR = Path("examples/reports/evidence_packet_prompt_input_generation")

TARGETS = [
    {"case_id": "linear", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "vercel", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "launchdarkly", "dimension": "vitalidad", "intent": "ready"},
    {"case_id": "vercel", "dimension": "coherencia", "intent": "thin"},
    {"case_id": "watermelon", "dimension": "percepcion", "intent": "thin"},
    {"case_id": "builtwith_kit_com", "dimension": "coherencia", "intent": "blocked_control"},
    {"case_id": "builtwith_kit_com", "dimension": "percepcion", "intent": "blocked_control"},
    {"case_id": "launchdarkly", "dimension": "coherencia", "intent": "review_required_control"},
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _build_manifest()
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
        "notes": ["Dry-path candidate integration lab trial."],
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
    _write_notes(manifest, comparison, bool(args.execute))


def _build_manifest() -> dict[str, Any]:
    requests: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for target in TARGETS:
        case_id = target["case_id"]
        dimension = target["dimension"]
        pair = (case_id, dimension)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        candidate = json.loads((INPUT_DIR / f"{case_id}.prompt_input_candidate.v0.json").read_text())
        dim = candidate["dimensions"][dimension]
        request, skip = build_lab_request(
            case_id=case_id,
            dimension=dimension,
            intent=target["intent"],
            model=LLM_PREMIUM_MODEL,
            task_label=f"Generate bounded findings for {case_id}/{dimension} in dry-path integration mode.",
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
    return summarize_lab_response(data, allowed_urls, dimension)


def _comparison(manifest: dict[str, Any], raw_outputs: dict[str, Any]) -> dict[str, Any]:
    results = raw_outputs["results"]
    per_case: dict[str, Any] = {}
    for result in results:
        key = f"{result['case_id']}::{result['dimension']}"
        previous_summary = _previous_summary(result["case_id"], result["dimension"])
        per_case[key] = {
            "case_id": result["case_id"],
            "dimension": result["dimension"],
            "intent": result["intent"],
            "readiness_status": result["readiness_status"],
            "included_evidence_count": result["included_evidence_count"],
            "summary": result["summary"],
            "json_repair_retry_attempted": result["json_repair_retry_attempted"],
            "json_repair_retry_succeeded": result["json_repair_retry_succeeded"],
            "parse_failure_unrecovered": result["parse_failure_unrecovered"],
            "previous_candidate_schema_summary": previous_summary,
            "drift_indicator": {
                "previous_has_typical_decision": previous_summary.get("has_typical_decision"),
                "current_has_typical_decision": result["summary"]["has_typical_decision"],
                "previous_risky_terms_outside_limits": previous_summary.get("risky_terms_outside_limits", []),
                "current_risky_terms_outside_limits": result["summary"]["risky_terms_outside_limits"],
            },
        }

    executed = bool(raw_outputs.get("executed"))
    parse_failures_unrecovered = sum(1 for result in results if result["parse_failure_unrecovered"])
    if executed and results:
        pass_flags = {
            "no_typical_decision": all(not result["summary"]["has_typical_decision"] for result in results),
            "limits_present": all(result["summary"]["limits_field_present"] for result in results),
            "risky_terms_outside_limits_empty": all(len(result["summary"]["risky_terms_outside_limits"]) == 0 for result in results),
            "evidence_urls_valid": all(result["summary"]["evidence_url_validity"] for result in results),
            "blocked_or_review_controls_skipped": _controls_skipped(manifest["skipped"]),
            "thin_cases_qualified": _thin_cases_qualified(per_case),
            "parse_failures_unrecovered_zero": parse_failures_unrecovered == 0,
        }
    else:
        pass_flags = {
            "no_typical_decision": None,
            "limits_present": None,
            "risky_terms_outside_limits_empty": None,
            "evidence_urls_valid": None,
            "blocked_or_review_controls_skipped": _controls_skipped(manifest["skipped"]),
            "thin_cases_qualified": None,
            "parse_failures_unrecovered_zero": None,
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
    }


def _controls_skipped(skipped: list[dict[str, Any]]) -> bool:
    expected = {
        ("builtwith_kit_com", "coherencia"),
        ("builtwith_kit_com", "percepcion"),
        ("launchdarkly", "coherencia"),
    }
    actual = {(item["case_id"], item["dimension"]) for item in skipped}
    return expected.issubset(actual)


def _thin_cases_qualified(per_case: dict[str, Any]) -> bool:
    for key in ("vercel::coherencia", "watermelon::percepcion"):
        if key not in per_case:
            return False
        summary = per_case[key]["summary"]
        if summary["finding_count"] > 2:
            return False
        if len(summary["risky_terms_outside_limits"]) != 0:
            return False
    return True


def _previous_summary(case_id: str, dimension: str) -> dict[str, Any]:
    if not (case_id == "linear" and dimension == "diferenciacion"):
        return {"available": False}
    previous_path = PREVIOUS_DIR / case_id / "candidate_output.json"
    if not previous_path.exists():
        return {"available": False}
    previous = json.loads(previous_path.read_text())
    return _summary(previous.get("raw_response"), [], dimension)


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
        f"""# Evidence Packet Candidate Integration Dry-Path

Status: {'executed' if executed else 'prepared only'}

Executable requests: {len(manifest['requests'])}
Skipped controls: {len(manifest['skipped'])}
Trial pass: {comparison['trial_pass']}
Parse failures unrecovered: {comparison['parse_failures_unrecovered']}

This is lab-only. No runtime or production prompt changes.
"""
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
