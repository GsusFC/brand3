#!/usr/bin/env python3
"""Run a controlled, non-runtime prompt-input generation trial for Linear.

The script compares the current Brand3 findings prompt input against the
Evidence Packet prompt-input candidate for one dimension: diferenciacion.
It writes prompts and raw JSON outputs to examples/, but it does not mutate
reports, scoring, persisted narrative payloads, or renderer behavior.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import LLM_PREMIUM_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.reports.derivation import collect_evidences, group_by_dimension
from src.reports.narrative import _FINDINGS_MAX_TOKENS, _FINDINGS_SYSTEM, _build_findings_user_prompt
from src.storage.sqlite_store import SQLiteStore


OUT_DIR = Path("examples/reports/evidence_packet_prompt_input_generation/linear")
RUN_ID = 80
DIMENSION = "diferenciacion"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Call the configured LLM twice.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot = _load_snapshot()
    packet_candidate = _load_prompt_input_candidate()

    current_prompt = _current_prompt(snapshot)
    candidate_prompt = _candidate_prompt(packet_candidate)
    _write_json("current_prompt.json", current_prompt)
    _write_json("candidate_prompt.json", candidate_prompt)

    cost_observation = {
        "created_at": _now(),
        "run_id": RUN_ID,
        "dimension": DIMENSION,
        "execute_requested": bool(args.execute),
        "llm_calls_planned": 2,
        "model": LLM_PREMIUM_MODEL,
        "usage_metadata_available": False,
        "cost_estimate_available": False,
        "notes": [
            "Provider response path used by LLMAnalyzer does not expose token usage metadata.",
            "Trial is limited to one case and one dimension.",
        ],
    }

    if args.execute:
        analyzer = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
        current_output = _call(analyzer, current_prompt)
        candidate_output = _call(analyzer, candidate_prompt)
        _write_json("current_output.json", current_output)
        _write_json("candidate_output.json", candidate_output)
        _write_json("comparison.json", _comparison(current_output, candidate_output, current_prompt, candidate_prompt))
        cost_observation.update(
            {
                "executed": True,
                "cache_hits": analyzer.cache_hits,
                "cache_misses": analyzer.cache_misses,
                "cache_writes": analyzer.cache_writes,
                "call_failures": analyzer.call_failures,
            }
        )
    else:
        cost_observation["executed"] = False

    _write_json("cost_observation.json", cost_observation)
    _write_notes(args.execute)


def _load_snapshot() -> dict:
    store = SQLiteStore("data/brand3.sqlite3")
    try:
        snapshot = store.get_run_snapshot(RUN_ID)
    finally:
        store.close()
    if snapshot is None:
        raise SystemExit(f"Missing local snapshot for run_id={RUN_ID}")
    return snapshot


def _load_prompt_input_candidate() -> dict:
    path = Path("examples/reports/evidence_packet_prompt_input/linear.prompt_input_candidate.v0.json")
    return json.loads(path.read_text())


def _current_prompt(snapshot: dict) -> dict[str, Any]:
    dimensions = group_by_dimension(collect_evidences(snapshot), snapshot)
    dim = next(item for item in dimensions if item.dimension == DIMENSION)
    run = snapshot.get("run") or {}
    return {
        "label": "current_brand3_findings_prompt",
        "case_id": "linear",
        "run_id": RUN_ID,
        "dimension": DIMENSION,
        "system": _FINDINGS_SYSTEM,
        "user": _build_findings_user_prompt(dim, "Linear", run.get("completed_at") or run.get("started_at")),
        "max_tokens": _FINDINGS_MAX_TOKENS,
        "model": LLM_PREMIUM_MODEL,
        "input_summary": {
            "evidence_count": len(dim.evidences),
            "score": dim.score,
            "verdict": dim.verdict,
        },
    }


def _candidate_prompt(candidate: dict) -> dict[str, Any]:
    dim = candidate["dimensions"][DIMENSION]
    evidence_lines = []
    for item in dim["evidence"]:
        limits = f" Limits: {item['limits']}" if item.get("limits") else ""
        evidence_lines.append(
            f"[{item['source_class']} · {item['feature_source']} · {item['classification_reason']}] "
            f"\"{item['text']}\" -> {item['url']}.{limits}"
        )
    constraints = "\n".join(f"- {constraint}" for constraint in dim["prompt_constraints"])
    user = f"""Dimension: Differentiation
Brand: Linear
Readiness status: {dim['readiness_status']}

Included evidence:
{chr(10).join(evidence_lines) or "(none)"}

Prompt constraints:
{constraints}

Return 1 to 3 findings using exactly this JSON shape:
{{"findings": [{{"title": "...", "observation": "...", "implication": "...", "typical_decision": "...", "evidence_urls": ["...", "..."]}}]}}

Additional trial rule:
- Do not use any evidence outside the Included evidence section.
- If the included evidence only supports relative positioning distance, say only that.
- Do not generate recommendations, leadership claims, superiority claims, adoption claims, or strategy claims.
"""
    return {
        "label": "evidence_packet_prompt_input_candidate",
        "case_id": "linear",
        "run_id": RUN_ID,
        "dimension": DIMENSION,
        "system": _FINDINGS_SYSTEM,
        "user": user,
        "max_tokens": _FINDINGS_MAX_TOKENS,
        "model": LLM_PREMIUM_MODEL,
        "input_summary": {
            "evidence_count": len(dim["evidence"]),
            "readiness_status": dim["readiness_status"],
            "constraints_count": len(dim["prompt_constraints"]),
        },
    }


def _call(analyzer: LLMAnalyzer, prompt: dict[str, Any]) -> dict[str, Any]:
    started = _now()
    data = analyzer._call_json(
        system=prompt["system"],
        user=prompt["user"],
        max_tokens=int(prompt["max_tokens"]),
    )
    return {
        "label": prompt["label"],
        "created_at": _now(),
        "started_at": started,
        "model": prompt["model"],
        "dimension": prompt["dimension"],
        "raw_response": data,
        "summary": _output_summary(data),
    }


def _output_summary(data: Any) -> dict[str, Any]:
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list):
        findings = []
    text = json.dumps(findings, ensure_ascii=False).lower()
    risky_terms = [
        "leading",
        "superior",
        "market advantage",
        "moat",
        "traction",
        "customer preference",
        "strategy",
        "strategic",
        "should",
        "must",
        "needs to",
    ]
    return {
        "finding_count": len(findings),
        "titles": [str(item.get("title") or "") for item in findings if isinstance(item, dict)],
        "risky_terms_detected": [term for term in risky_terms if term in text],
    }


def _comparison(current_output: dict, candidate_output: dict, current_prompt: dict, candidate_prompt: dict) -> dict:
    return {
        "case_id": "linear",
        "dimension": DIMENSION,
        "current_input_evidence_count": current_prompt["input_summary"]["evidence_count"],
        "candidate_input_evidence_count": candidate_prompt["input_summary"]["evidence_count"],
        "current_output_summary": current_output["summary"],
        "candidate_output_summary": candidate_output["summary"],
        "candidate_is_more_constrained": candidate_prompt["input_summary"]["constraints_count"] > 0,
        "manual_review_required": True,
    }


def _write_json(name: str, payload: dict) -> None:
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _write_notes(executed: bool) -> None:
    status = "executed" if executed else "prepared only"
    (OUT_DIR / "trial_notes.md").write_text(
        f"""# Linear Prompt Input Generation Trial

Status: {status}

Scope:

- one case: Linear
- one dimension: diferenciacion
- current Brand3 findings prompt vs Evidence Packet prompt-input candidate
- no report mutation
- no prompt rollout
- no scoring/rendering changes

Artifacts:

- `current_prompt.json`
- `candidate_prompt.json`
- `current_output.json` if executed
- `candidate_output.json` if executed
- `comparison.json` if executed
- `cost_observation.json`
"""
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
