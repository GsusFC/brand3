"""Utility and normalization helpers for Analyst TLDR support."""

from __future__ import annotations

from typing import Any
from dataclasses import is_dataclass

from src.reports.brand_research_pack import BrandResearchPack
from src.features.magnetism.analyst_tldr_support_runtime_constants import (
    ANALYST_BLOCK_QUESTIONS,
    ANALYST_TLDR_PROMPT_VERSION,
    TLDR_KEYS,
)


def normalize_analyst_response(
    raw: dict[str, Any],
    *,
    current_tldr: dict[str, Any] | None = None,
    research_pack: Any | None = None,
) -> dict[str, Any]:
    blocks = raw.get("tldr_brand3") if isinstance(raw.get("tldr_brand3"), dict) else {}
    normalized_blocks: dict[str, Any] = {}
    validation_notes: list[str] = []
    source_index = _source_index(research_pack)

    for key in TLDR_KEYS:
        raw_block = blocks.get(key) if isinstance(blocks.get(key), dict) else {}
        block, notes = _normalize_block(key, raw_block, source_index)
        normalized_blocks[key] = block
        validation_notes.extend(notes)

    normalized = {
        "prompt_version": ANALYST_TLDR_PROMPT_VERSION,
        "entity_reading": _clean_text(raw.get("entity_reading")),
        "verdict_vs_current": _clean_text(raw.get("verdict_vs_current")) or "unknown",
        "main_gain": _clean_text(raw.get("main_gain")),
        "main_risk": _clean_text(raw.get("main_risk")),
        "scoring_context": _normalize_scoring_context(raw.get("scoring_context")),
        "validation_notes": _unique_texts(validation_notes),
        "tldr_brand3": normalized_blocks,
    }
    if current_tldr:
        normalized["current_tldr"] = _compact_current_tldr(current_tldr)
    return normalized


def _compact_evidence_basis(evidence_packet_summary: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(evidence_packet_summary, dict):
        return {}
    proof_support = evidence_packet_summary.get("proof_support")
    evidence_payload: dict[str, Any] = {}
    if isinstance(proof_support, dict):
        proof_count_raw = proof_support.get("count")
        proof_count = (
            proof_count_raw
            if isinstance(proof_count_raw, int)
            else _safe_len(proof_support.get("evidence"))
        )
        evidence_payload = {
            "source": _clean_text(evidence_packet_summary.get("source")),
            "source_label": _clean_text(evidence_packet_summary.get("source_label")),
            "evidence_basis": _clean_text(evidence_packet_summary.get("evidence_basis")),
            "detected_signal_count": _to_non_negative_int(evidence_packet_summary.get("detected_signal_count")),
            "evidence_item_count": _to_non_negative_int(evidence_packet_summary.get("evidence_item_count")),
            "proof_support_status": _normalize_choice(
                proof_support.get("status") if isinstance(proof_support, dict) else None,
                {"observed", "partial", "not_detected"},
                fallback="not_detected",
            ),
            "proof_support_count": proof_count,
            "proof_support_reading": _clean_text(proof_support.get("reading")),
            "sources": _compact_list(evidence_packet_summary.get("sources"), limit=20, text_limit=180),
            "evidence_counts": evidence_packet_summary.get("evidence_counts"),
        }
    return evidence_payload


def _normalize_scoring_context(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    expressive = _bounded_int(raw.get("expressive_magnetism_score"))
    earned = _bounded_int(raw.get("earned_magnetism_score"))
    status = _normalize_choice(
        raw.get("evidence_duty_status"),
        {"not_required", "satisfied", "partial", "weak"},
        fallback="not_required",
    )
    requires_evidence = bool(raw.get("promise_requires_evidence")) or status in {"partial", "weak"}
    penalty = _bounded_int(raw.get("coherence_evidence_duty_penalty"), maximum=25)
    if not requires_evidence:
        status = "not_required"
        penalty = 0
    if earned is None:
        earned = expressive
    return {
        "expressive_magnetism_score": expressive,
        "earned_magnetism_score": earned,
        "promise_requires_evidence": requires_evidence,
        "evidence_duty_status": status,
        "coherence_evidence_duty_penalty": penalty or 0,
        "reasoning": _clean_text(raw.get("reasoning")),
        "evidence_gaps": _clean_list(raw.get("evidence_gaps")),
    }


def _normalize_block(
    key: str,
    raw: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    answer = _clean_text(raw.get("answer") or raw.get("content"))
    evidence_used = _clean_list(raw.get("evidence_used") or raw.get("evidence"))
    evidence_sources = _normalize_evidence_sources(raw.get("evidence_sources"), source_index)
    reasoning = _clean_text(raw.get("reasoning") or raw.get("rationale"))
    counter_evidence = _clean_list(raw.get("counter_evidence"))

    claim_type = _normalize_choice(raw.get("claim_type"), {"declared", "performed", "inferred", "absent"}, fallback="inferred" if answer else "absent")
    mode = _normalize_choice(
        raw.get("mode"),
        {"literal", "compressed", "interpreted_from_discourse", "needs_human_review", "not_detected"},
        fallback="interpreted_from_discourse" if answer else "not_detected",
    )
    confidence = _normalize_choice(raw.get("confidence"), {"high", "medium", "low"}, fallback="medium" if answer else "low")
    detected = bool(raw.get("detected")) or bool(answer)
    human_review = bool(raw.get("human_review_recommended"))

    if answer and not evidence_used:
        notes.append(f"{key}: answer present but evidence_used was missing or empty.")
        human_review = True
        if mode == "literal":
            mode = "needs_human_review"

    if not detected:
        claim_type = "absent"
        mode = "not_detected"
        confidence = "low"
        answer = ""

    question = _clean_text(raw.get("question")) or ANALYST_BLOCK_QUESTIONS[key]
    if not reasoning and answer:
        reasoning = "The analyst pass derived this block from the provided Research Pack evidence."

    if not counter_evidence and claim_type in {"inferred", "performed"} and answer:
        counter_evidence = [
            "The brand does not explicitly declare this exact Brand3 articulation in the available evidence."
        ]

    block = {
        "block": key,
        "question": question,
        "answer": answer or None,
        "content": answer or None,
        "claim_type": claim_type,
        "mode": mode,
        "confidence": confidence,
        "reasoning": reasoning,
        "rationale": reasoning,
        "evidence_used": evidence_used,
        "evidence_sources": evidence_sources,
        "evidence": evidence_used,
        "counter_evidence": counter_evidence,
        "human_review_recommended": human_review or mode == "needs_human_review" or (bool(answer) and not evidence_used),
        "detected": bool(answer) and mode != "not_detected",
        "validation_notes": notes,
    }
    return block, notes


def _fallback_payload(
    *,
    current_tldr: dict[str, Any] | None,
    reason: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "prompt_version": ANALYST_TLDR_PROMPT_VERSION,
        "analysis_error": {
            "reason": reason,
            "detail": detail,
        },
        "validation_notes": [detail],
        "tldr_brand3": _compact_current_tldr(current_tldr or {}),
    }


def _compact_current_tldr(current_tldr: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in TLDR_KEYS:
        block = current_tldr.get(key) if isinstance(current_tldr, dict) else None
        if not isinstance(block, dict):
            continue
        compact[key] = {
            "block": key,
            "question": _clean_text(block.get("question")) or ANALYST_BLOCK_QUESTIONS[key],
            "answer": block.get("answer") or block.get("content"),
            "claim_type": block.get("claim_type"),
            "mode": block.get("mode"),
            "confidence": block.get("confidence"),
            "reasoning": _clean_text(block.get("reasoning") or block.get("rationale")),
            "evidence_used": _clean_list(block.get("evidence_used") or block.get("evidence")),
        }
    return compact


def _normalize_evidence_sources(value: Any, source_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if isinstance(item, dict):
            source_key = _clean_text(item.get("source_key") or item.get("source_url") or item.get("url") or item.get("label"))
            url = _clean_text(item.get("url") or item.get("source_url"))
            label = _clean_text(item.get("label") or item.get("source_label"))
            source_type = _clean_text(item.get("source_type"))
        else:
            source_key = _clean_text(item)
            url = ""
            label = ""
            source_type = ""
        if not source_key and not url and not label:
            continue
        lookup_key = source_key or url or label
        if lookup_key.lower() in seen:
            continue
        seen.add(lookup_key.lower())
        metadata = source_index.get(lookup_key.lower(), {})
        output.append(
            {
                "source_key": source_key or metadata.get("source_key") or metadata.get("url") or lookup_key,
                "source_type": source_type or metadata.get("source_type", ""),
                "url": url or metadata.get("url", ""),
                "label": label or metadata.get("label", ""),
            }
        )
    return output


def _source_index(research_pack: Any | None) -> dict[str, dict[str, Any]]:
    pack = _research_pack_dict(research_pack)
    source_map = pack.get("source_map") if isinstance(pack, dict) else {}
    if not isinstance(source_map, dict):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for key, value in source_map.items():
        if not isinstance(value, dict):
            continue
        canonical = {
            "source_key": str(key),
            "source_type": _clean_text(value.get("source_type")),
            "url": _clean_text(value.get("url")),
            "label": _clean_text(value.get("label")),
        }
        for candidate in {str(key), canonical["url"], canonical["label"]}:
            candidate = _clean_text(candidate)
            if candidate:
                index[candidate.lower()] = canonical
    return index


def _research_pack_dict(research_pack: Any) -> dict[str, Any]:
    if research_pack is None:
        return {}
    if isinstance(research_pack, dict):
        return research_pack
    if isinstance(research_pack, BrandResearchPack) or is_dataclass(research_pack):
        return research_pack.to_dict()
    if hasattr(research_pack, "to_dict") and callable(research_pack.to_dict):
        payload = research_pack.to_dict()
        return payload if isinstance(payload, dict) else {}
    return {}


def _compact_research_pack_for_prompt(pack: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(pack, dict):
        return {}
    source_map = pack.get("source_map") if isinstance(pack.get("source_map"), dict) else {}
    compact = {
        "version": pack.get("version"),
        "input_url": pack.get("input_url"),
        "resolved_entity": pack.get("resolved_entity"),
        "entity_type": pack.get("entity_type"),
        "parent_brand": pack.get("parent_brand"),
        "official_urls": _compact_list(pack.get("official_urls"), limit=12, text_limit=180),
        "analyzed_urls": _compact_list(pack.get("analyzed_urls"), limit=20, text_limit=180),
        "source_map": _compact_source_map(source_map),
        "company_summary": _truncate_text(pack.get("company_summary"), 450),
        "product_summary": _truncate_text(pack.get("product_summary"), 450),
        "audience": _truncate_text(pack.get("audience"), 350),
        "offer": _truncate_text(pack.get("offer"), 450),
        "outcome": _truncate_text(pack.get("outcome"), 350),
        "category": _truncate_text(pack.get("category"), 160),
        "declared_purpose": _truncate_text(pack.get("declared_purpose"), 450),
        "declared_mission": _truncate_text(pack.get("declared_mission"), 450),
        "future_direction": _truncate_text(pack.get("future_direction"), 450),
        "tone_of_voice": _truncate_text(pack.get("tone_of_voice"), 220),
        "personality_signals": _compact_list(pack.get("personality_signals"), limit=8, text_limit=220),
        "visual_or_conceptual_signals": _compact_list(pack.get("visual_or_conceptual_signals"), limit=8, text_limit=220),
        "values_signals": _compact_list(pack.get("values_signals"), limit=8, text_limit=220),
        "attributes_signals": _compact_list(pack.get("attributes_signals"), limit=8, text_limit=220),
        "proof_points": _compact_evidence_list(pack.get("proof_points"), limit=8),
        "founder_or_press_context": _compact_evidence_list(pack.get("founder_or_press_context"), limit=8),
        "competitive_context": _compact_evidence_list(pack.get("competitive_context"), limit=4),
        "noise_rejected": _compact_evidence_list(pack.get("noise_rejected"), limit=4, text_limit=180),
        "evidence_gaps": _compact_list(pack.get("evidence_gaps"), limit=8, text_limit=260),
        "confidence_notes": _compact_list(pack.get("confidence_notes"), limit=8, text_limit=260),
        "evidence_counts": {
            "source_count": len(source_map),
            "proof_points": _safe_len(pack.get("proof_points")),
            "founder_or_press_context": _safe_len(pack.get("founder_or_press_context")),
            "competitive_context": _safe_len(pack.get("competitive_context")),
            "noise_rejected": _safe_len(pack.get("noise_rejected")),
        },
    }
    return compact


def _compact_source_map(source_map: dict[str, Any], *, limit: int = 35) -> dict[str, Any]:
    def priority(item: tuple[str, Any]) -> tuple[int, str]:
        value = item[1] if isinstance(item[1], dict) else {}
        source_type = str(value.get("source_type") or "")
        rank = {
            "owned_official": 0,
            "owned_product": 1,
            "owned_about": 2,
            "owned_security_trust": 3,
            "proof_point": 4,
            "press_or_founder": 5,
            "social": 6,
            "noise": 8,
        }.get(source_type, 7)
        return rank, str(item[0])

    compact: dict[str, Any] = {}
    for key, value in sorted(source_map.items(), key=priority)[:limit]:
        if not isinstance(value, dict):
            continue
        compact[str(key)] = {
            "url": _truncate_text(value.get("url"), 220),
            "source_type": _truncate_text(value.get("source_type"), 80),
            "label": _truncate_text(value.get("label"), 140),
            "surface_role": _truncate_text(value.get("surface_role"), 80),
            "entity_scope": _truncate_text(value.get("entity_scope"), 80),
            "title": _truncate_text(value.get("title"), 160),
        }
    return compact


def _compact_evidence_list(value: Any, *, limit: int, text_limit: int = 320) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        text = _truncate_text(item.get("text"), text_limit)
        source_url = _truncate_text(item.get("source_url"), 220)
        key = (text.lower(), source_url.lower())
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "text": text,
                "kind": _truncate_text(item.get("kind"), 40),
                "source_url": source_url,
                "source_type": _truncate_text(item.get("source_type"), 80),
                "source_label": _truncate_text(item.get("source_label"), 100),
                "topic": _truncate_text(item.get("topic"), 100),
                "confidence": _truncate_text(item.get("confidence"), 40),
            }
        )
        if len(output) >= limit:
            break
    return output


def _compact_list(value: Any, *, limit: int, text_limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _truncate_text(item, text_limit)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def _truncate_text(value: Any, limit: int) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _safe_len(value: Any) -> int:
    return len(value) if isinstance(value, list | dict) else 0


def _to_non_negative_int(value: Any) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def _normalize_choice(value: Any, allowed: set[str], fallback: str) -> str:
    normalized = _clean_text(value).lower()
    return normalized if normalized in allowed else fallback


def _bounded_int(value: Any, *, maximum: int = 100) -> int | None:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(0, min(maximum, number))


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _clean_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _unique_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


__all__ = [
    "normalize_analyst_response",
    "_normalize_scoring_context",
    "_normalize_block",
    "_compact_current_tldr",
    "_compact_evidence_basis",
    "_normalize_evidence_sources",
    "_source_index",
    "_research_pack_dict",
    "_compact_research_pack_for_prompt",
    "_compact_source_map",
    "_compact_evidence_list",
    "_compact_list",
    "_truncate_text",
    "_safe_len",
    "_to_non_negative_int",
    "_normalize_choice",
    "_bounded_int",
    "_clean_list",
    "_clean_text",
    "_unique_texts",
    "_fallback_payload",
]
