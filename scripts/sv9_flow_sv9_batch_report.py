#!/usr/bin/env python3
"""Summarize SV9 Flow versus legacy SV9 shadow comparison payloads."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

SV9_FLOW_SV9_BATCH_REPORT_VERSION = "sv9-flow-sv9-batch-report-v1"

BLOCKING_NOT_DETECTED = frozenset({"magnetism", "mission", "value_proposition", "core_purpose"})
CORE_RECOVERY_REVIEW_COMPONENTS = frozenset({"core_purpose", "magnetism", "mission", "value_proposition"})
# Vision/values remain visible in the report, but they do not force manual review
# unless they also create a material score/component delta.
REVIEW_NOT_DETECTED = frozenset()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("compare_json", nargs="+", help="JSON files from scripts/sv9_flow_sv9_shadow_eval.py")
    parser.add_argument("--output", default="", help="Optional report output path")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.compare_json]
    report = build_batch_report(payloads, sources=args.compare_json)
    rendered = (
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        if args.format == "json"
        else render_markdown_report(report)
    )
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


def build_batch_report(payloads: list[dict[str, Any]], *, sources: list[str] | None = None) -> dict[str, Any]:
    rows = [
        _summarize_payload(payload, source=(sources or [None] * len(payloads))[index])
        for index, payload in enumerate(payloads)
        if isinstance(payload, dict)
    ]
    return {
        "schema_version": SV9_FLOW_SV9_BATCH_REPORT_VERSION,
        "run_count": len(rows),
        "summary": _summary(rows),
        "runs": rows,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    assessment_kinds = summary.get("assessment_kinds") if isinstance(summary.get("assessment_kinds"), dict) else {}
    lines = [
        "# SV9 Flow SV9 Batch Report",
        "",
        f"- schema: `{report.get('schema_version')}`",
        f"- runs: `{report.get('run_count')}`",
        f"- acceptable: `{summary.get('acceptable', 0)}`",
        f"- review: `{summary.get('review', 0)}`",
        f"- blocker: `{summary.get('blocker', 0)}`",
        "- assessment kinds: `"
        + ", ".join(f"{key}:{value}" for key, value in sorted(assessment_kinds.items()))
        + "`",
        "",
        "| brand | status | flow | legacy | delta | not detected | reasons |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for run in report.get("runs") or []:
        if not isinstance(run, dict):
            continue
        lines.append(
            "| {brand} | {status} | {flow} | {legacy} | {delta:+} | {not_detected} | {reasons} |".format(
                brand=run.get("brand_name") or "",
                status=run.get("assessment"),
                flow=run.get("flow_score"),
                legacy=run.get("legacy_score"),
                delta=run.get("score_delta") or 0,
                not_detected=", ".join(run.get("flow_not_detected") or []) or "-",
                reasons=", ".join(run.get("assessment_reasons") or []) or "-",
            )
        )
    lines.extend(["", "## Component Deltas"])
    for run in report.get("runs") or []:
        if not isinstance(run, dict):
            continue
        lines.append(f"### {run.get('brand_name')}")
        compact = []
        for key, component in sorted((run.get("components") or {}).items()):
            if not isinstance(component, dict):
                continue
            if component.get("score_delta") or component.get("status_changed"):
                compact.append(
                    "{key}:{delta:+} {flow}/{legacy}".format(
                        key=key,
                        delta=component.get("score_delta") or 0,
                        flow=component.get("flow_status"),
                        legacy=component.get("legacy_status"),
                    )
                )
        lines.append("- " + ("; ".join(compact) if compact else "no material component deltas"))
        gates = run.get("gate_decisions") if isinstance(run.get("gate_decisions"), dict) else {}
        if gates:
            rendered_gates = "; ".join(
                f"{key}:{value.get('outcome')}({', '.join(value.get('support_terms') or [])})"
                for key, value in sorted(gates.items())
                if isinstance(value, dict)
            )
            lines.append(f"- gates: `{rendered_gates}`")
        overrides = run.get("gate_overrides") if isinstance(run.get("gate_overrides"), list) else []
        if overrides:
            rendered_overrides = "; ".join(
                "{block}({terms})".format(
                    block=item.get("block"),
                    terms=", ".join(item.get("support_terms") or []) or "-",
                )
                for item in overrides
                if isinstance(item, dict)
            )
            lines.append(f"- gate overrides: `{rendered_overrides}`")
        tile_lines = _material_tile_change_lines(run.get("components") or {})
        if tile_lines:
            lines.append("- tile changes:")
            lines.extend(f"  - {line}" for line in tile_lines)
    return "\n".join(lines).rstrip()


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "acceptable": sum(1 for row in rows if row.get("assessment") == "acceptable"),
        "review": sum(1 for row in rows if row.get("assessment") == "review"),
        "blocker": sum(1 for row in rows if row.get("assessment") == "blocker"),
        "average_score_delta": _average([row.get("score_delta") for row in rows]),
        "blocker_brands": [row.get("brand_name") for row in rows if row.get("assessment") == "blocker"],
        "review_brands": [row.get("brand_name") for row in rows if row.get("assessment") == "review"],
        "assessment_kinds": dict(Counter(str(row.get("assessment_kind") or "unknown") for row in rows)),
        "gate_override_count": sum(len(row.get("gate_overrides") or []) for row in rows),
        "gate_override_brands": [
            row.get("brand_name")
            for row in rows
            if row.get("gate_overrides")
        ],
    }


def _summarize_payload(payload: dict[str, Any], *, source: str | None) -> dict[str, Any]:
    comparison = payload.get("comparison") if isinstance(payload.get("comparison"), dict) else {}
    flow = payload.get("sv9") if isinstance(payload.get("sv9"), dict) else {}
    legacy = payload.get("legacy_sv9") if isinstance(payload.get("legacy_sv9"), dict) else {}
    components = _component_summaries(comparison.get("components") if isinstance(comparison.get("components"), dict) else {})
    flow_not_evaluated = [str(item) for item in flow.get("not_evaluated") or []]
    legacy_not_evaluated = [str(item) for item in legacy.get("not_evaluated") or []]
    gate_decisions = _gate_decisions(payload)
    gate_overrides = _gate_overrides(payload, gate_decisions=gate_decisions)
    assessment, reasons = _assessment(
        score_delta=_number(comparison.get("brand3_score_delta")),
        not_detected_added=[str(item) for item in comparison.get("not_detected_added") or []],
        components=components,
        flow_components=flow.get("components") if isinstance(flow.get("components"), dict) else {},
        flow_not_evaluated=flow_not_evaluated,
        flow_reliability_status=str(flow.get("reliability_status") or ""),
        gate_overrides=gate_overrides,
    )
    return {
        "source": source,
        "brand_name": payload.get("brand_name"),
        "source_run_id": payload.get("source_run_id"),
        "url": payload.get("url"),
        "flow_score": flow.get("brand3_score"),
        "legacy_score": legacy.get("brand3_score"),
        "score_delta": _number(comparison.get("brand3_score_delta")),
        "base_average_delta": _number(comparison.get("base_average_delta")),
        "flow_not_detected": [str(item) for item in flow.get("not_detected") or []],
        "legacy_not_detected": [str(item) for item in legacy.get("not_detected") or []],
        "flow_not_evaluated": flow_not_evaluated,
        "legacy_not_evaluated": legacy_not_evaluated,
        "flow_reliability_status": flow.get("reliability_status"),
        "legacy_reliability_status": legacy.get("reliability_status"),
        "not_detected_added": [str(item) for item in comparison.get("not_detected_added") or []],
        "not_detected_removed": [str(item) for item in comparison.get("not_detected_removed") or []],
        "reliability_changed": comparison.get("reliability_changed"),
        "assessment": assessment,
        "assessment_kind": _assessment_kind(assessment, reasons),
        "assessment_reasons": reasons,
        "components": components,
        "gate_decisions": gate_decisions,
        "gate_overrides": gate_overrides,
    }


def _assessment(
    *,
    score_delta: int | float | None,
    not_detected_added: list[str],
    components: dict[str, dict[str, Any]],
    flow_components: dict[str, Any],
    flow_not_evaluated: list[str],
    flow_reliability_status: str,
    gate_overrides: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    blockers: list[str] = []
    reviews: list[str] = []
    if flow_reliability_status == "broken":
        blockers.append("flow_reliability_broken")
    if flow_not_evaluated:
        blockers.append("flow_not_evaluated:" + ",".join(sorted(flow_not_evaluated)))
    if score_delta is not None:
        absolute_delta = abs(score_delta)
        if score_delta < -12:
            blockers.append("score_delta_lt_minus_12")
        elif score_delta > 12:
            reviews.append("positive_score_delta_gt_12")
        elif absolute_delta > 5:
            reviews.append("score_delta_6_to_12")
    blocking_added = sorted(set(not_detected_added) & BLOCKING_NOT_DETECTED)
    if blocking_added:
        blockers.append("blocking_not_detected_added:" + ",".join(blocking_added))
    review_added = sorted(set(not_detected_added) & REVIEW_NOT_DETECTED)
    if review_added:
        reviews.append("review_not_detected_added:" + ",".join(review_added))
    large_component_deltas = [
        key
        for key, component in components.items()
        if _component_delta_requires_review(component)
    ]
    if large_component_deltas:
        reviews.append("component_delta_gte_4:" + ",".join(sorted(large_component_deltas)))
    positive_core_recoveries = [
        key
        for key, component in components.items()
        if _positive_core_recovery_requires_review(key, component)
    ]
    if positive_core_recoveries:
        reviews.append("positive_core_recovery_review:" + ",".join(sorted(positive_core_recoveries)))
    magnetism = flow_components.get("magnetism") if isinstance(flow_components.get("magnetism"), dict) else {}
    if _number(magnetism.get("score")) == 10:
        reviews.append("magnetism_ceiling_review")
    material_gate_overrides = _material_gate_override_blocks(gate_overrides, components)
    if material_gate_overrides:
        reviews.append("gate_override_review:" + ",".join(material_gate_overrides))
    gate_candidates = _gate_candidate_blocks(gate_overrides)
    if gate_candidates:
        # Every gate-positive/LLM-negative candidate reaches human review;
        # the material >=4 lane above is escalation, not the queue condition.
        reviews.append("gate_candidate_review:" + ",".join(gate_candidates))
    if blockers:
        return "blocker", blockers + reviews
    if reviews:
        return "review", reviews
    return "acceptable", []


def _assessment_kind(assessment: str, reasons: list[str]) -> str:
    if any(reason.startswith(("flow_not_evaluated:", "flow_reliability_broken")) for reason in reasons):
        return "technical_blocker"
    if any(reason.startswith("blocking_not_detected_added:") for reason in reasons):
        return "contract_blocker"
    if "score_delta_lt_minus_12" in reasons:
        return "legacy_delta_blocker"
    if any(reason.startswith(("score_delta_6_to_12", "positive_score_delta_gt_12")) for reason in reasons):
        return "legacy_delta_review"
    if any(
        reason.startswith(("component_delta_gte_4:", "review_not_detected_added:"))
        or reason == "magnetism_ceiling_review"
        or reason.startswith("gate_override_review:")
        or reason.startswith("gate_candidate_review:")
        or reason.startswith("positive_core_recovery_review:")
        for reason in reasons
    ):
        return "policy_review"
    return "acceptable" if assessment == "acceptable" else assessment


def _component_delta_requires_review(component: dict[str, Any]) -> bool:
    delta = _number(component.get("score_delta"))
    if delta is None:
        return False
    if delta <= -4:
        return True
    if delta >= 4:
        return component.get("flow_status") == "scored" and component.get("legacy_status") == "scored"
    return False


def _positive_core_recovery_requires_review(key: str, component: dict[str, Any]) -> bool:
    if key not in CORE_RECOVERY_REVIEW_COMPONENTS:
        return False
    delta = _number(component.get("score_delta"))
    return (
        delta is not None
        and delta >= 4
        and component.get("flow_status") == "scored"
        and component.get("legacy_status") == "not_detected"
    )


def _component_summaries(raw_components: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw_components.items():
        if not isinstance(value, dict):
            continue
        status = value.get("status") if isinstance(value.get("status"), dict) else {}
        tile_changes = value.get("tile_changes") if isinstance(value.get("tile_changes"), dict) else {}
        out[str(key)] = {
            "score_delta": _number(value.get("score_delta")),
            "flow_status": status.get("flow"),
            "legacy_status": status.get("legacy"),
            "status_changed": bool(value.get("status_changed")),
            "changed_tiles": _changed_tile_count(tile_changes),
            "tile_changes": _compact_tile_changes(tile_changes),
        }
    return out


def _compact_tile_changes(tile_changes: dict[str, Any]) -> dict[str, list[str]]:
    return {
        key: [str(item) for item in value]
        for key, value in tile_changes.items()
        if key != "changed" and isinstance(value, list) and value
    }


def _material_tile_change_lines(components: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, component in sorted(components.items()):
        if not isinstance(component, dict):
            continue
        changes = component.get("tile_changes") if isinstance(component.get("tile_changes"), dict) else {}
        rendered = _render_tile_changes(changes)
        if rendered:
            lines.append(f"{key}: {rendered}")
    return lines


def _render_tile_changes(changes: dict[str, list[str]]) -> str:
    labels = {
        "lit_added": "+lit",
        "lit_removed": "-lit",
        "blind_spot_added": "+blind",
        "blind_spot_removed": "-blind",
        "off_added": "+off",
        "off_removed": "-off",
    }
    parts = []
    for key in ("lit_added", "lit_removed", "blind_spot_added", "blind_spot_removed", "off_added", "off_removed"):
        values = changes.get(key)
        if values:
            parts.append(f"{labels[key]} {','.join(values)}")
    return "; ".join(parts)


def _changed_tile_count(tile_changes: dict[str, Any]) -> int:
    total = 0
    for key, value in tile_changes.items():
        if key == "changed":
            continue
        if isinstance(value, list):
            total += len(value)
    return total


def _gate_decisions(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    flow = payload.get("flow") if isinstance(payload.get("flow"), dict) else {}
    debug = flow.get("interpretation_debug") if isinstance(flow.get("interpretation_debug"), dict) else {}
    decisions = debug.get("block_detection_decisions")
    if not isinstance(decisions, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in decisions:
        if not isinstance(item, dict) or not item.get("block"):
            continue
        out[str(item["block"])] = {
            "outcome": item.get("outcome"),
            "limitation_code": item.get("limitation_code") or "",
            "support_terms": [str(term) for term in item.get("support_terms") or []],
            "weaken_terms": [str(term) for term in item.get("weaken_terms") or []],
        }
    return out


def _gate_overrides(
    payload: dict[str, Any],
    *,
    gate_decisions: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    flow = payload.get("flow") if isinstance(payload.get("flow"), dict) else {}
    debug = flow.get("interpretation_debug") if isinstance(flow.get("interpretation_debug"), dict) else {}
    provenance = debug.get("detection_provenance")
    if not isinstance(provenance, dict):
        return []
    decisions = gate_decisions or _gate_decisions(payload)
    overrides: list[dict[str, Any]] = []
    for block, item in sorted(provenance.items()):
        if not isinstance(item, dict):
            continue
        final_source = str(item.get("final_source") or "")
        # "gate_override" only exists in payloads produced before the gate
        # became veto-only; keep matching it so older batches stay reviewable.
        if final_source not in {"gate_override", "llm_rejected_gate_candidate"}:
            continue
        decision = decisions.get(str(block), {})
        overrides.append(
            {
                "block": str(block),
                "llm_detected": bool(item.get("llm_detected")),
                "gate_detected": bool(item.get("gate_detected")),
                "final_source": final_source,
                "gate_reason": item.get("gate_reason") or "",
                "review_queue_reason": str(item.get("review_queue_reason") or ""),
                "support_terms": [str(term) for term in decision.get("support_terms") or []],
                "weaken_terms": [str(term) for term in decision.get("weaken_terms") or []],
            }
        )
    return overrides


def _gate_candidate_blocks(gate_overrides: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(override.get("block") or "")
            for override in gate_overrides
            if override.get("review_queue_reason") == "gate_positive_llm_negative" and override.get("block")
        }
    )


def _material_gate_override_blocks(
    gate_overrides: list[dict[str, Any]],
    components: dict[str, dict[str, Any]],
) -> list[str]:
    material: list[str] = []
    for override in gate_overrides:
        block = str(override.get("block") or "")
        component = components.get(block)
        if not isinstance(component, dict):
            continue
        delta = _number(component.get("score_delta"))
        if delta is not None and abs(delta) >= 4:
            material.append(block)
    return sorted(set(material))


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _average(values: list[Any]) -> float | None:
    numbers = [float(value) for value in values if _number(value) is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 2)


if __name__ == "__main__":
    raise SystemExit(main())
