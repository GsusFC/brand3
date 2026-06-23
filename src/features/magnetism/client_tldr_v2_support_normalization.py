"""Client-facing TLDR v2 normalization helpers."""

from __future__ import annotations

from typing import Any

from src.features.magnetism.analyst_tldr import TLDR_KEYS
from src.features.magnetism.client_tldr_v2_support_runtime import _normalize_choice
from src.features.magnetism.client_tldr_v2_support_contract import CLIENT_TLDR_V2_PROMPT_VERSION
from src.features.magnetism.client_tldr_v2_support_normalization_score import (
    _client_score_provenance,
    _normalize_score_reading,
)
from src.features.magnetism.client_tldr_v2_support_normalization_system import (
    _collect_evidence_refs,
    _client_system_reading,
    _legacy_system_reading,
    _question_for_block,
    _normalize_system_reading,
    _validation_notes,
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


def _normalize_client_block(
    key: str,
    raw_block: Any,
    source_block: dict[str, Any],
    *,
    lang: str,
) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    raw = raw_block if isinstance(raw_block, dict) else {}
    raw_text = _clean_text(raw_block) if isinstance(raw_block, str) else ""
    source_answer = _clean_text(source_block.get("answer") or source_block.get("content"))
    answer = _clean_text(raw.get("answer") or raw.get("content") or raw_text) or source_answer
    question = _clean_text(raw.get("question")) or _question_for_block(key, lang)
    claim_type = _normalize_choice(
        raw.get("claim_type"),
        {"declared", "performed", "inferred", "absent"},
        fallback="inferred" if answer else "absent",
    )
    mode = _normalize_choice(
        raw.get("mode"),
        {"literal", "interpreted_from_discourse", "needs_human_review", "not_detected"},
        fallback="interpreted_from_discourse" if answer else "not_detected",
    )
    confidence = _normalize_choice(raw.get("confidence"), {"high", "medium", "low"}, fallback="medium" if answer else "low")
    evidence_refs = _clean_list(raw.get("evidence_refs")) or [source.get("url") for source in source_block.get("evidence_sources", []) if source.get("url")]
    caveat = _clean_text(raw.get("caveat"))
    validation_question = _clean_text(raw.get("validation_question"))
    reasoning = _clean_text(raw.get("reasoning") or raw.get("rationale") or source_block.get("reasoning"))
    if not evidence_refs and answer:
        notes.append(f"{key}: answer present without evidence refs.")
        caveat = caveat or (
            "This block is still lightly evidenced." if lang == "en" else "Este bloque todavía está poco evidenciado."
        )
        validation_question = validation_question or _question_for_block(key, lang)
        mode = "needs_human_review"
        confidence = "low"
    if not answer:
        claim_type = "absent"
        mode = "not_detected"
        confidence = "low"
    if not reasoning and answer:
        reasoning = (
            "This reading is grounded in the available evidence and the current score context."
            if lang == "en"
            else "Esta lectura se apoya en la evidencia disponible y en el contexto del score."
        )
    if not validation_question and confidence in {"low", "medium"}:
        validation_question = _question_for_block(key, lang)
    if not caveat and confidence == "low":
        caveat = (
            "Treat this as a working reading, not a conclusion."
            if lang == "en"
            else "Trátalo como una lectura de trabajo, no como una conclusión."
        )
    if not evidence_refs and source_block.get("evidence_sources"):
        evidence_refs = [source.get("url") for source in source_block.get("evidence_sources", []) if source.get("url")]
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
        "evidence_used": _clean_list(source_block.get("evidence_used")),
        "evidence_sources": _normalize_evidence_sources(source_block.get("evidence_sources")),
        "evidence_refs": [ref for ref in evidence_refs if isinstance(ref, str) and ref.strip()],
        "counter_evidence": _clean_list(source_block.get("counter_evidence")),
        "human_review_recommended": bool(raw.get("human_review_recommended")) or mode == "needs_human_review" or confidence == "low",
        "validation_question": validation_question,
        "caveat": caveat,
        "detected": bool(answer) and mode != "not_detected",
    }
    return block, notes


def _client_tldr_v2_block_aliases(key: str) -> list[str]:
    spaced = key.replace("_", " ")
    title = spaced.title()
    kebab = key.replace("_", "-")
    compact = key.replace("_", "")
    return [
        key,
        key.upper(),
        spaced,
        spaced.upper(),
        title,
        title.upper(),
        kebab,
        kebab.upper(),
        compact,
        compact.upper(),
    ]


def _client_tldr_v2_block_text(raw_block: Any) -> str:
    if isinstance(raw_block, str):
        return _clean_text(raw_block)
    if isinstance(raw_block, dict):
        for field in ("answer", "content", "text", "reading"):
            text = _clean_text(raw_block.get(field))
            if text:
                return text
        return _clean_text(str(raw_block))
    return ""


def _resolve_client_tldr_v2_block(raw: dict[str, Any], key: str) -> Any:
    if not isinstance(raw, dict):
        return None
    candidate_maps: list[dict[str, Any]] = []
    for candidate in (raw.get("blocks"), raw.get("tldr_brand3_v2"), raw):
        if isinstance(candidate, dict):
            candidate_maps.append(candidate)
    aliases = _client_tldr_v2_block_aliases(key)
    for candidate_map in candidate_maps:
        for alias in aliases:
            if alias in candidate_map:
                return candidate_map.get(alias)
    return None


def _normalize_tldr_blocks(current_tldr: dict[str, Any] | None) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    source = current_tldr if isinstance(current_tldr, dict) else {}
    for key in TLDR_KEYS:
        block = source.get(key) if isinstance(source.get(key), dict) else {}
        answer = _clean_text(block.get("answer") or block.get("content"))
        compact[key] = {
            "block": key,
            "question": _clean_text(block.get("question")),
            "answer": answer or None,
            "content": answer or None,
            "claim_type": _clean_text(block.get("claim_type")) or ("inferred" if answer else "absent"),
            "mode": _clean_text(block.get("mode")) or ("interpreted_from_discourse" if answer else "not_detected"),
            "confidence": _clean_text(block.get("confidence")) or ("medium" if answer else "low"),
            "reasoning": _clean_text(block.get("reasoning") or block.get("rationale")),
            "rationale": _clean_text(block.get("reasoning") or block.get("rationale")),
            "evidence_used": _clean_list(block.get("evidence_used") or block.get("evidence")),
            "evidence_sources": _normalize_evidence_sources(block.get("evidence_sources")),
            "counter_evidence": _clean_list(block.get("counter_evidence")),
            "human_review_recommended": bool(block.get("human_review_recommended")),
            "detected": bool(answer) or bool(block.get("detected")),
        }


def _normalize_evidence_sources(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    out: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            url = _clean_text(item.get("url") or item.get("source_url"))
            label = _clean_text(item.get("label") or item.get("source_label") or item.get("source_type"))
            source_key = _clean_text(item.get("source_key") or item.get("source_url") or item.get("url"))
        else:
            url = _clean_text(item)
            label = ""
            source_key = _clean_text(item)
        if not url and not source_key:
            continue
        out.append(
            {
                "url": url or source_key,
                "label": label or source_key or url,
                "source_key": source_key or url,
            }
        )
    return out


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        text = _clean_text(item)
        if text and text not in output:
            output.append(text)
    return output


def _normalize_list_text_values(value: Any) -> list[str]:
    return _unique(_clean_list(value))


def _normalize_list_dict_values(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            output.append(item)
    return output


def _unique(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = _clean_text(value)
        if text and text not in output:
            output.append(text)
    return output
