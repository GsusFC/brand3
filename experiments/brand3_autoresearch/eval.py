"""Evaluate Brand3 prompt candidates against a small AutoResearch harness."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_CASES_PATH = ROOT / "cases" / "cases.json"
DEFAULT_BASELINE_PATH = ROOT / "baseline" / "scorecard.json"
DEFAULT_CANDIDATE_DIR = ROOT / "candidate"


@dataclass
class CaseResult:
    case_id: str
    score: float
    coverage_score: float
    evidence_score: float
    noise_score: float
    structure_score: float
    detected_blocks: list[str]
    missing_required_blocks: list[str]
    forbidden_hits: list[str]
    notes: list[str]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_payload(candidate_obj: Any) -> dict[str, Any]:
    if isinstance(candidate_obj, dict) and isinstance(candidate_obj.get("payload"), dict):
        return candidate_obj["payload"]
    return candidate_obj if isinstance(candidate_obj, dict) else {}


def text_blob(value: Any) -> str:
    parts: list[str] = []

    def walk(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, str):
            if node.strip():
                parts.append(node)
            return
        if isinstance(node, dict):
            for item in node.values():
                walk(item)
            return
        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(value)
    return " ".join(parts).lower()


def block_is_detected(block: Any) -> bool:
    if not isinstance(block, dict):
        return False
    if bool(block.get("detected")):
        return True
    for key in ("content", "answer", "finding", "findings"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def evaluate_case(case: dict[str, Any], candidate: dict[str, Any], weights: dict[str, float]) -> CaseResult:
    detected_blocks: list[str] = []
    missing_required_blocks: list[str] = []
    forbidden_hits: list[str] = []
    notes: list[str] = []

    tldr = candidate.get("tldr_brand3")
    if not isinstance(tldr, dict):
        tldr = {}

    for block_id in case.get("required_blocks") or []:
        block = tldr.get(block_id)
        if block_is_detected(block):
            detected_blocks.append(block_id)
        else:
            missing_required_blocks.append(block_id)

    expected_absent = set(case.get("expected_absent_blocks") or [])
    for block_id in expected_absent:
        if block_is_detected(tldr.get(block_id)):
            notes.append(f"unexpected block detected: {block_id}")

    blob = text_blob(candidate)
    for term in case.get("forbid_terms") or []:
        normalized_term = str(term).strip().lower()
        if normalized_term and normalized_term in blob:
            forbidden_hits.append(normalized_term)

    language = str(case.get("language") or "").strip().lower()
    candidate_lang = str(candidate.get("lang") or candidate.get("language") or "").strip().lower()
    if language and candidate_lang and language != candidate_lang:
        notes.append(f"language mismatch: expected {language}, got {candidate_lang}")

    required_count = max(1, len(case.get("required_blocks") or []))
    coverage_score = len(detected_blocks) / required_count
    max_detected_blocks = case.get("max_detected_blocks")
    if isinstance(max_detected_blocks, int):
        coverage_score = min(coverage_score, 1.0 if len(detected_blocks) <= max_detected_blocks else 0.0)

    evidence_count = 0
    for block_id in detected_blocks:
        block = tldr.get(block_id)
        if isinstance(block, dict):
            evidence = block.get("evidence_used") or block.get("evidence") or []
            if isinstance(evidence, list) and evidence:
                evidence_count += 1
            elif isinstance(evidence, str) and evidence.strip():
                evidence_count += 1
    min_evidence_blocks = int(case.get("min_evidence_blocks") or 0)
    evidence_score = min(1.0, evidence_count / max(1, min_evidence_blocks or len(detected_blocks) or 1))

    if forbidden_hits:
        noise_score = max(0.0, 1.0 - (0.25 * len(forbidden_hits)))
    else:
        noise_score = 1.0

    required_top_level = case.get("required_top_level") or ["tldr_brand3", "diagnosis"]
    structure_hits = sum(1 for key in required_top_level if isinstance(candidate.get(key), (dict, list, str)))
    structure_score = structure_hits / max(1, len(required_top_level))

    if case.get("required_blocks") and not detected_blocks:
        notes.append("no required blocks detected")

    overall = round(
        (coverage_score * float(weights.get("coverage", 0.4)))
        + (evidence_score * float(weights.get("evidence", 0.3)))
        + (noise_score * float(weights.get("noise", 0.2)))
        + (structure_score * float(weights.get("structure", 0.1))),
        4,
    )

    return CaseResult(
        case_id=str(case.get("id") or "unknown"),
        score=overall,
        coverage_score=round(coverage_score, 4),
        evidence_score=round(evidence_score, 4),
        noise_score=round(noise_score, 4),
        structure_score=round(structure_score, 4),
        detected_blocks=detected_blocks,
        missing_required_blocks=missing_required_blocks,
        forbidden_hits=forbidden_hits,
        notes=notes,
    )


def render_report(results: list[CaseResult], baseline: dict[str, Any]) -> str:
    avg_score = round(sum(item.score for item in results) / max(1, len(results)), 4)
    lines = [
        "# Brand3 AutoResearch Report",
        "",
        f"- cases: {len(results)}",
        f"- average_score: {avg_score}",
        f"- baseline_version: {baseline.get('version', 'unknown')}",
        "",
        "## Per Case",
    ]
    for result in results:
        lines.extend(
            [
                "",
                f"### {result.case_id}",
                f"- score: {result.score}",
                f"- coverage: {result.coverage_score}",
                f"- evidence: {result.evidence_score}",
                f"- noise: {result.noise_score}",
                f"- structure: {result.structure_score}",
                f"- detected_blocks: {', '.join(result.detected_blocks) or 'none'}",
                f"- missing_required_blocks: {', '.join(result.missing_required_blocks) or 'none'}",
                f"- forbidden_hits: {', '.join(result.forbidden_hits) or 'none'}",
                f"- notes: {', '.join(result.notes) or 'none'}",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Brand3 AutoResearch candidates.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--json", action="store_true", dest="emit_json")
    args = parser.parse_args()

    cases_doc = load_json(args.cases)
    baseline = load_json(args.baseline)
    weights = baseline.get("weights") or {}

    results: list[CaseResult] = []
    for case in cases_doc.get("cases") or []:
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            continue
        candidate_path = args.candidate_dir / f"{case_id}.json"
        if not candidate_path.exists():
            results.append(
                CaseResult(
                    case_id=case_id,
                    score=0.0,
                    coverage_score=0.0,
                    evidence_score=0.0,
                    noise_score=0.0,
                    structure_score=0.0,
                    detected_blocks=[],
                    missing_required_blocks=list(case.get("required_blocks") or []),
                    forbidden_hits=[],
                    notes=["candidate missing"],
                )
            )
            continue
        candidate_obj = load_json(candidate_path)
        candidate = candidate_payload(candidate_obj)
        results.append(evaluate_case(case, candidate, weights))

    report_text = render_report(results, baseline)
    if args.report:
        args.report.write_text(report_text, encoding="utf-8")

    if args.emit_json:
        payload = {
            "baseline_version": baseline.get("version"),
            "average_score": round(sum(item.score for item in results) / max(1, len(results)), 4),
            "cases": [result.__dict__ for result in results],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(report_text, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

