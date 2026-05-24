#!/usr/bin/env python3
"""Build a review table for Magnetism outputs from existing Brand Audit runs.

This script is intentionally read-only by default. It reuses Brand Audit
snapshots as the shared evidence packet, runs the Magnetism TLDR interpreter,
and writes a Markdown/JSON review artifact for methodological inspection.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import BRAND3_DB_PATH
from src.features.magnetism.extractor import TLDR_KEYS, MagnetismExtractor
from src.storage.sqlite_store import SQLiteStore


OUT_DIR = Path("scratch/magnetism_brand_audit_batch_review")

KNOWN_NOISE_MARKERS = [
    "%ESI_AUDIENCE_SEGMENTATION%",
    "__NEXT_DATA__",
    "Remove contentData",
    "GraphQL API",
    "Product roadmap",
    "vehicle_state",
    "captions settings",
    "seek to live",
    "/bin/bash",
    "rg --files",
]

QUALITY_BLOCKS = ("value_proposition", "mission", "vision")


EVIDENCE_LEAK_MARKERS = [
    "; evidence=",
    "source_type=",
    "dimension=",
    "feature=",
    ".com/news/",
    "/news/",
    "botbeat",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Magnetism TLDR Brand3 over existing Brand Audit snapshots and produce a review table."
    )
    parser.add_argument("--db", default=str(BRAND3_DB_PATH), help="SQLite database path.")
    parser.add_argument("--limit", type=int, default=25, help="Number of latest Brand Audit runs to review.")
    parser.add_argument("--run-id", action="append", type=int, default=[], help="Specific run id. Repeatable.")
    parser.add_argument("--brand", default=None, help="Filter runs by exact brand name.")
    parser.add_argument("--url", default=None, help="Filter runs by exact URL.")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="Directory for Markdown and JSON artifacts.")
    parser.add_argument("--dedupe", action="store_true", help="Keep only the latest run per normalized brand/url pair.")
    args = parser.parse_args()

    store = SQLiteStore(args.db)
    try:
        snapshots = _load_snapshots(store, args)
        if args.dedupe:
            snapshots = _dedupe_snapshots(snapshots)
        rows = _build_rows(snapshots)
    finally:
        store.close()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json_path = out_dir / f"review-{timestamp}.json"
    md_path = out_dir / f"review-{timestamp}.md"
    latest_json = out_dir / "latest.json"
    latest_md = out_dir / "latest.md"

    summary = _build_summary(rows)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db_path": args.db,
        "run_count": len(rows),
        "summary": summary,
        "rows": rows,
    }
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    md_text = _render_markdown(payload)
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    latest_json.write_text(json_text, encoding="utf-8")
    latest_md.write_text(md_text, encoding="utf-8")

    print(f"Wrote {len(rows)} rows")
    print(f"Markdown: {md_path}")
    print(f"JSON: {json_path}")


def _load_snapshots(store: SQLiteStore, args: argparse.Namespace) -> list[dict[str, Any]]:
    run_ids = list(dict.fromkeys(args.run_id))
    if not run_ids:
        runs = store.list_runs(brand_name=args.brand, url=args.url, limit=args.limit)
        run_ids = [int(row["id"]) for row in runs]

    snapshots: list[dict[str, Any]] = []
    for run_id in run_ids:
        snapshot = store.get_run_snapshot(run_id)
        if snapshot:
            snapshots.append(snapshot)
    return snapshots




def _dedupe_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for snapshot in snapshots:
        run = snapshot.get("run") or {}
        key = _snapshot_dedupe_key(snapshot)
        existing = latest_by_key.get(key)
        if existing is None or int((run.get("id") or 0)) > int(((existing.get("run") or {}).get("id") or 0)):
            latest_by_key[key] = snapshot
    return sorted(
        latest_by_key.values(),
        key=lambda item: int(((item.get("run") or {}).get("id") or 0)),
        reverse=True,
    )


def _snapshot_dedupe_key(snapshot: dict[str, Any]) -> tuple[str, str]:
    run = snapshot.get("run") or {}
    brand = str(run.get("brand_name") or "").strip().lower()
    url = str(run.get("url") or "").strip().lower().rstrip("/")
    if url:
        return ("url", url)
    return ("brand", brand)

def _build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def count_by(field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            value = str(row.get(field) or "missing")
            counts[value] = counts.get(value, 0) + 1
        return counts

    group_totals: dict[str, int] = {}
    group_presence: dict[str, int] = {}
    for row in rows:
        groups = ((row.get("evidence_packet") or {}).get("strategic_group_counts") or {})
        if not isinstance(groups, dict):
            continue
        for group, count in groups.items():
            if not count:
                continue
            group_totals[group] = group_totals.get(group, 0) + int(count)
            group_presence[group] = group_presence.get(group, 0) + 1

    missing_group_presence = {
        group: len(rows) - group_presence.get(group, 0)
        for group in ("product_offer", "audience", "outcome", "mission_language", "vision_language")
    }
    flag_counts: dict[str, int] = {}
    for row in rows:
        for flag in row.get("review_flags") or []:
            key = str(flag).split(":", 1)[0]
            flag_counts[key] = flag_counts.get(key, 0) + 1

    block_quality_counts = {
        block: count_by(f"{block}_quality")
        for block in QUALITY_BLOCKS
    }

    return {
        "value_proposition_confidence": count_by("value_proposition_confidence"),
        "mission_confidence": count_by("mission_confidence"),
        "vision_confidence": count_by("vision_confidence"),
        "block_quality": block_quality_counts,
        "strategic_group_totals": dict(sorted(group_totals.items())),
        "strategic_group_presence": dict(sorted(group_presence.items())),
        "missing_group_presence": missing_group_presence,
        "review_flag_counts": dict(sorted(flag_counts.items())),
    }


def _build_rows(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    extractor = MagnetismExtractor(llm=None)
    rows: list[dict[str, Any]] = []
    for snapshot in snapshots:
        result = extractor.extract_from_audit_snapshot(snapshot)
        rows.append(_build_row(snapshot, result))
    return rows


def _build_row(snapshot: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    run = snapshot.get("run") or {}
    tldr = result.get("tldr_brand3") or {}
    layers = result.get("magenta_circle") or {}
    metrics = result.get("metrics") or {}
    packet = result.get("evidence_packet_summary") or {}
    value_block = tldr.get("value_proposition") or {}
    mission_block = tldr.get("mission") or {}
    vision_block = tldr.get("vision") or {}

    detected_layers = [
        layer for layer, value in layers.items() if isinstance(value, dict) and value.get("detected")
    ]
    detected_blocks = [
        block for block in TLDR_KEYS if _block_has_answer(tldr.get(block) or {})
    ]
    review_blocks = [
        block for block in TLDR_KEYS if (tldr.get(block) or {}).get("human_review_recommended")
    ]
    visible_values = _visible_interpretation_values(tldr, layers, result)
    noise_hits = _known_noise_hits(visible_values)
    evidence_leaks = _evidence_leak_hits(
        [
            _block_answer(tldr.get("value_proposition") or {}),
            _block_answer(tldr.get("magnetism") or {}),
            _block_answer(tldr.get("mission") or {}),
            _block_answer(tldr.get("vision") or {}),
        ]
    )
    missing_blocks = [block for block in TLDR_KEYS if block not in detected_blocks]

    review_flags: list[str] = []
    group_counts = packet.get("strategic_group_counts") or {}
    missing_vp_kind: str | None = None
    if "value_proposition" in missing_blocks:
        if not group_counts:
            missing_vp_kind = "no_usable_strategic_evidence"
        elif not group_counts.get("product_offer") and (
            group_counts.get("vision_language") or group_counts.get("personality_tone")
        ):
            missing_vp_kind = "non_offer_brand_signal"
        else:
            missing_vp_kind = "missing_value_proposition"
        review_flags.append(missing_vp_kind)
    if len(detected_layers) <= 2 and missing_vp_kind != "no_usable_strategic_evidence":
        if missing_vp_kind == "non_offer_brand_signal":
            review_flags.append("limited_non_offer_layer_coverage")
        elif group_counts and len([value for value in group_counts.values() if value]) >= 3:
            review_flags.append("limited_observable_layers")
        else:
            review_flags.append("weak_layer_coverage")
    value_gaps = [str(gap).lower() for gap in (value_block.get("counter_evidence") or [])]
    if any("does not clearly name the audience" in gap for gap in value_gaps):
        review_flags.append("value_prop_audience_not_named")
    if any("does not clearly state the outcome" in gap for gap in value_gaps):
        review_flags.append("value_prop_outcome_not_stated")
    mission_missing = "mission" in missing_blocks
    if mission_missing and group_counts.get("product_offer") and not group_counts.get("mission_language"):
        review_flags.append("mission_not_declared")
    if review_blocks:
        if "vision" in review_blocks:
            review_flags.append("interpreted_vision_needs_review")
        if "core_purpose" in review_blocks:
            review_flags.append("purpose_hypothesis_needs_review")
        review_flags.append("human_review_blocks:" + ",".join(review_blocks))
    if noise_hits:
        review_flags.append("known_noise_leak:" + ",".join(noise_hits))
    if evidence_leaks:
        review_flags.append("evidence_format_leak:" + ",".join(evidence_leaks))

    value_quality = _block_quality("value_proposition", value_block, noise_hits, evidence_leaks)
    mission_quality = _block_quality("mission", mission_block, noise_hits, evidence_leaks)
    vision_quality = _block_quality("vision", vision_block, noise_hits, evidence_leaks)

    return {
        "run_id": run.get("id"),
        "brand": run.get("brand_name"),
        "url": run.get("url"),
        "audit_score": run.get("composite_score"),
        "magnetism_score": metrics.get("magnetism_score"),
        "coherence_score": metrics.get("coherence_score"),
        "detected_layers": detected_layers,
        "detected_block_count": len(detected_blocks),
        "missing_blocks": missing_blocks,
        "needs_review_blocks": review_blocks,
        "value_proposition": _block_answer(value_block),
        "value_proposition_confidence": value_block.get("confidence"),
        "value_proposition_quality": value_quality["status"],
        "value_proposition_quality_reasons": value_quality["reasons"],
        "value_proposition_gaps": value_block.get("counter_evidence") or [],
        "magnetism": _block_answer(tldr.get("magnetism") or {}),
        "mission": _block_answer(mission_block),
        "mission_confidence": mission_block.get("confidence"),
        "mission_quality": mission_quality["status"],
        "mission_quality_reasons": mission_quality["reasons"],
        "mission_gaps": mission_block.get("counter_evidence") or [],
        "vision": _block_answer(vision_block),
        "vision_confidence": vision_block.get("confidence"),
        "vision_quality": vision_quality["status"],
        "vision_quality_reasons": vision_quality["reasons"],
        "vision_gaps": vision_block.get("counter_evidence") or [],
        "known_noise_hits": noise_hits,
        "evidence_leak_hits": evidence_leaks,
        "review_flags": review_flags,
        "evidence_packet": {
            "raw_input_count": packet.get("raw_input_count"),
            "evidence_item_count": packet.get("evidence_item_count"),
            "derived_evidence_count": packet.get("derived_evidence_count"),
            "feature_count": packet.get("feature_count"),
            "sources": packet.get("sources"),
            "data_quality": packet.get("data_quality"),
            "strategic_group_counts": packet.get("strategic_group_counts"),
            "strategic_warnings": packet.get("strategic_warnings"),
        },
    }


def _block_has_answer(block: dict[str, Any]) -> bool:
    if block.get("mode") == "not_detected" or block.get("claim_type") == "absent":
        return False
    answer = _block_answer(block)
    return bool(answer and answer != "(no detectado)")


def _block_answer(block: dict[str, Any]) -> str:
    value = block.get("answer")
    if value is None:
        value = block.get("content")
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _block_quality(
    block_name: str,
    block: dict[str, Any],
    noise_hits: list[str] | None = None,
    evidence_leaks: list[str] | None = None,
) -> dict[str, Any]:
    answer = _block_answer(block)
    mode = str(block.get("mode") or "")
    claim_type = str(block.get("claim_type") or "")
    if not answer or mode == "not_detected" or claim_type == "absent":
        return {"status": "missing", "reasons": ["no_answer"]}

    confidence = str(block.get("confidence") or "low")
    reasons: list[str] = []
    if noise_hits:
        reasons.append("visible_noise")
    if evidence_leaks:
        reasons.append("evidence_format_leak")
    if block.get("human_review_recommended"):
        reasons.append("human_review")
    for gap in block.get("counter_evidence") or []:
        reason = _quality_gap_reason(str(gap))
        if reason and reason not in reasons:
            reasons.append(reason)

    if confidence == "high" and not reasons:
        status = "strong"
    elif confidence in {"high", "medium"} and "visible_noise" not in reasons and "evidence_format_leak" not in reasons:
        status = "usable"
    else:
        status = "weak"

    if block_name == "vision" and "human_review" in reasons and status == "strong":
        status = "usable"
    return {"status": status, "reasons": reasons}


def _quality_gap_reason(gap: str) -> str:
    low = gap.lower()
    if "does not clearly name the audience" in low:
        return "missing_audience"
    if "does not clearly state the outcome" in low:
        return "missing_outcome"
    if "multiple offer" in low or "multiple offer signals" in low:
        return "multiple_offers"
    if "not a formal vision" in low:
        return "interpreted_not_declared"
    if "no sufficient public evidence" in low:
        return "insufficient_evidence"
    return "methodological_gap"


def _visible_interpretation_values(
    tldr: dict[str, Any],
    layers: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "tldr": {
            key: {
                "answer": (block or {}).get("answer") or (block or {}).get("content"),
                "reasoning": (block or {}).get("reasoning") or (block or {}).get("rationale"),
                "evidence_used": (block or {}).get("evidence_used") or (block or {}).get("evidence"),
                "counter_evidence": (block or {}).get("counter_evidence"),
            }
            for key, block in tldr.items()
            if isinstance(block, dict)
        },
        "layers": {
            key: {
                "finding": (layer or {}).get("finding") or (layer or {}).get("findings"),
                "evidence": (layer or {}).get("evidence") or (layer or {}).get("evidence_list"),
            }
            for key, layer in layers.items()
            if isinstance(layer, dict)
        },
        "diagnosis": result.get("diagnosis"),
        "system_reading": result.get("system_reading"),
    }


def _known_noise_hits(value: Any) -> list[str]:
    text = json.dumps(value, ensure_ascii=False)
    hits = [marker for marker in KNOWN_NOISE_MARKERS if marker.lower() in text.lower()]
    return sorted(set(hits))


def _evidence_leak_hits(values: list[str]) -> list[str]:
    text = '\n'.join(values)
    hits = [marker for marker in EVIDENCE_LEAK_MARKERS if marker.lower() in text.lower()]
    return sorted(set(hits))

def _render_markdown(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    summary = payload.get("summary") or {}
    lines = [
        "# Magnetism Brand Audit Batch Review",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- db_path: `{payload['db_path']}`",
        f"- run_count: `{payload['run_count']}`",
        "",
        "## Batch Summary",
        "",
        f"- VP confidence: `{_compact_counts(summary.get('value_proposition_confidence'))}`",
        f"- Mission confidence: `{_compact_counts(summary.get('mission_confidence'))}`",
        f"- Vision confidence: `{_compact_counts(summary.get('vision_confidence'))}`",
        f"- Group presence: `{_compact_counts(summary.get('strategic_group_presence'))}`",
        f"- Missing key groups: `{_compact_counts(summary.get('missing_group_presence'))}`",
        f"- Review flags: `{_compact_counts(summary.get('review_flag_counts'))}`",
        f"- VP quality: `{_compact_counts((summary.get('block_quality') or {}).get('value_proposition'))}`",
        f"- Mission quality: `{_compact_counts((summary.get('block_quality') or {}).get('mission'))}`",
        f"- Vision quality: `{_compact_counts((summary.get('block_quality') or {}).get('vision'))}`",
        "",
        "## Rows",
        "",
        "| run | brand | audit | mag | coh | layers | blocks | review flags | VP quality | VP conf | VP gaps | Mission quality | Mission conf | Mission gaps | Vision quality | Vision conf | Vision gaps | value proposition | mission | vision |",
        "|---:|---|---:|---:|---:|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {run_id} | {brand} | {audit_score} | {magnetism_score} | {coherence_score} | {layers} | {blocks}/9 | {flags} | {vp_quality} | {vp_conf} | {vp_gaps} | {mission_quality} | {mission_conf} | {mission_gaps} | {vision_quality} | {vision_conf} | {vision_gaps} | {value} | {mission} | {vision} |".format(
                run_id=row.get("run_id"),
                brand=_md(row.get("brand")),
                audit_score=_num(row.get("audit_score")),
                magnetism_score=_num(row.get("magnetism_score")),
                coherence_score=_num(row.get("coherence_score")),
                layers=_md(", ".join(row.get("detected_layers") or [])),
                blocks=row.get("detected_block_count"),
                flags=_md(", ".join(row.get("review_flags") or []) or "ok"),
                vp_quality=_md(_quality_cell(row, "value_proposition")),
                vp_conf=_md(row.get("value_proposition_confidence")),
                vp_gaps=_md("; ".join(row.get("value_proposition_gaps") or [])),
                mission_quality=_md(_quality_cell(row, "mission")),
                mission_conf=_md(row.get("mission_confidence")),
                mission_gaps=_md("; ".join(row.get("mission_gaps") or [])),
                vision_quality=_md(_quality_cell(row, "vision")),
                vision_conf=_md(row.get("vision_confidence")),
                vision_gaps=_md("; ".join(row.get("vision_gaps") or [])),
                value=_md(row.get("value_proposition")),
                mission=_md(row.get("mission")),
                vision=_md(row.get("vision")),
            )
        )

    lines.extend(["", "## Block Quality Examples", ""])
    for block in QUALITY_BLOCKS:
        lines.extend(_render_quality_examples(rows, block))

    lines.extend(["", "## Evidence Packet Summary", ""])
    for row in rows:
        packet = row.get("evidence_packet") or {}
        lines.append(
            "- run {run_id} · {brand}: raw={raw} evidence_items={items} derived={derived} features={features} groups={groups} sources={sources}".format(
                run_id=row.get("run_id"),
                brand=row.get("brand"),
                raw=packet.get("raw_input_count"),
                items=packet.get("evidence_item_count"),
                derived=packet.get("derived_evidence_count"),
                features=packet.get("feature_count"),
                groups=_compact_counts(packet.get("strategic_group_counts")),
                sources=", ".join(packet.get("sources") or []),
            )
        )
    return "\n".join(lines) + "\n"


def _render_quality_examples(rows: list[dict[str, Any]], block: str, limit: int = 8) -> list[str]:
    title = block.replace("_", " ").title()
    ranked = sorted(
        rows,
        key=lambda row: (
            {"weak": 0, "missing": 1, "usable": 2, "strong": 3}.get(str(row.get(f"{block}_quality")), 4),
            str(row.get("brand") or ""),
        ),
    )[:limit]
    lines = [f"### {title}", "", "| quality | run | brand | confidence | reasons | answer |", "|---|---:|---|---|---|---|"]
    for row in ranked:
        lines.append(
            "| {quality} | {run_id} | {brand} | {confidence} | {reasons} | {answer} |".format(
                quality=_md(row.get(f"{block}_quality")),
                run_id=row.get("run_id"),
                brand=_md(row.get("brand")),
                confidence=_md(row.get(f"{block}_confidence")),
                reasons=_md(", ".join(row.get(f"{block}_quality_reasons") or [])),
                answer=_md(row.get(block)),
            )
        )
    lines.append("")
    return lines


def _quality_cell(row: dict[str, Any], block: str) -> str:
    quality = str(row.get(f"{block}_quality") or "")
    reasons = row.get(f"{block}_quality_reasons") or []
    if not reasons:
        return quality
    return quality + " (" + ", ".join(str(reason) for reason in reasons[:3]) + ")"


def _num(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def _md(value: Any) -> str:
    text = str(value or "").replace("\n", " ").strip()
    text = text.replace("|", "\\|")
    return text[:180] + ("..." if len(text) > 180 else "")


def _compact_counts(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    return ",".join(f"{key}:{count}" for key, count in value.items() if count)


if __name__ == "__main__":
    main()
