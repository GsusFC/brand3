"""Block-level TLDR v2 normalization helpers."""

from __future__ import annotations

from typing import Any

from src.features.magnetism.analyst_tldr import TLDR_KEYS
from src.features.magnetism.client_tldr_v2_support_normalization_system import _question_for_block
from src.features.magnetism.client_tldr_v2_support_runtime import _normalize_choice


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
        evidence_refs = [source.get("url") for source in source_block.get("evidence_sources") if source.get("url")]
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
    return compact


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
    return str(value).strip()


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        text = _clean_text(item)
        if text and text not in output:
            output.append(text)
    return output
