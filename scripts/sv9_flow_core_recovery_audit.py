#!/usr/bin/env python3
"""Audit core component recoveries from full SV9 Flow compare payloads."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CORE_RECOVERY_COMPONENTS = frozenset({"core_purpose", "magnetism", "mission", "value_proposition"})
PRODUCT_BOUND_TERMS = (
    "agency",
    "consulting firm",
    "continuous appsec",
    "financial infrastructure",
    "infrastructure",
    "manages",
    "marketing agency",
    "payments",
    "platform",
    "provide",
    "provides",
    "software",
)
WHY_BEYOND_PRODUCT_TERMS = (
    "beyond the product",
    "why exists",
    "why the company exists",
    "belief",
    "conviction",
    "change the way",
    "make it possible",
    "so that",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("compare_json", nargs="+", help="Full compare payloads with flow.candidate included.")
    parser.add_argument("--component", default="", help="Optional component filter.")
    parser.add_argument("--min-delta", type=int, default=4)
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    parser.add_argument("--markdown-output", default="", help="Optional markdown output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.compare_json]
    report = build_core_recovery_audit(
        payloads,
        sources=args.compare_json,
        component=args.component or None,
        min_delta=args.min_delta,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    markdown = render_markdown(report) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    if args.markdown_output:
        Path(args.markdown_output).write_text(markdown, encoding="utf-8")
    print(markdown, end="")
    return 0


def build_core_recovery_audit(
    payloads: list[dict[str, Any]],
    *,
    sources: list[str] | None = None,
    component: str | None = None,
    min_delta: int = 4,
) -> dict[str, Any]:
    source_list = sources or ["" for _ in payloads]
    components = {component} if component else set(CORE_RECOVERY_COMPONENTS)
    items: list[dict[str, Any]] = []
    for index, payload in enumerate(payloads):
        source = source_list[index] if index < len(source_list) else ""
        for key, comparison in _comparison_components(payload).items():
            if key not in components or not _is_recovery(payload, key, comparison, min_delta=min_delta):
                continue
            items.append(_audit_item(payload, source=source, component=key, comparison=comparison))
    risk_counts = Counter(flag for item in items for flag in item.get("risk_flags") or [])
    return {
        "schema_version": "sv9-flow-core-recovery-audit-v1",
        "item_count": len(items),
        "risk_counts": dict(sorted(risk_counts.items())),
        "items": items,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SV9 Flow Core Recovery Audit",
        "",
        f"- schema: `{report.get('schema_version')}`",
        f"- items: `{report.get('item_count')}`",
    ]
    risk_counts = report.get("risk_counts") or {}
    if risk_counts:
        lines.append("- risk counts: `" + ", ".join(f"{k}:{v}" for k, v in risk_counts.items()) + "`")
    lines.extend(
        [
            "",
            "| brand | component | delta | flow | legacy | risks | refs |",
            "|---|---|---:|---|---|---|---|",
        ]
    )
    for item in report.get("items") or []:
        refs = ", ".join(ref.get("ref", "") for ref in item.get("refs") or [])
        risks = ", ".join(item.get("risk_flags") or [])
        lines.append(
            "| {brand} | {component} | {delta:+} | {flow_status} | {legacy_status} | {risks} | {refs} |".format(
                brand=item.get("brand_name") or "",
                component=item.get("component") or "",
                delta=item.get("score_delta") or 0,
                flow_status=item.get("flow_status") or "",
                legacy_status=item.get("legacy_status") or "",
                risks=risks,
                refs=refs,
            )
        )
    return "\n".join(lines)


def _comparison_components(payload: dict[str, Any]) -> dict[str, Any]:
    comparison = payload.get("comparison") if isinstance(payload.get("comparison"), dict) else {}
    components = comparison.get("components") if isinstance(comparison.get("components"), dict) else {}
    return {str(key): value for key, value in components.items() if isinstance(value, dict)}


def _is_recovery(payload: dict[str, Any], key: str, component: dict[str, Any], *, min_delta: int) -> bool:
    status = component.get("status") if isinstance(component.get("status"), dict) else {}
    delta = _number(component.get("score_delta"))
    legacy_status = status.get("legacy")
    return (
        delta is not None
        and delta >= min_delta
        and status.get("flow") == "scored"
        and (legacy_status == "not_detected" or _legacy_zero_score(payload, key))
    )


def _legacy_zero_score(payload: dict[str, Any], key: str) -> bool:
    legacy = payload.get("legacy_sv9") if isinstance(payload.get("legacy_sv9"), dict) else {}
    components = legacy.get("components") if isinstance(legacy.get("components"), dict) else {}
    component = components.get(key) if isinstance(components.get(key), dict) else {}
    return (
        component.get("status") == "scored"
        and _number(component.get("score")) == 0
        and not component.get("lit_tiles")
    )


def _audit_item(
    payload: dict[str, Any],
    *,
    source: str,
    component: str,
    comparison: dict[str, Any],
) -> dict[str, Any]:
    status = comparison.get("status") if isinstance(comparison.get("status"), dict) else {}
    block = _interpretation_block(payload, component)
    refs = _evidence_refs(payload, component)
    evidence = _evidence_by_ref(payload)
    ref_summaries = [_ref_summary(ref, evidence.get(ref)) for ref in refs]
    content = str(block.get("content") or "")
    rationale = str(block.get("rationale") or "")
    risk_flags = _risk_flags(content=content, rationale=rationale, refs=ref_summaries, block=block)
    sv9_component = _sv9_component(payload, component)
    return {
        "brand_name": payload.get("brand_name"),
        "url": payload.get("url"),
        "source_run_id": payload.get("source_run_id"),
        "source": source,
        "component": component,
        "score_delta": _number(comparison.get("score_delta")),
        "flow_status": status.get("flow"),
        "legacy_status": status.get("legacy"),
        "content": content,
        "rationale": rationale,
        "confidence": block.get("confidence"),
        "detection_provenance": block.get("detection_provenance") or {},
        "lit_tiles": sv9_component.get("lit_tiles") or [],
        "blind_spot_tiles": sv9_component.get("blind_spot_tiles") or [],
        "off_tiles": sv9_component.get("off_tiles") or [],
        "refs": ref_summaries,
        "risk_flags": risk_flags,
    }


def _interpretation_block(payload: dict[str, Any], component: str) -> dict[str, Any]:
    flow = payload.get("flow") if isinstance(payload.get("flow"), dict) else {}
    candidate = flow.get("candidate") if isinstance(flow.get("candidate"), dict) else {}
    interpretation = candidate.get("interpretation") if isinstance(candidate.get("interpretation"), dict) else {}
    blocks = interpretation.get("blocks") if isinstance(interpretation.get("blocks"), dict) else {}
    block = blocks.get(component)
    return block if isinstance(block, dict) else {}


def _evidence_refs(payload: dict[str, Any], component: str) -> list[str]:
    flow = payload.get("flow") if isinstance(payload.get("flow"), dict) else {}
    candidate = flow.get("candidate") if isinstance(flow.get("candidate"), dict) else {}
    interpretation = candidate.get("interpretation") if isinstance(candidate.get("interpretation"), dict) else {}
    evidence_refs = interpretation.get("evidence_refs") if isinstance(interpretation.get("evidence_refs"), dict) else {}
    return [str(ref) for ref in evidence_refs.get(component) or []]


def _evidence_by_ref(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    flow = payload.get("flow") if isinstance(payload.get("flow"), dict) else {}
    candidate = flow.get("candidate") if isinstance(flow.get("candidate"), dict) else {}
    pack = candidate.get("evidence_pack") if isinstance(candidate.get("evidence_pack"), dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for item in pack.get("evidence") or []:
        if isinstance(item, dict) and item.get("ref"):
            out[str(item["ref"])] = item
    return out


def _ref_summary(ref: str, evidence: dict[str, Any] | None) -> dict[str, Any]:
    evidence = evidence or {}
    metadata = evidence.get("metadata") if isinstance(evidence.get("metadata"), dict) else {}
    return {
        "ref": ref,
        "source": evidence.get("source"),
        "evidence_type": evidence.get("evidence_type"),
        "source_class": metadata.get("source_class"),
        "url": evidence.get("url"),
        "content_excerpt": str(evidence.get("content") or "")[:500],
    }


def _sv9_component(payload: dict[str, Any], component: str) -> dict[str, Any]:
    sv9 = payload.get("sv9") if isinstance(payload.get("sv9"), dict) else {}
    components = sv9.get("components") if isinstance(sv9.get("components"), dict) else {}
    value = components.get(component)
    return value if isinstance(value, dict) else {}


def _risk_flags(
    *,
    content: str,
    rationale: str,
    refs: list[dict[str, Any]],
    block: dict[str, Any],
) -> list[str]:
    text = f"{content} {rationale}".lower()
    flags: list[str] = []
    if not block:
        flags.append("missing_full_candidate")
    if any(ref.get("source_class") in {"external_proof", "other"} for ref in refs):
        flags.append("uses_non_owned_refs")
    owned_refs = [ref for ref in refs if ref.get("source_class") == "owned_copy"]
    if not owned_refs:
        flags.append("no_owned_copy_ref")
    if any(term in text for term in PRODUCT_BOUND_TERMS):
        flags.append("product_or_offer_bound_language")
    if not any(term in text for term in WHY_BEYOND_PRODUCT_TERMS):
        flags.append("no_explicit_why_beyond_product_language")
    if len({ref.get("content_excerpt") for ref in owned_refs}) < len(owned_refs):
        flags.append("duplicate_owned_copy_refs")
    return flags


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


if __name__ == "__main__":
    raise SystemExit(main())
