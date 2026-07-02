#!/usr/bin/env python3
"""Build an offline SV9 Flow calibration packet from existing compare payloads."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sv9_flow_sv9_batch_report import build_batch_report, render_markdown_report

SV9_FLOW_CALIBRATION_LOOP_VERSION = "sv9-flow-calibration-loop-v1"
CORE_COMPONENTS = frozenset({"mission", "value_proposition", "core_purpose", "magnetism"})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("compare_json", nargs="+", help="JSON files from scripts/sv9_flow_sv9_shadow_eval.py")
    parser.add_argument("--cohort-name", default="adhoc", help="Name for this calibration cohort")
    parser.add_argument("--output-dir", required=True, help="Directory where loop artifacts will be written")
    parser.add_argument("--budget-usd", type=float, default=None, help="Optional target budget for this loop")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.compare_json]
    packet = build_calibration_packet(
        payloads,
        sources=args.compare_json,
        cohort_name=args.cohort_name,
        budget_usd=args.budget_usd,
    )
    output_dir = Path(args.output_dir)
    write_calibration_packet(packet, output_dir)
    print(render_loop_summary(packet))
    return 0


def build_calibration_packet(
    payloads: list[dict[str, Any]],
    *,
    sources: list[str] | None = None,
    cohort_name: str = "adhoc",
    budget_usd: float | None = None,
) -> dict[str, Any]:
    source_list = sources or ["" for _ in payloads]
    batch_report = build_batch_report(payloads, sources=source_list)
    cohort_manifest = build_cohort_manifest(
        payloads,
        batch_report=batch_report,
        sources=source_list,
        cohort_name=cohort_name,
    )
    review_queue = build_review_queue(batch_report)
    cost_observation = build_cost_observation(
        payloads,
        batch_report=batch_report,
        cohort_manifest=cohort_manifest,
        budget_usd=budget_usd,
    )
    return {
        "schema_version": SV9_FLOW_CALIBRATION_LOOP_VERSION,
        "created_at": _utc_now(),
        "cohort_name": cohort_name,
        "batch_report": batch_report,
        "cohort_manifest": cohort_manifest,
        "review_queue": review_queue,
        "cost_observation": cost_observation,
    }


def write_calibration_packet(packet: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "cohort_manifest.json": packet["cohort_manifest"],
        "cost_observation.json": packet["cost_observation"],
        "batch_report.json": packet["batch_report"],
        "review_queue.json": packet["review_queue"],
    }
    for filename, payload in artifacts.items():
        (output_dir / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (output_dir / "batch_report.md").write_text(
        render_markdown_report(packet["batch_report"]) + "\n",
        encoding="utf-8",
    )
    (output_dir / "review_queue.md").write_text(
        render_review_queue_markdown(packet["review_queue"]) + "\n",
        encoding="utf-8",
    )
    (output_dir / "loop_summary.md").write_text(
        render_loop_summary(packet) + "\n",
        encoding="utf-8",
    )


def build_cohort_manifest(
    payloads: list[dict[str, Any]],
    *,
    batch_report: dict[str, Any],
    sources: list[str],
    cohort_name: str,
) -> dict[str, Any]:
    runs_by_source = {str(run.get("source") or ""): run for run in batch_report.get("runs") or []}
    runs_by_id = {str(run.get("source_run_id") or ""): run for run in batch_report.get("runs") or []}
    entries: list[dict[str, Any]] = []
    for index, payload in enumerate(payloads):
        source = sources[index] if index < len(sources) else ""
        run = runs_by_source.get(source) or runs_by_id.get(str(payload.get("source_run_id") or "")) or {}
        entries.append(
            {
                "brand_name": payload.get("brand_name"),
                "url": payload.get("url"),
                "source_run_id": payload.get("source_run_id"),
                "source": source,
                "assessment": run.get("assessment"),
                "assessment_kind": run.get("assessment_kind"),
                "score_delta": run.get("score_delta"),
                "risk_tags": _risk_tags(payload, run),
                "visual_acquisition_present": bool(payload.get("visual_acquisition_present")),
                "flow_reliability_status": ((payload.get("sv9") or {}).get("reliability_status")),
                "legacy_reliability_status": ((payload.get("legacy_sv9") or {}).get("reliability_status")),
            }
        )
    return {
        "schema_version": f"{SV9_FLOW_CALIBRATION_LOOP_VERSION}.cohort_manifest",
        "created_at": _utc_now(),
        "cohort_name": cohort_name,
        "run_count": len(entries),
        "entries": entries,
        "risk_tag_counts": dict(Counter(tag for entry in entries for tag in entry.get("risk_tags") or [])),
    }


def build_cost_observation(
    payloads: list[dict[str, Any]],
    *,
    batch_report: dict[str, Any],
    cohort_manifest: dict[str, Any],
    budget_usd: float | None,
) -> dict[str, Any]:
    run_count = len(payloads)
    full_payloads = sum(1 for payload in payloads if isinstance((payload.get("flow") or {}).get("candidate"), dict))
    compare_legacy_runs = sum(1 for payload in payloads if isinstance(payload.get("legacy_sv9"), dict))
    estimated_calls = {
        "flow_interpretation_per_block": run_count * 9,
        "flow_sv9_evaluator_components": run_count * 10,
        "legacy_sv9_evaluator_components": compare_legacy_runs * 10,
    }
    estimated_calls["total_upper_bound_without_cache"] = sum(estimated_calls.values())
    observed_usage = _observed_llm_usage(payloads)
    usage_available = observed_usage["payload_count"] > 0
    return {
        "schema_version": f"{SV9_FLOW_CALIBRATION_LOOP_VERSION}.cost_observation",
        "created_at": _utc_now(),
        "run_count": run_count,
        "budget_usd": budget_usd,
        "budget_enforcement": "not_enforced_usage_unobservable" if budget_usd is not None else "not_requested",
        "usage_metadata_available": bool(observed_usage["usage_metadata_available"]),
        "cost_estimate_available": False,
        "cost_observability": "observed_call_count" if usage_available else "call_count_estimate_only",
        "observed_llm_usage": observed_usage,
        "estimated_llm_calls": estimated_calls,
        "cache_observability": {
            "available": usage_available,
            "reason": (
                "compare payloads persist LLMAnalyzer cache counters"
                if usage_available
                else "compare payloads do not persist LLMAnalyzer cache_hits/cache_misses/cache_writes"
            ),
        },
        "full_payloads": full_payloads,
        "compare_legacy_runs": compare_legacy_runs,
        "assessment_summary": (batch_report.get("summary") or {}),
        "risk_tag_counts": cohort_manifest.get("risk_tag_counts") or {},
        "notes": [
            "This packet does not execute new LLM calls.",
            (
                "Provider token usage is present in llm_usage observations."
                if observed_usage["usage_metadata_available"]
                else "Provider token usage is not exposed by the observed payloads."
            ),
            (
                "Observed call counts come from payload llm_usage."
                if usage_available
                else "Call counts are upper-bound planning estimates before persistent cache effects."
            ),
        ],
    }


def build_review_queue(batch_report: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for run in batch_report.get("runs") or []:
        if not isinstance(run, dict):
            continue
        priority, reason = _priority_for_run(run)
        if priority == "P4":
            continue
        items.append(
            {
                "priority": priority,
                "priority_reason": reason,
                "brand_name": run.get("brand_name"),
                "url": run.get("url"),
                "source_run_id": run.get("source_run_id"),
                "assessment": run.get("assessment"),
                "assessment_kind": run.get("assessment_kind"),
                "score_delta": run.get("score_delta"),
                "assessment_reasons": run.get("assessment_reasons") or [],
                "component_focus": _component_focus(run),
                "gate_overrides": run.get("gate_overrides") or [],
                "recommended_next_step": _recommended_next_step(run, priority),
            }
        )
    items.sort(key=lambda item: (item["priority"], str(item.get("brand_name") or "")))
    return {
        "schema_version": f"{SV9_FLOW_CALIBRATION_LOOP_VERSION}.review_queue",
        "created_at": _utc_now(),
        "item_count": len(items),
        "priority_counts": dict(Counter(item["priority"] for item in items)),
        "items": items,
    }


def _observed_llm_usage(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "payload_count": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "cache_writes": 0,
        "provider_calls": 0,
        "usage_metadata_available": False,
    }
    roles: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        usage = payload.get("llm_usage") if isinstance(payload, dict) else None
        if not isinstance(usage, dict):
            continue
        role_payloads = usage.get("roles") if isinstance(usage.get("roles"), dict) else {}
        totals["payload_count"] += 1
        for role, role_usage in role_payloads.items():
            if not isinstance(role_usage, dict):
                continue
            entry = roles.setdefault(
                str(role),
                {
                    "cache_hits": 0,
                    "cache_misses": 0,
                    "cache_writes": 0,
                    "provider_calls": 0,
                    "usage_metadata_available": False,
                },
            )
            for key in ("cache_hits", "cache_misses", "cache_writes", "provider_calls"):
                value = int(role_usage.get(key) or 0)
                entry[key] += value
                totals[key] += value
            if role_usage.get("usage_metadata_available"):
                entry["usage_metadata_available"] = True
                totals["usage_metadata_available"] = True
    return {**totals, "roles": roles}


def render_review_queue_markdown(review_queue: dict[str, Any]) -> str:
    lines = [
        "# SV9 Flow Calibration Review Queue",
        "",
        f"- schema: `{review_queue.get('schema_version')}`",
        f"- items: `{review_queue.get('item_count', 0)}`",
        "- priority counts: `"
        + ", ".join(f"{key}:{value}" for key, value in sorted((review_queue.get("priority_counts") or {}).items()))
        + "`",
        "",
        "| priority | brand | delta | kind | focus | next step |",
        "|---|---|---:|---|---|---|",
    ]
    for item in review_queue.get("items") or []:
        lines.append(
            "| {priority} | {brand} | {delta:+} | {kind} | {focus} | {next} |".format(
                priority=item.get("priority"),
                brand=_md_cell(item.get("brand_name")),
                delta=item.get("score_delta") or 0,
                kind=_md_cell(item.get("assessment_kind")),
                focus=_md_cell(", ".join(item.get("component_focus") or []) or "-"),
                next=_md_cell(item.get("recommended_next_step")),
            )
        )
    return "\n".join(lines).rstrip()


def render_loop_summary(packet: dict[str, Any]) -> str:
    batch_summary = (packet.get("batch_report") or {}).get("summary") or {}
    cost = packet.get("cost_observation") or {}
    review = packet.get("review_queue") or {}
    lines = [
        "# SV9 Flow Calibration Loop Summary",
        "",
        f"- cohort: `{packet.get('cohort_name')}`",
        f"- runs: `{(packet.get('batch_report') or {}).get('run_count')}`",
        f"- acceptable: `{batch_summary.get('acceptable', 0)}`",
        f"- review: `{batch_summary.get('review', 0)}`",
        f"- blocker: `{batch_summary.get('blocker', 0)}`",
        f"- review queue items: `{review.get('item_count', 0)}`",
        f"- cost observability: `{cost.get('cost_observability')}`",
        f"- estimated llm calls upper bound: `{(cost.get('estimated_llm_calls') or {}).get('total_upper_bound_without_cache')}`",
        "",
        "## Status",
        "",
        _loop_status(batch_summary, review, cost),
    ]
    return "\n".join(lines).rstrip()


def _priority_for_run(run: dict[str, Any]) -> tuple[str, str]:
    reasons = [str(reason) for reason in run.get("assessment_reasons") or []]
    components = run.get("components") if isinstance(run.get("components"), dict) else {}
    if run.get("flow_not_evaluated") or any(
        component.get("flow_status") == "not_evaluated"
        for component in components.values()
        if isinstance(component, dict)
    ):
        return "P0", "flow_component_not_evaluated"
    if run.get("flow_reliability_status") == "broken":
        return "P0", "flow_reliability_broken"
    if run.get("assessment") == "blocker":
        return "P0", "blocker_assessment"
    if run.get("score_delta") is not None and run.get("score_delta") < -8:
        return "P1", "negative_total_delta_lt_minus_8"
    if _negative_core_component_delta(components):
        return "P1", "negative_core_component_delta_lte_minus_4"
    if any(reason.startswith("positive_core_recovery_review:") for reason in reasons):
        return "P2", "positive_core_recovery"
    if any(reason == "positive_score_delta_gt_12" for reason in reasons):
        return "P3", "positive_legacy_delta_review"
    if any(reason.startswith("component_delta_gte_4:") for reason in reasons):
        focus = set(_component_focus(run))
        if focus & {"magnetism", "core_purpose"}:
            return "P2", "policy_review_core_or_magnetism"
        return "P2", "policy_review_component_delta"
    if any(reason.startswith("gate_override_review:") for reason in reasons):
        return "P2", "material_gate_override"
    if any(reason.startswith("gate_candidate_review:") for reason in reasons):
        return "P3", "gate_positive_llm_negative_candidate"
    if run.get("assessment") == "review":
        return "P3", "remaining_review"
    return "P4", "acceptable_spot_check"


def _component_focus(run: dict[str, Any]) -> list[str]:
    focus: set[str] = set()
    for reason in run.get("assessment_reasons") or []:
        text = str(reason)
        if ":" not in text:
            continue
        prefix, values = text.split(":", 1)
        if prefix in {
            "component_delta_gte_4",
            "blocking_not_detected_added",
            "review_not_detected_added",
            "gate_override_review",
            "gate_candidate_review",
            "flow_not_evaluated",
            "positive_core_recovery_review",
        }:
            focus.update(item for item in values.split(",") if item)
    if not focus and run.get("score_delta") is not None:
        focus.update(_large_delta_components(run.get("components") or {}))
    return sorted(focus)


def _large_delta_components(components: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key, component in components.items():
        if not isinstance(component, dict):
            continue
        delta = _number(component.get("score_delta"))
        if delta is not None and abs(delta) >= 4:
            out.append(str(key))
    return out


def _negative_core_component_delta(components: dict[str, Any]) -> bool:
    for key, component in components.items():
        if key not in CORE_COMPONENTS or not isinstance(component, dict):
            continue
        delta = _number(component.get("score_delta"))
        if delta is not None and delta <= -4:
            return True
    return False


def _recommended_next_step(run: dict[str, Any], priority: str) -> str:
    focus = set(_component_focus(run))
    if priority == "P0":
        return "fix technical contract before more calibration"
    if priority == "P1":
        return "full audit evidence refs and tile profile before changing rules"
    if any(str(reason).startswith("positive_core_recovery_review:") for reason in run.get("assessment_reasons") or []):
        return "verify recovered core component against source refs before promotion"
    if any(str(reason).startswith("gate_candidate_review:") for reason in run.get("assessment_reasons") or []):
        return "confirm the LLM rejection of the gate candidate against source refs"
    if focus & {"magnetism", "core_purpose"}:
        return "inspect full audit; only propose rule if repeated across brands"
    if any(str(reason).startswith("gate_override_review:") for reason in run.get("assessment_reasons") or []):
        return "verify gate override against source refs before changing thresholds"
    if run.get("assessment_kind") == "legacy_delta_review":
        return "compare against golden subset or human judgement"
    return "manual review if cohort threshold remains high"


def _risk_tags(payload: dict[str, Any], run: dict[str, Any]) -> list[str]:
    tags: set[str] = set()
    flow = payload.get("sv9") if isinstance(payload.get("sv9"), dict) else {}
    legacy = payload.get("legacy_sv9") if isinstance(payload.get("legacy_sv9"), dict) else {}
    comparison = payload.get("comparison") if isinstance(payload.get("comparison"), dict) else {}
    if payload.get("visual_acquisition_present"):
        tags.add("visual_acquisition_present")
    else:
        tags.add("visual_acquisition_absent")
    for block in flow.get("not_detected") or []:
        tags.add(f"flow_not_detected:{block}")
    for block in comparison.get("not_detected_added") or []:
        tags.add(f"not_detected_added:{block}")
    for block in comparison.get("not_detected_removed") or []:
        tags.add(f"not_detected_removed:{block}")
    if flow.get("reliability_status") == "broken" or flow.get("not_evaluated"):
        tags.add("technical_broken_or_not_evaluated")
    if run.get("assessment_kind"):
        tags.add(f"assessment_kind:{run.get('assessment_kind')}")
    for override in run.get("gate_overrides") or []:
        if not isinstance(override, dict) or not override.get("block"):
            continue
        tags.add(f"gate_override:{override.get('block')}")
        if override.get("review_queue_reason") == "gate_positive_llm_negative":
            tags.add(f"gate_candidate:{override.get('block')}")
    if run.get("score_delta") is not None:
        delta = _number(run.get("score_delta")) or 0
        if delta > 12:
            tags.add("positive_delta_gt_12")
        elif delta < -8:
            tags.add("negative_delta_lt_minus_8")
    if legacy.get("not_detected"):
        tags.add("legacy_has_not_detected")
    return sorted(tags)


def _loop_status(batch_summary: dict[str, Any], review_queue: dict[str, Any], cost: dict[str, Any]) -> str:
    if batch_summary.get("blocker", 0):
        return "Not ready for expanded batch: blockers remain."
    priority_counts = review_queue.get("priority_counts") or {}
    if priority_counts.get("P0", 0):
        return "Not ready for expanded batch: technical P0 review items remain."
    if cost.get("cost_observability") == "observed_call_count":
        return "Ready for controlled expanded batch with observed call/cache accounting."
    return "Ready for controlled expanded batch if cost instrumentation is accepted as estimate-only."


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _md_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
