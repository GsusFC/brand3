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
from src.reports.vertical_signals import VERTICAL_SIGNAL_PROFILES, VerticalSignalProfile
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

QUALITY_BLOCKS = tuple(TLDR_KEYS)


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
    page_role_presence: dict[str, int] = {}
    missing_page_role_counts: dict[str, int] = {}
    failure_cause_counts: dict[str, int] = {}
    for row in rows:
        packet = row.get("evidence_packet") or {}
        groups = packet.get("strategic_group_counts") or {}
        if not isinstance(groups, dict):
            continue
        for group, count in groups.items():
            if not count:
                continue
            group_totals[group] = group_totals.get(group, 0) + int(count)
            group_presence[group] = group_presence.get(group, 0) + 1
        extraction_report = packet.get("extraction_quality_report") or {}
        for role in extraction_report.get("owned_page_roles") or []:
            page_role_presence[str(role)] = page_role_presence.get(str(role), 0) + 1
        for role in extraction_report.get("missing_core_roles") or []:
            missing_page_role_counts[str(role)] = missing_page_role_counts.get(str(role), 0) + 1
        cause = extraction_report.get("likely_failure_cause")
        if cause:
            failure_cause_counts[str(cause)] = failure_cause_counts.get(str(cause), 0) + 1

    missing_group_presence = {
        group: len(rows) - group_presence.get(group, 0)
        for group in ("product_offer", "audience", "outcome", "mission_language", "vision_language")
    }
    flag_counts: dict[str, int] = {}
    vertical_profile_counts: dict[str, dict[str, int]] = {}
    for row in rows:
        for flag in row.get("review_flags") or []:
            key = str(flag).split(":", 1)[0]
            flag_counts[key] = flag_counts.get(key, 0) + 1
        for impact in row.get("vertical_profile_impact") or []:
            profile = str(impact.get("profile") or "unknown")
            profile_counts = vertical_profile_counts.setdefault(
                profile,
                {
                    "rows": 0,
                    "rows_with_review_flags": 0,
                    "strong_value_proposition": 0,
                    "usable_attributes": 0,
                    "usable_values": 0,
                },
            )
            profile_counts["rows"] += 1
            if row.get("review_flags"):
                profile_counts["rows_with_review_flags"] += 1
            if row.get("value_proposition_quality") == "strong":
                profile_counts["strong_value_proposition"] += 1
            if row.get("attributes_quality") in {"strong", "usable"}:
                profile_counts["usable_attributes"] += 1
            if row.get("values_quality") in {"strong", "usable"}:
                profile_counts["usable_values"] += 1

    block_quality_counts = {
        block: count_by(f"{block}_quality")
        for block in QUALITY_BLOCKS
    }
    diagnosis_counts = count_by("extraction_diagnosis")

    return {
        "value_proposition_confidence": count_by("value_proposition_confidence"),
        "mission_confidence": count_by("mission_confidence"),
        "vision_confidence": count_by("vision_confidence"),
        "canonical_evidence_quality": count_by("canonical_evidence_quality"),
        "extraction_diagnosis": diagnosis_counts,
        "owned_page_role_presence": dict(sorted(page_role_presence.items())),
        "missing_core_page_roles": dict(sorted(missing_page_role_counts.items())),
        "extraction_failure_causes": dict(sorted(failure_cause_counts.items())),
        "proof_support_status": count_by("proof_support_status"),
        "credibility_support_status": count_by("credibility_support_status"),
        "proof_support_total": sum(int(row.get("proof_support_count") or 0) for row in rows),
        "block_quality": block_quality_counts,
        "strategic_group_totals": dict(sorted(group_totals.items())),
        "strategic_group_presence": dict(sorted(group_presence.items())),
        "missing_group_presence": missing_group_presence,
        "review_flag_counts": dict(sorted(flag_counts.items())),
        "vertical_profile_impact": dict(sorted(vertical_profile_counts.items())),
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
    system_reading = result.get("system_reading") or {}
    proof_support = packet.get("proof_support") or {}
    credibility_support = system_reading.get("credibility_support") or {}
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
        [_block_answer(tldr.get(block) or {}) for block in TLDR_KEYS]
    )
    missing_blocks = [block for block in TLDR_KEYS if block not in detected_blocks]

    review_flags: list[str] = []
    group_counts = packet.get("strategic_group_counts") or {}
    extraction_quality_report = packet.get("extraction_quality_report") or {}
    source_counts = packet.get("strategic_source_counts") or {}
    rejected_reason_counts = packet.get("strategic_rejected_reason_counts") or {}
    evidence_quality = packet.get("evidence_quality") or {}
    extraction_diagnosis = _extraction_diagnosis(
        packet=packet,
        group_counts=group_counts,
        source_counts=source_counts,
        rejected_reason_counts=rejected_reason_counts,
        evidence_quality=evidence_quality,
    )
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

    block_quality = {
        block: _block_quality(block, tldr.get(block) or {}, noise_hits, evidence_leaks)
        for block in TLDR_KEYS
    }
    block_fields: dict[str, Any] = {}
    for block in TLDR_KEYS:
        tldr_block = tldr.get(block) or {}
        quality = block_quality[block]
        block_fields[block] = _block_answer(tldr_block)
        block_fields[f"{block}_confidence"] = tldr_block.get("confidence")
        block_fields[f"{block}_quality"] = quality["status"]
        block_fields[f"{block}_quality_reasons"] = quality["reasons"]
        block_fields[f"{block}_gaps"] = tldr_block.get("counter_evidence") or []

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
        "canonical_evidence_quality": evidence_quality.get("status") or "missing",
        "canonical_evidence_quality_reasons": evidence_quality.get("reasons") or [],
        "extraction_diagnosis": extraction_diagnosis["status"],
        "extraction_diagnosis_reasons": extraction_diagnosis["reasons"],
        "owned_page_roles": extraction_quality_report.get("owned_page_roles") or [],
        "missing_core_page_roles": extraction_quality_report.get("missing_core_roles") or [],
        "extraction_failure_cause": extraction_quality_report.get("likely_failure_cause"),
        "proof_support_status": proof_support.get("status") or "not_detected",
        "proof_support_count": int(proof_support.get("count") or 0),
        "credibility_support_status": credibility_support.get("status") or "not_detected",
        "credibility_support_count": int(credibility_support.get("count") or 0),
        "credibility_support_evidence": credibility_support.get("evidence") or [],
        **block_fields,
        "block_quality": block_quality,
        "vertical_profile_impact": _vertical_profile_impact(result, tldr, layers),
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
            "evidence_quality": evidence_quality,
            "extraction_quality_report": extraction_quality_report,
            "extraction_diagnosis": extraction_diagnosis,
            "strategic_group_counts": packet.get("strategic_group_counts"),
            "strategic_source_counts": source_counts,
            "strategic_rejected_reason_counts": rejected_reason_counts,
            "strategic_warnings": packet.get("strategic_warnings"),
            "proof_support": proof_support,
        },
    }


def _extraction_diagnosis(
    *,
    packet: dict[str, Any],
    group_counts: dict[str, Any],
    source_counts: dict[str, Any],
    rejected_reason_counts: dict[str, Any],
    evidence_quality: dict[str, Any],
) -> dict[str, Any]:
    raw_input_count = int(packet.get("raw_input_count") or 0)
    evidence_item_count = int(packet.get("evidence_item_count") or 0)
    feature_count = int(packet.get("feature_count") or 0)
    rejected_count = int(packet.get("strategic_rejected_count") or 0)
    usable_group_count = len([value for value in group_counts.values() if value])
    owned_source_count = sum(
        int(source_counts.get(source_type) or 0)
        for source_type in ("owned_raw", "owned", "social")
    )
    context_source_count = sum(
        int(source_counts.get(source_type) or 0)
        for source_type in ("encyclopedic", "news", "review", "other", "changelog")
    )
    evidence_status = str(evidence_quality.get("status") or "missing")
    missing_groups = set(evidence_quality.get("missing_key_groups") or [])

    reasons: list[str] = []
    if raw_input_count <= 0:
        reasons.append("no_raw_inputs")
    if evidence_item_count <= 0 and feature_count <= 0:
        reasons.append("no_persisted_feature_evidence")
    if usable_group_count <= 0:
        reasons.append("no_strategic_groups")
    if owned_source_count <= 0:
        reasons.append("no_owned_evidence")
    if context_source_count > owned_source_count and owned_source_count <= 1:
        reasons.append("third_party_heavy")
    if rejected_count >= 20 and usable_group_count <= 2:
        reasons.append("many_rejections_low_signal")
    for group in ("product_offer", "audience", "outcome"):
        if group in missing_groups:
            reasons.append(f"missing_{group}")

    if "no_raw_inputs" in reasons or "no_strategic_groups" in reasons:
        status = "capture_gap"
    elif evidence_status == "strong":
        status = "strong"
    elif evidence_status == "usable":
        status = "usable"
    elif "third_party_heavy" in reasons:
        status = "third_party_heavy"
    elif "many_rejections_low_signal" in reasons:
        status = "selection_gap"
    else:
        status = "brand_sparse"

    top_rejected_reasons = sorted(
        rejected_reason_counts.items(),
        key=lambda item: (-int(item[1] or 0), str(item[0])),
    )[:5]

    return {
        "status": status,
        "reasons": reasons,
        "raw_input_count": raw_input_count,
        "evidence_item_count": evidence_item_count,
        "feature_count": feature_count,
        "owned_source_count": owned_source_count,
        "context_source_count": context_source_count,
        "usable_group_count": usable_group_count,
        "top_rejected_reasons": [
            {"reason": str(reason), "count": int(count or 0)}
            for reason, count in top_rejected_reasons
        ],
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


def _vertical_profile_impact(
    result: dict[str, Any],
    tldr: dict[str, Any],
    layers: dict[str, Any],
) -> list[dict[str, Any]]:
    strategic_packet = result.get("strategic_evidence_packet")
    if not isinstance(strategic_packet, dict):
        strategic_packet = {}
    impacts: list[dict[str, Any]] = []
    for profile in VERTICAL_SIGNAL_PROFILES:
        group_matches = _profile_group_matches(profile, strategic_packet)
        layer_matches = _profile_layer_matches(profile, layers)
        term_matches = _profile_term_matches(profile, tldr) if group_matches or layer_matches else {}
        if not group_matches and not layer_matches and not term_matches:
            continue
        impacts.append(
            {
                "profile": profile.key,
                "matched_groups": group_matches,
                "matched_layers": layer_matches,
                "matched_terms": term_matches,
                "touched_blocks": _profile_touched_blocks(group_matches, layer_matches, term_matches),
            }
        )
    return impacts


def _profile_group_matches(
    profile: VerticalSignalProfile,
    strategic_packet: dict[str, Any],
) -> dict[str, int]:
    groups = strategic_packet.get("groups") if isinstance(strategic_packet, dict) else {}
    if not isinstance(groups, dict):
        return {}
    matches: dict[str, int] = {}
    for group, keywords in profile.group_keywords.items():
        count = 0
        for item in groups.get(group) or []:
            if isinstance(item, dict) and _contains_any(str(item.get("text") or ""), keywords):
                count += 1
        if count:
            matches[group] = count
    return matches


def _profile_layer_matches(
    profile: VerticalSignalProfile,
    layers: dict[str, Any],
) -> dict[str, int]:
    matches: dict[str, int] = {}
    for layer_key, keywords in profile.layer_keywords.items():
        layer = layers.get(layer_key) or {}
        if not isinstance(layer, dict):
            continue
        text = " ".join(
            str(layer.get(field) or "")
            for field in ("finding", "findings", "evidence", "evidence_list")
        )
        if _contains_any(text, keywords):
            matches[layer_key] = 1
    return matches


def _profile_term_matches(
    profile: VerticalSignalProfile,
    tldr: dict[str, Any],
) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for block in ("attributes", "values"):
        text = _block_answer(tldr.get(block) or {})
        terms = [
            term
            for term in profile.term_markers.get(block, {})
            if _contains_any(text, (term,))
        ]
        if terms:
            matches[block] = terms
    return matches


def _profile_touched_blocks(
    group_matches: dict[str, int],
    layer_matches: dict[str, int],
    term_matches: dict[str, list[str]],
) -> list[str]:
    blocks: list[str] = []
    if "product_offer" in group_matches or "outcome" in group_matches or "netspace" in layer_matches:
        blocks.append("value_proposition")
    if "mission_language" in group_matches or "tactispace" in layer_matches:
        blocks.append("mission")
    if "attributes" in term_matches:
        blocks.append("attributes")
    if "values_language" in group_matches or "ambientspace" in layer_matches or "values" in term_matches:
        blocks.append("values")
    return blocks


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    low = str(text or "").lower()
    return any(keyword.lower() in low for keyword in keywords)


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
        f"- Canonical evidence quality: `{_compact_counts(summary.get('canonical_evidence_quality'))}`",
        f"- Extraction diagnosis: `{_compact_counts(summary.get('extraction_diagnosis'))}`",
        f"- Owned page roles: `{_compact_counts(summary.get('owned_page_role_presence'))}`",
        f"- Missing core page roles: `{_compact_counts(summary.get('missing_core_page_roles'))}`",
        f"- Extraction failure causes: `{_compact_counts(summary.get('extraction_failure_causes'))}`",
        f"- Proof support: `{_compact_counts(summary.get('proof_support_status'))}` · total_proof_points=`{summary.get('proof_support_total') or 0}`",
        f"- Credibility support: `{_compact_counts(summary.get('credibility_support_status'))}`",
        f"- Group presence: `{_compact_counts(summary.get('strategic_group_presence'))}`",
        f"- Missing key groups: `{_compact_counts(summary.get('missing_group_presence'))}`",
        f"- Review flags: `{_compact_counts(summary.get('review_flag_counts'))}`",
        f"- Vertical profile impact: `{_compact_nested_counts(summary.get('vertical_profile_impact'))}`",
        f"- VP quality: `{_compact_counts((summary.get('block_quality') or {}).get('value_proposition'))}`",
        f"- Mission quality: `{_compact_counts((summary.get('block_quality') or {}).get('mission'))}`",
        f"- Vision quality: `{_compact_counts((summary.get('block_quality') or {}).get('vision'))}`",
        f"- All TLDR block quality: `{_compact_block_quality(summary.get('block_quality'))}`",
        "",
        "## Rows",
        "",
        "| run | brand | audit | mag | coh | evidence quality | extraction diagnosis | proof | page roles | missing pages | layers | blocks | review flags | vertical profiles | VP quality | VP conf | VP gaps | Mission quality | Mission conf | Mission gaps | Vision quality | Vision conf | Vision gaps | value proposition | mission | vision |",
        "|---:|---|---:|---:|---:|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {run_id} | {brand} | {audit_score} | {magnetism_score} | {coherence_score} | {evidence_quality} | {extraction_diagnosis} | {proof} | {page_roles} | {missing_pages} | {layers} | {blocks}/9 | {flags} | {vertical_profiles} | {vp_quality} | {vp_conf} | {vp_gaps} | {mission_quality} | {mission_conf} | {mission_gaps} | {vision_quality} | {vision_conf} | {vision_gaps} | {value} | {mission} | {vision} |".format(
                run_id=row.get("run_id"),
                brand=_md(row.get("brand")),
                audit_score=_num(row.get("audit_score")),
                magnetism_score=_num(row.get("magnetism_score")),
                coherence_score=_num(row.get("coherence_score")),
                evidence_quality=_md(_canonical_evidence_quality_cell(row)),
                extraction_diagnosis=_md(_extraction_diagnosis_cell(row)),
                proof=_md(_proof_support_cell(row)),
                page_roles=_md(", ".join(row.get("owned_page_roles") or [])),
                missing_pages=_md(", ".join(row.get("missing_core_page_roles") or [])),
                layers=_md(", ".join(row.get("detected_layers") or [])),
                blocks=row.get("detected_block_count"),
                flags=_md(", ".join(row.get("review_flags") or []) or "ok"),
                vertical_profiles=_md(_vertical_profiles_cell(row)),
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
            "- run {run_id} · {brand}: raw={raw} evidence_items={items} derived={derived} features={features} proof={proof} roles={roles} missing_pages={missing_pages} cause={cause} groups={groups} sources={sources}".format(
                run_id=row.get("run_id"),
                brand=row.get("brand"),
                raw=packet.get("raw_input_count"),
                items=packet.get("evidence_item_count"),
                derived=packet.get("derived_evidence_count"),
                features=packet.get("feature_count"),
                proof=_proof_support_cell(row),
                roles=", ".join((packet.get("extraction_quality_report") or {}).get("owned_page_roles") or []),
                missing_pages=", ".join((packet.get("extraction_quality_report") or {}).get("missing_core_roles") or []),
                cause=(packet.get("extraction_quality_report") or {}).get("likely_failure_cause") or "",
                groups=_compact_counts(packet.get("strategic_group_counts")),
                sources=", ".join(packet.get("sources") or []),
            )
        )
    return "\n".join(lines) + "\n"


def _render_quality_examples(rows: list[dict[str, Any]], block: str, limit: int = 12) -> list[str]:
    title = block.replace("_", " ").title()
    ranked = _balanced_quality_rows(rows, block, limit=limit)
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


def _balanced_quality_rows(rows: list[dict[str, Any]], block: str, limit: int = 12) -> list[dict[str, Any]]:
    status_order = ("weak", "missing", "usable", "strong")
    sorted_rows = sorted(rows, key=lambda row: str(row.get("brand") or ""))
    selected: list[dict[str, Any]] = []
    seen: set[int] = set()

    for status in status_order:
        for row in sorted_rows:
            if row.get(f"{block}_quality") != status:
                continue
            selected.append(row)
            seen.add(id(row))
            break

    for row in sorted(
        rows,
        key=lambda item: (
            {status: index for index, status in enumerate(status_order)}.get(str(item.get(f"{block}_quality")), 99),
            str(item.get("brand") or ""),
        ),
    ):
        if id(row) in seen:
            continue
        selected.append(row)
        seen.add(id(row))
        if len(selected) >= limit:
            break
    return selected[:limit]


def _proof_support_cell(row: dict[str, Any]) -> str:
    credibility_status = row.get("credibility_support_status")
    credibility_count = row.get("credibility_support_count")
    if credibility_status not in {None, ""} and credibility_count not in {None, ""}:
        status = str(credibility_status)
        count = int(credibility_count or 0)
    else:
        status = str(row.get("proof_support_status") or "not_detected")
        count = int(row.get("proof_support_count") or 0)

    if count <= 0:
        return status
    return f"{status}:{count}"


def _canonical_evidence_quality_cell(row: dict[str, Any]) -> str:
    quality = str(row.get("canonical_evidence_quality") or "")
    reasons = row.get("canonical_evidence_quality_reasons") or []
    if not reasons:
        return quality
    return quality + " (" + ", ".join(str(reason) for reason in reasons[:3]) + ")"


def _extraction_diagnosis_cell(row: dict[str, Any]) -> str:
    diagnosis = str(row.get("extraction_diagnosis") or "")
    reasons = row.get("extraction_diagnosis_reasons") or []
    if not reasons:
        return diagnosis
    return diagnosis + " (" + ", ".join(str(reason) for reason in reasons[:3]) + ")"


def _quality_cell(row: dict[str, Any], block: str) -> str:
    quality = str(row.get(f"{block}_quality") or "")
    reasons = row.get(f"{block}_quality_reasons") or []
    if not reasons:
        return quality
    return quality + " (" + ", ".join(str(reason) for reason in reasons[:3]) + ")"


def _vertical_profiles_cell(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for impact in row.get("vertical_profile_impact") or []:
        profile = str(impact.get("profile") or "")
        touched = ",".join(impact.get("touched_blocks") or [])
        if profile and touched:
            parts.append(f"{profile}({touched})")
        elif profile:
            parts.append(profile)
    return "; ".join(parts) or "none"


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


def _compact_nested_counts(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    parts: list[str] = []
    for key, counts in value.items():
        compact = _compact_counts(counts)
        if compact:
            parts.append(f"{key}={compact}")
    return "; ".join(parts)


def _compact_block_quality(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    parts = []
    for block in QUALITY_BLOCKS:
        counts = _compact_counts(value.get(block))
        if counts:
            parts.append(f"{block}={counts}")
    return "; ".join(parts)


if __name__ == "__main__":
    main()
