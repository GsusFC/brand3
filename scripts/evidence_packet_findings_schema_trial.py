#!/usr/bin/env python3
"""Lab-only findings schema trial for Evidence Packet inputs.

Runs one optional LLM call for Linear/diferenciacion using a schema without
typical_decision. This does not touch production prompts or report generation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer


OUT_DIR = Path("examples/reports/evidence_packet_findings_schema_trial/linear_diferenciacion")
CANDIDATE_PATH = Path("examples/reports/evidence_packet_prompt_input/linear.prompt_input_candidate.v0.json")
PREVIOUS_OUTPUT_PATH = Path("examples/reports/evidence_packet_prompt_input_generation/linear/candidate_output.json")


SYSTEM = """You are a strict evidence analyst for a Brand3 lab experiment.
Return JSON only. Do not write report prose. Do not recommend strategy.
Do not infer leadership, advantage, superiority, moat, traction, adoption,
customer preference, intent, roadmap, or planning direction.

Use only included evidence. If the evidence is narrow, produce one narrow
finding rather than broad interpretation."""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    request = _request()
    _write_json("request.json", request)

    cost = {
        "created_at": _now(),
        "execute_requested": bool(args.execute),
        "executed": False,
        "llm_calls_planned": 1,
        "model": LLM_PREMIUM_MODEL,
        "usage_metadata_available": False,
        "cost_estimate_available": False,
        "notes": ["One controlled lab call only; provider usage metadata is not exposed through LLMAnalyzer."],
    }

    if args.execute:
        analyzer = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
        raw_output = _call(analyzer, request)
        _write_json("raw_output.json", raw_output)
        comparison = _comparison(raw_output)
        _write_json("comparison.json", comparison)
        cost.update(
            {
                "executed": True,
                "cache_hits": analyzer.cache_hits,
                "cache_misses": analyzer.cache_misses,
                "cache_writes": analyzer.cache_writes,
                "call_failures": analyzer.call_failures,
            }
        )
    else:
        _write_json("raw_output.json", {"executed": False, "raw_response": None, "summary": _summary(None)})
        _write_json("comparison.json", {"executed": False, "manual_review_required": True})

    _write_json("cost_observation.json", cost)
    _write_notes(args.execute)


def _request() -> dict[str, Any]:
    candidate = json.loads(CANDIDATE_PATH.read_text())
    dim = candidate["dimensions"]["diferenciacion"]
    evidence_lines = []
    for item in dim["evidence"]:
        evidence_lines.append(
            {
                "text": item["text"],
                "url": item["url"],
                "source_class": item["source_class"],
                "limits": item.get("limits") or "",
            }
        )
    user = {
        "task": "Create bounded evidence findings for Linear/diferenciacion.",
        "schema": {
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
        },
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
        "included_evidence": evidence_lines,
    }
    return {
        "case_id": "linear",
        "dimension": "diferenciacion",
        "source": "evidence_packet_prompt_input_candidate",
        "model": LLM_PREMIUM_MODEL,
        "system": SYSTEM,
        "user": json.dumps(user, indent=2, ensure_ascii=False),
        "max_tokens": 1800,
    }


def _call(analyzer: LLMAnalyzer, request: dict[str, Any]) -> dict[str, Any]:
    data = analyzer._call_json(
        system=request["system"],
        user=request["user"],
        max_tokens=int(request["max_tokens"]),
    )
    return {
        "created_at": _now(),
        "model": request["model"],
        "case_id": request["case_id"],
        "dimension": request["dimension"],
        "raw_response": data,
        "summary": _summary(data),
    }


def _comparison(raw_output: dict[str, Any]) -> dict[str, Any]:
    previous = json.loads(PREVIOUS_OUTPUT_PATH.read_text())
    current_summary = raw_output["summary"]
    previous_summary = _summary(previous.get("raw_response"))
    return {
        "case_id": "linear",
        "dimension": "diferenciacion",
        "previous_schema": "observation_implication_typical_decision",
        "new_schema": "evidence_anchor_observation_bounded_interpretation_limits",
        "previous_summary": previous_summary,
        "new_summary": current_summary,
        "reduced_strategic_drift": bool(previous_summary["risky_terms_detected"]) and not bool(current_summary["risky_terms_detected"]),
        "limits_field_present": current_summary["limits_field_present"],
        "manual_review_required": True,
    }


def _summary(data: Any) -> dict[str, Any]:
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
    return {
        "finding_count": len(findings),
        "titles": [str(item.get("title") or "") for item in findings if isinstance(item, dict)],
        "risky_terms_detected": [term for term in risky_terms if term in text],
        "risky_terms_outside_limits": [term for term in risky_terms if term in text_without_limits],
        "limits_field_present": all(isinstance(item, dict) and bool(str(item.get("limits") or "").strip()) for item in findings) if findings else False,
        "has_typical_decision": "typical_decision" in text,
    }


def _write_json(name: str, payload: dict[str, Any]) -> None:
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _write_notes(executed: bool) -> None:
    (OUT_DIR / "trial_notes.md").write_text(
        f"""# Evidence Packet Findings Schema Trial

Status: {'executed' if executed else 'prepared only'}

Case: Linear
Dimension: diferenciacion

This lab trial removes `typical_decision` and asks for explicit `limits`.
No production prompt, report, scoring, renderer, or payload format was changed.
"""
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
