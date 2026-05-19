#!/usr/bin/env python3
"""Lab-only multi-case trial for the findings schema without typical_decision."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer


OUT_DIR = Path("examples/reports/evidence_packet_findings_schema_trial/multi_case_v0")
INPUT_DIR = Path("examples/reports/evidence_packet_prompt_input")
PREVIOUS_DIR = Path("examples/reports/evidence_packet_prompt_input_generation")

TARGETS = [
    {"case_id": "linear", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "vercel", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "launchdarkly", "dimension": "diferenciacion", "intent": "ready"},
    {"case_id": "watermelon", "dimension": "percepcion", "intent": "thin"},
    {"case_id": "builtwith_kit_com", "dimension": "percepcion", "intent": "negative_control_blocked"},
]

SYSTEM = """You are a strict evidence analyst for a Brand3 lab experiment.
Return JSON only. Do not write report prose. Do not recommend strategy.
Do not infer leadership, advantage, superiority, moat, traction, adoption,
customer preference, intent, roadmap, or planning direction.

Use only included evidence. If the evidence is narrow, produce one narrow
finding rather than broad interpretation."""

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
        "notes": ["Single trial batch for multi-case schema validation; provider usage metadata not exposed by LLMAnalyzer."],
    }

    if args.execute and manifest["requests"]:
        analyzer = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
        for request in manifest["requests"]:
            result = _call(analyzer, request)
            raw_outputs["results"].append(result)
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

    for target in TARGETS:
        case_id = target["case_id"]
        dimension = target["dimension"]
        path = INPUT_DIR / f"{case_id}.prompt_input_candidate.v0.json"
        candidate = json.loads(path.read_text())
        dim = candidate["dimensions"][dimension]
        status = dim["readiness_status"]
        if status not in INCLUDED_STATUSES:
            skipped.append(
                {
                    "case_id": case_id,
                    "dimension": dimension,
                    "status": status,
                    "reason": "status_not_executable_for_lab_call",
                }
            )
            continue

        allowed_urls = sorted({item.get("url") for item in dim["evidence"] if str(item.get("url") or "").strip()})
        request_payload = {
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
                "If evidence is too narrow, produce one narrow finding rather than broad prose.",
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
                "user": json.dumps(request_payload, indent=2, ensure_ascii=False),
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
    return {
        "created_at": _now(),
        "case_id": request["case_id"],
        "dimension": request["dimension"],
        "intent": request["intent"],
        "readiness_status": request["readiness_status"],
        "allowed_evidence_urls": request["allowed_evidence_urls"],
        "raw_response": data,
        "summary": _summary(data, request["allowed_evidence_urls"], request["dimension"]),
    }


def _summary(data: Any, allowed_urls: list[str], dimension: str) -> dict[str, Any]:
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list):
        findings = []
    text = json.dumps(findings, ensure_ascii=False).lower()
    text_without_limits = json.dumps(
        [
            {key: value for key, value in item.items() if key != "limits"}
            for item in findings
            if isinstance(item, dict)
        ],
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
    urls_used = []
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
        "limits_field_present": all(isinstance(item, dict) and bool(str(item.get("limits") or "").strip()) for item in findings) if findings else False,
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
    per_case = {}
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

    pass_flags = {
        "no_typical_decision": all(not result["summary"]["has_typical_decision"] for result in results),
        "limits_present": all(result["summary"]["limits_field_present"] for result in results),
        "risky_terms_outside_limits_empty": all(len(result["summary"]["risky_terms_outside_limits"]) == 0 for result in results),
        "blocked_dimensions_skipped_or_abstained": any(item["case_id"] == "builtwith_kit_com" for item in manifest["skipped"]),
        "thin_case_qualified": _thin_case_qualified(per_case),
        "evidence_urls_valid": all(result["summary"]["evidence_url_validity"] for result in results),
    }
    trial_pass = all(pass_flags.values())
    return {
        "created_at": _now(),
        "executed": raw_outputs["executed"],
        "requests_executed": len(results),
        "requests_skipped": len(manifest["skipped"]),
        "per_case": per_case,
        "pass_flags": pass_flags,
        "trial_pass": trial_pass,
        "manual_review_required": True,
    }


def _previous_summary(case_id: str, dimension: str) -> dict[str, Any]:
    path = PREVIOUS_DIR / case_id / "candidate_output.json"
    if not path.exists():
        return {"available": False}
    previous = json.loads(path.read_text())
    return _summary(previous.get("raw_response"), [], dimension)


def _thin_case_qualified(per_case: dict[str, Any]) -> bool:
    key = "watermelon::percepcion"
    if key not in per_case:
        return False
    summary = per_case[key]["summary"]
    return len(summary["risky_terms_outside_limits"]) == 0 and summary["finding_count"] <= 2


def _write_json(name: str, payload: dict[str, Any]) -> None:
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _write_notes(manifest: dict[str, Any], comparison: dict[str, Any], executed: bool) -> None:
    OUT_DIR.joinpath("trial_notes.md").write_text(
        f"""# Evidence Packet Findings Schema Multi-Case Trial

Status: {'executed' if executed else 'prepared only'}

Executed requests: {len(manifest['requests'])}
Skipped requests: {len(manifest['skipped'])}
Trial pass: {comparison['trial_pass']}

Cases requested:
- linear / diferenciacion
- vercel / diferenciacion
- launchdarkly / diferenciacion
- watermelon / percepcion
- builtwith_kit_com / percepcion (negative control; expected skip)

This is lab-only. No runtime integration or production prompt changes.
"""
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
