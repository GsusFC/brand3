#!/usr/bin/env python3
"""Lab-only candidate integration dry-path v2.1.

Consumes the segmented real-validation v2.1 request manifest and executes
bounded findings generation with the lab schema.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.reports.evidence_packet_candidate_integration import summarize_lab_response


INPUT_MANIFEST = Path("examples/reports/evidence_packet_real_validation_batch_v2_1/request_manifest.json")
OUT_DIR = Path("examples/reports/evidence_packet_candidate_integration_dry_path_v2_1")
REVIEW_MD = Path("docs/brand3_evidence_packet_candidate_integration_dry_path_v2_1_review.md")
REVIEW_JSON = Path("docs/brand3_evidence_packet_candidate_integration_dry_path_v2_1_review.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(INPUT_MANIFEST)
    _write_json("request_manifest.json", manifest)

    raw_outputs: dict[str, Any] = {
        "created_at": _now(),
        "executed": bool(args.execute),
        "model": LLM_PREMIUM_MODEL,
        "source_manifest": str(INPUT_MANIFEST),
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
        "notes": ["Dry-path candidate integration v2.1 over segmented real-validation matrix."],
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
                    "summary": summarize_lab_response(None, request["allowed_evidence_urls"], request["dimension"]),
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
    _write_review(manifest, comparison, cost_observation)


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    requests = []
    for row in payload.get("requests") or []:
        status = str(row.get("readiness_status") or "")
        if status not in {"ready", "thin"}:
            continue
        requests.append(row)
    skipped = list(payload.get("skipped") or [])
    return {"created_at": _now(), "source_created_at": payload.get("created_at"), "requests": requests, "skipped": skipped}


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
        "summary": summarize_lab_response(data, request["allowed_evidence_urls"], request["dimension"]),
        "json_repair_retry_attempted": retry_attempted,
        "json_repair_retry_succeeded": retry_succeeded,
        "parse_failure_unrecovered": unrecovered,
    }


def _comparison(manifest: dict[str, Any], raw_outputs: dict[str, Any]) -> dict[str, Any]:
    results = raw_outputs["results"]
    per_case: dict[str, Any] = {}
    for result in results:
        key = f"{result['case_id']}::{result['dimension']}"
        summary = result["summary"] or {}
        per_case[key] = {
            "case_id": result["case_id"],
            "dimension": result["dimension"],
            "group_id": result.get("group_id"),
            "intent": result["intent"],
            "readiness_status": result["readiness_status"],
            "included_evidence_count": result["included_evidence_count"],
            "summary": summary,
            "json_repair_retry_attempted": result["json_repair_retry_attempted"],
            "json_repair_retry_succeeded": result["json_repair_retry_succeeded"],
            "parse_failure_unrecovered": result["parse_failure_unrecovered"],
            "drift_indicator": {
                "current_has_typical_decision": bool(summary.get("has_typical_decision")),
                "current_risky_terms_outside_limits": list(summary.get("risky_terms_outside_limits") or []),
            },
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
            "blocked_or_review_controls_skipped": _controls_skipped(manifest["skipped"]),
            "thin_cases_qualified": _thin_cases_qualified(results),
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
    controls = {(str(item.get("case_id") or ""), str(item.get("dimension") or "")) for item in skipped}
    expected = {
        ("builtwith_kit_com", "coherencia"),
        ("builtwith_kit_com", "percepcion"),
    }
    if not expected.issubset(controls):
        return False
    return all(str(item.get("status") or "") in {"blocked", "review_required", "abstain"} for item in skipped)


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
        f"""# Evidence Packet Candidate Integration Dry-Path v2.1

Status: {'executed' if executed else 'prepared only'}
Source manifest: `{INPUT_MANIFEST}`

Executable requests: {len(manifest['requests'])}
Skipped controls: {len(manifest['skipped'])}
Trial pass: {comparison['trial_pass']}
Parse failures unrecovered: {comparison['parse_failures_unrecovered']}

This is lab-only. No runtime or production prompt changes.
"""
    )


def _write_review(manifest: dict[str, Any], comparison: dict[str, Any], cost_observation: dict[str, Any]) -> None:
    REVIEW_MD.write_text(
        "\n".join(
            [
                "# Brand3 Evidence Packet Candidate Integration Dry-Path v2.1 Review",
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
                "Lab-only. No runtime integration.",
            ]
        )
        + "\n"
    )
    REVIEW_JSON.write_text(
        json.dumps(
            {
                "created_at": _now(),
                "source_manifest": str(INPUT_MANIFEST),
                "executed": comparison["executed"],
                "requests_executed": comparison["requests_executed"],
                "requests_skipped": comparison["requests_skipped"],
                "trial_pass": comparison["trial_pass"],
                "pass_flags": comparison["pass_flags"],
                "parse_failures_unrecovered": comparison["parse_failures_unrecovered"],
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


if __name__ == "__main__":
    main()
