"""Client-facing TLDR v2 normalization helpers."""

from __future__ import annotations

from typing import Any

from src.features.magnetism.analyst_tldr import TLDR_KEYS
from src.features.magnetism.client_tldr_v2_support_contract import CLIENT_TLDR_V2_PROMPT_VERSION
from src.features.magnetism.client_tldr_v2_support_normalization_score import (
    _normalize_score_reading,
    _client_score_provenance,
)
from src.features.magnetism.client_tldr_v2_support_normalization_system import (
    _collect_evidence_refs,
    _client_system_reading,
    _legacy_system_reading,
    _normalize_system_reading,
    _validation_notes,
)
from src.features.magnetism.client_tldr_v2_support_normalization_blocks import (
    _clean_list,
    _client_tldr_v2_block_text,
    _normalize_client_block,
    _normalize_evidence_sources,
    _normalize_tldr_blocks,
    _resolve_client_tldr_v2_block,
    _clean_text,
)

def normalize_client_tldr_v2_response(
    raw: dict[str, Any],
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    perceptual_guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if "blocks" in raw or "executive_reading" in raw or "score_note" in raw or "caveats" in raw:
        return _normalize_client_tldr_v2_editorial_response(
            raw,
            brand_name=brand_name,
            url=url,
            current_tldr=current_tldr,
            score_provenance=score_provenance,
            report_base=report_base,
            lang=lang,
            perceptual_guidance=perceptual_guidance or {},
        )
    return _normalize_client_tldr_v2_legacy_response(
        raw,
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
        perceptual_guidance=perceptual_guidance or {},
    )


def _normalize_client_tldr_v2_editorial_response(
    raw: dict[str, Any],
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    perceptual_guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score_note = _clean_text(raw.get("score_note"))
    executive_reading = _clean_text(raw.get("executive_reading"))
    score_reading = _normalize_score_reading(
        raw.get("score_reading"),
        score_provenance,
        lang,
        score_note=score_note or executive_reading,
    )
    normalized_blocks: dict[str, str] = {}
    legacy_blocks: dict[str, Any] = {}
    validation_notes: list[str] = []
    for key in TLDR_KEYS:
        raw_block = _resolve_client_tldr_v2_block(raw, key)
        legacy_block, notes = _normalize_client_block(
            key,
            raw_block,
            current_tldr.get(key) if isinstance(current_tldr, dict) else {},
            lang=lang,
        )
        legacy_blocks[key] = legacy_block
        block_text = _client_tldr_v2_block_text(raw_block)
        if not block_text:
            block_text = _clean_text(legacy_block.get("answer") or legacy_block.get("content"))
        normalized_blocks[key] = block_text
        validation_notes.extend(notes)

    caveats = _clean_list(raw.get("caveats"))
    system_reading = _normalize_system_reading(
        raw.get("system_reading"),
        score_provenance,
        report_base,
        lang,
        executive_reading=executive_reading,
        caveats=caveats,
    )
    system_reading = _client_system_reading(system_reading)
    if executive_reading and not system_reading.get("diagnosis"):
        system_reading["diagnosis"] = executive_reading
    if score_note:
        score_reading["note"] = score_note
    evidence_refs = _collect_evidence_refs(legacy_blocks, score_provenance)
    validation_notes.extend(_validation_notes(legacy_blocks, score_provenance, _legacy_system_reading(system_reading)))
    validation_notes.extend(caveats)
    return {
        "prompt_version": CLIENT_TLDR_V2_PROMPT_VERSION,
        "generation_mode": "llm_client_v2",
        "brand_name": brand_name,
        "url": url,
        "score_reading": score_reading,
        "executive_reading": executive_reading,
        "score_note": score_note,
        "blocks": normalized_blocks,
        "legacy_tldr_brand3_v2": legacy_blocks,
        "system_reading": system_reading,
        "caveats": caveats,
        "evidence_refs": evidence_refs,
        "validation_notes": _unique(validation_notes),
        "display_score_source": score_reading.get("display_source"),
        "recommended_display_score": score_reading.get("value"),
    }


def _normalize_client_tldr_v2_legacy_response(
    raw: dict[str, Any],
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    perceptual_guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score_reading = _normalize_score_reading(raw.get("score_reading"), score_provenance, lang)
    raw_blocks = raw.get("tldr_brand3_v2") if isinstance(raw.get("tldr_brand3_v2"), dict) else {}
    normalized_blocks: dict[str, str] = {}
    legacy_blocks: dict[str, Any] = {}
    validation_notes: list[str] = []
    for key in TLDR_KEYS:
        raw_block = _resolve_client_tldr_v2_block(raw, key)
        legacy_block, notes = _normalize_client_block(
            key,
            raw_block,
            current_tldr.get(key) if isinstance(current_tldr, dict) else {},
            lang=lang,
        )
        legacy_blocks[key] = legacy_block
        block_text = _client_tldr_v2_block_text(raw_block) or _clean_text(legacy_block.get("answer") or legacy_block.get("content"))
        normalized_blocks[key] = block_text
        validation_notes.extend(notes)

    system_reading = _normalize_system_reading(raw.get("system_reading"), score_provenance, report_base, lang)
    system_reading = _client_system_reading(system_reading)
    evidence_refs = _collect_evidence_refs(legacy_blocks, score_provenance)
    validation_notes.extend(_validation_notes(legacy_blocks, score_provenance, _legacy_system_reading(system_reading)))
    return {
        "prompt_version": CLIENT_TLDR_V2_PROMPT_VERSION,
        "generation_mode": "llm_client_v2",
        "brand_name": brand_name,
        "url": url,
        "score_reading": score_reading,
        "blocks": normalized_blocks,
        "legacy_tldr_brand3_v2": legacy_blocks,
        "system_reading": system_reading,
        "evidence_refs": evidence_refs,
        "validation_notes": _unique(validation_notes),
        "display_score_source": score_reading.get("display_source"),
        "recommended_display_score": score_reading.get("value"),
    }


def _unique(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = _clean_text(value)
        if text and text not in output:
            output.append(text)
    return output
