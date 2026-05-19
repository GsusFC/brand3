#!/usr/bin/env python3
"""Lab-only unified v1 trial for findings schema across ready/thin/blocked profiles."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer


OUT_DIR = Path("examples/reports/evidence_packet_findings_schema_trial/unified_v1")
INPUT_DIR = Path("examples/reports/evidence_packet_prompt_input")
PREVIOUS_DIR = Path("examples/reports/evidence_packet_prompt_input_generation")

TARGETS = [
    {"case_id": "linear", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "vercel", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "launchdarkly", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "linear", "dimension": "coherencia", "intent": "ready"},
    {"case_id": "vercel", "dimension": "coherencia", "intent": "thin"},
    {"case_id": "launchdarkly", "dimension": "vitalidad", "intent": "ready"},
    {"case_id": "watermelon", "dimension": "percepcion", "intent": "thin"},
    {"case_id": "watermelon", "dimension": "vitalidad", "intent": "blocked_control"},
    {"case_id": "builtwith_kit_com", "dimension": "coherencia", "intent": "blocked_control"},
    {"case_id": "builtwith_kit_com", "dimension": "percepcion", "intent": "blocked_control"},
    {"case_id": "launchdarkly", "dimension": "coherencia", "intent": "review_required_control"},
]

SYSTEM = """You are a strict evidence analyst for a Brand3 lab experiment.
Return JSON only. Do not write report prose. Do not recommend strategy.
Do not infer leadership, advantage, superiority, moat, traction, adoption,
customer preference, intent, roadmap, or planning direction.

Use only included evidence. If evidence is narrow, produce narrow findings."""

SCHEMA = {
    "findings": [
        {
            "title": "",
            "evidence_anchor": "",
            "observation": "",
            "bounded_interpretation": "",
            "limits": "",
            "evidence_urls": [],
        }
    ]
}

INCLUDED_STATUSES = {"ready", "thin"}


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
        "notes": ["Unified v1 lab trial; provider usage metadata not exposed by LLMAnalyzer."],
        "json_repair_retries_attempted": 0,
        "json_repair_retries_succeeded": 0,
    }

    if args.execute and manifest["requests"]:
        analyzer = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
        for request in manifest["requests"]:
            result = _call(analyzer, request)
            raw_outputs["results"].append(result)
            if result.get("json_repair_retry_attempted"):
                cost_observation["json_repair_retries_attempted"] += 1
            if result.get("json_repair_retry_succeeded"):
                cost_observation["json_repair_retries_succeeded"] += 1
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
                    "allowed_evidence_urls": request["allowed_evidence_urls"],
                    "executed": False,
                    "raw_response": None,
                    "summary": _summary(None, request["allowed_evidence_urls"], request["dimension"]),
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
        status = dim["readiness_status"]
        if status not in INCLUDED_STATUSES:
            skipped.append(
                {
                    "case_id": case_id,
                    "dimension": dimension,
                    "status": status,
                    "intent": target["intent"],
                    "reason": "status_not_executable_for_lab_call",
                }
            )
            continue

        allowed_urls = sorted({item.get("url") for item in dim["evidence"] if str(item.get("url") or "").strip()})
        user_payload = {
            "task": f"Create bounded evidence findings for {case_id}/{dimension}.",
            "schema": SCHEMA,
            "field_rules": {
                "title": "3-6 words. Pattern, not quality.",
                "evidence_anchor": "Quote, source, URL, or measured evidence used.",
                "observation": "Only what included evidence supports.",
                "bounded_interpretation": "Conditional interpretation only; no strategy, recommendation, or category leadership.",
                "limits": "What the evidence does not prove.",
                "evidence_urls": "Only URLs/provenance values present in included evidence.",
            },
            "prompt_rules": [
                "Do not include typical_decision.",
                "Do not generate strategic choices.",
                "Do not recommend actions.",
                "Do not infer leadership, advantage, superiority, moat, traction, adoption, customer preference, intent, or roadmap.",
                "For competitor comparison evidence, only discuss relative positioning distance.",
                "Use only included evidence URLs.",
                "If evidence is narrow, produce one narrow finding rather than broad prose.",
                "Return JSON only.",
            ],
            "included_evidence": [
                {
                    "text": item["text"],
                    "url": item["url"],
                    "source_class": item["source_class"],
                    "limits": item.get("limits") or "",
                }
                for item in dim["evidence"]
            ],
        }
        requests.append(
            {
                "case_id": case_id,
                "dimension": dimension,
                "intent": target["intent"],
                "readiness_status": status,
                "source": "evidence_packet_prompt_input_candidate",
                "model": LLM_PREMIUM_MODEL,
                "system": SYSTEM,
                "user": json.dumps(user_payload, indent=2, ensure_ascii=False),
                "max_tokens": 1800,
                "allowed_evidence_urls": allowed_urls,
            }
        )
    return {"created_at": _now(), "requests": requests, "skipped": skipped}


def _call(analyzer: LLMAnalyzer, request: dict[str, Any]) -> dict[str, Any]:
    data = analyzer._call_json(
        system=request["system"],
        user=request["user"],
        max_tokens=int(request["max_tokens"]),
    )
    retry_attempted = False
    retry_succeeded = False
    repair_reason = None

    if not _has_findings(data) and _is_json_parse_failure(analyzer):
        retry_attempted = True
        repair_reason = "json_parse_error"
        data_retry = analyzer._call_json(
            system=request["system"],
            user=_repair_user_prompt(request["user"]),
            max_tokens=int(request["max_tokens"]),
        )
        if _has_findings(data_retry):
            data = data_retry
            retry_succeeded = True

    return {
        "created_at": _now(),
        "case_id": request["case_id"],
        "dimension": request["dimension"],
        "intent": request["intent"],
        "readiness_status": request["readiness_status"],
        "allowed_evidence_urls": request["allowed_evidence_urls"],
        "raw_response": data,
        "summary": _summary(data, request["allowed_evidence_urls"], request["dimension"]),
        "json_repair_retry_attempted": retry_attempted,
        "json_repair_retry_succeeded": retry_succeeded,
        "json_repair_retry_reason": repair_reason,
    }


def _summary(data: Any, allowed_urls: list[str], dimension: str) -> dict[str, Any]:
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list):
        findings = []
    text = json.dumps(findings, ensure_ascii=False).lower()
    text_without_limits = json.dumps(
        [{k: v for k, v in item.items() if k != "limits"} for item in findings if isinstance(item, dict)],
        ensure_ascii=False,
    ).lower()
    risky_terms = [
        "strategy",
        "strategic",
        "recommend",
        "should",
        "must",
        "needs to",
        "leadership",
        "advantage",
        "superior",
        "moat",
        "traction",
        "adoption",
        "customer preference",
        "roadmap",
    ]
    risky_terms_outside_limits = _risky_terms_outside_limits(
        text_without_limits=text_without_limits,
        risky_terms=risky_terms,
        dimension=dimension,
    )
    urls_used: list[str] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        urls = item.get("evidence_urls")
        if isinstance(urls, list):
            urls_used.extend(str(url) for url in urls if isinstance(url, str))
    urls_used = sorted(set(urls_used))
    url_validity = all(url in allowed_urls for url in urls_used) if urls_used else True
    return {
        "finding_count": len(findings),
        "titles": [str(item.get("title") or "") for item in findings if isinstance(item, dict)],
        "risky_terms_detected": [term for term in risky_terms if term in text],
        "risky_terms_outside_limits": risky_terms_outside_limits,
        "limits_field_present": all(bool(str(item.get("limits") or "").strip()) for item in findings if isinstance(item, dict))
        if findings
        else False,
        "has_typical_decision": "typical_decision" in text,
        "evidence_urls_used": urls_used,
        "evidence_url_validity": url_validity,
    }


def _risky_terms_outside_limits(text_without_limits: str, risky_terms: list[str], dimension: str) -> list[str]:
    flagged = [term for term in risky_terms if term in text_without_limits]
    if "leadership" not in flagged or dimension != "vitalidad":
        return flagged

    factual_markers = (
        "leadership team",
        "leadership teams",
        "leadership expansion",
        "expanded leadership",
        "executive team",
        "executive hire",
        "appointed",
    )
    strategic_markers = (
        "market leadership",
        "category leadership",
        "industry leadership",
        "leadership position",
        "leadership over",
        "leadership in",
    )
    if any(marker in text_without_limits for marker in factual_markers) and not any(
        marker in text_without_limits for marker in strategic_markers
    ):
        return [term for term in flagged if term != "leadership"]
    return flagged


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
            "summary": result["summary"],
            "previous_candidate_schema_summary": previous_summary,
            "risky_terms_delta": {
                "previous_outside_limits": previous_summary.get("risky_terms_outside_limits", []),
                "new_outside_limits": result["summary"]["risky_terms_outside_limits"],
            },
        }

    executed = bool(raw_outputs.get("executed"))
    if executed and results:
        pass_flags = {
            "no_typical_decision": all(not result["summary"]["has_typical_decision"] for result in results),
            "limits_present": all(result["summary"]["limits_field_present"] for result in results),
            "risky_terms_outside_limits_empty": all(len(result["summary"]["risky_terms_outside_limits"]) == 0 for result in results),
            "blocked_or_review_controls_skipped": _controls_skipped(manifest["skipped"]),
            "thin_cases_qualified": _thin_cases_qualified(per_case),
            "evidence_urls_valid": all(result["summary"]["evidence_url_validity"] for result in results),
        }
    else:
        pass_flags = {
            "no_typical_decision": None,
            "limits_present": None,
            "risky_terms_outside_limits_empty": None,
            "blocked_or_review_controls_skipped": _controls_skipped(manifest["skipped"]),
            "thin_cases_qualified": None,
            "evidence_urls_valid": None,
        }

    return {
        "created_at": _now(),
        "executed": executed,
        "requests_executed": len(results),
        "requests_skipped": len(manifest["skipped"]),
        "per_case": per_case,
        "pass_flags": pass_flags,
        "trial_pass": all(value is True for value in pass_flags.values()) if executed else None,
        "manual_review_required": True,
    }


def _controls_skipped(skipped: list[dict[str, Any]]) -> bool:
    expected = {
        ("watermelon", "vitalidad"),
        ("builtwith_kit_com", "coherencia"),
        ("builtwith_kit_com", "percepcion"),
        ("launchdarkly", "coherencia"),
    }
    actual = {(item["case_id"], item["dimension"]) for item in skipped}
    return expected.issubset(actual)


def _thin_cases_qualified(per_case: dict[str, Any]) -> bool:
    keys = ("vercel::coherencia", "watermelon::percepcion")
    for key in keys:
        if key not in per_case:
            return False
        summary = per_case[key]["summary"]
        if summary["finding_count"] > 2 or len(summary["risky_terms_outside_limits"]) != 0:
            return False
    return True


def _previous_summary(case_id: str, dimension: str) -> dict[str, Any]:
    # Historical candidate output exists only for linear/diferenciacion.
    if not (case_id == "linear" and dimension == "diferenciacion"):
        return {"available": False}
    previous_path = PREVIOUS_DIR / case_id / "candidate_output.json"
    if not previous_path.exists():
        return {"available": False}
    previous = json.loads(previous_path.read_text())
    return _summary(previous.get("raw_response"), [], dimension)


def _write_json(name: str, payload: dict[str, Any]) -> None:
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _write_notes(manifest: dict[str, Any], comparison: dict[str, Any], executed: bool) -> None:
    (OUT_DIR / "trial_notes.md").write_text(
        f"""# Evidence Packet Findings Schema Unified Trial v1

Status: {'executed' if executed else 'prepared only'}

Executable requests: {len(manifest['requests'])}
Skipped controls: {len(manifest['skipped'])}
Trial pass: {comparison['trial_pass']}

Coverage: diferenciacion + coherencia + vitalidad + percepcion.
This is lab-only. No runtime or production prompt changes.
"""
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


if __name__ == "__main__":
    main()
