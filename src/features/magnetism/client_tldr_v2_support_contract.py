"""Prompt/schema contract and parser helpers for client TLDR v2."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from src.features.magnetism.analyst_tldr import TLDR_KEYS
from src.reports.experimental_perceptual_narrative import build_perceptual_narrative_hints

CLIENT_TLDR_V2_PROMPT_VERSION = "brand3-client-tldr-v2-v0.3"
CLIENT_TLDR_V2_TIMEOUT_SECONDS = 45

__all__ = [
    "CLIENT_TLDR_V2_PROMPT_VERSION",
    "CLIENT_TLDR_V2_TIMEOUT_SECONDS",
    "build_client_tldr_v2_prompt",
    "client_tldr_v2_response_schema",
    "run_client_tldr_v2_contract_functions",
    "_compact_score_state_for_prompt",
    "_compact_readiness_for_prompt",
    "_compact_dimensions_for_prompt",
    "_compact_perceptual_hints_for_prompt",
    "_compact_perceptual_guidance",
    "_client_tldr_v2_system_prompt",
    "_coerce_client_tldr_v2_raw_json",
    "_looks_like_editorial_client_tldr_v2_payload",
    "_safe_raw_response_preview",
    "_parse_plain_text_client_tldr_v2",
]


def run_client_tldr_v2_contract_functions() -> dict[str, Any]:
    """Compatibility shim for potential future runtime introspection."""
    return {
        "prompt_version": CLIENT_TLDR_V2_PROMPT_VERSION,
        "timeout_seconds": CLIENT_TLDR_V2_TIMEOUT_SECONDS,
        "tldr_keys": deepcopy(TLDR_KEYS),
    }


def build_client_tldr_v2_prompt(
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    perceptual_hints: dict[str, Any] | None = None,
    lang: str,
) -> str:
    """Build the compact LLM prompt input for client TLDR v2."""
    dimensions = _compact_dimensions_for_prompt(report_base)
    perceptual_hints = (
        _compact_perceptual_hints_for_prompt(report_base)
        if perceptual_hints is None
        else perceptual_hints
    )
    corpus_guidance = _compact_perceptual_guidance(perceptual_hints)
    payload = {
        "prompt_version": CLIENT_TLDR_V2_PROMPT_VERSION,
        "brand": {"name": brand_name, "url": url},
        "task": (
            "Write a client-safe editorial TLDR preview, not an audit object. "
            "Use the score and evidence context to produce concise strategic prose."
        ),
        "language": lang,
        "reasoning_contract": {
            "purpose": (
                "Perform strategic synthesis from the payload before writing the 9-block TLDR."
            ),
            "evidence_relevance": [
                "Evaluate each evidence item for relevance before using it.",
                "Classify evidence as owned, direct, indirect, weak, ambiguous, or off-entity.",
                "Off-entity evidence cannot support positive claims.",
                "Ambiguous entity evidence becomes a limitation, not proof.",
            ],
            "claim_ladder": [
                "Separate stated claims from performed claims, inferred claims, and absent claims.",
                "If explicit evidence is absent, explain the absence briefly and move the issue to validation questions.",
                "Use weak inference only when the evidence supports it cautiously.",
            ],
            "mission_vision": [
                "Do not hardcode Mission/Vision behavior.",
                "If no explicit mission exists, decide whether a performed or inferred mission is supported.",
                "If supported, write it as inferred.",
                "If not supported, say so briefly and turn the gap into validation questions.",
                "Apply the same logic to vision and other blocks.",
            ],
            "perceptual_hints": [
                "Use perceptual hints as reasoning lenses, not copy blocks.",
                "Reject hints that do not semantically fit the scanned brand.",
                "Do not copy unrelated corpus language into the TLDR.",
                "Corpus guidance is for tone, framing, and block reasoning only; it is not source-level evidence.",
                "Use the score/evidence payload as the only factual basis.",
            ],
            "corpus_guidance": corpus_guidance,
            "output_discipline": [
                "Preserve the 9-block TLDR structure, but keep the copy editorial.",
                "Group validation questions.",
                "Keep evidence internal; do not show raw evidence refs in the main body.",
                "Translate score and data quality into client-safe language.",
                "If a corpus phrase strongly matches expected output language, do not repeat it verbatim.",
                "Every claim must be traceable to scan evidence or the scored readiness context.",
            ],
        },
        "score_state": _compact_score_state_for_prompt(score_provenance),
        "readiness": _compact_readiness_for_prompt(report_base),
        "dimensions": dimensions,
        "current_tldr": current_tldr,
        "perceptual_hints": corpus_guidance,
        "required_output": {
            "executive_reading": "client-safe strategic synthesis",
            "score_note": "client-safe score/data-quality interpretation",
            "blocks": {
                key: "one short strategic paragraph or sentence"
                for key in TLDR_KEYS
            },
            "system_reading": {
                "credibility_support": "client-safe credibility sentence",
                "strategic_tensions": ["bounded strategic tensions"],
                "validation_questions": ["bounded validation questions"],
                "diagnosis": "client-safe diagnosis",
            },
            "caveats": ["bounded caveats"],
        },
        "rules": [
            "Keep the output client-safe and strategic.",
            "Do not mention replay, fingerprint, drift, provenance, or audit internals.",
            "Do not turn fallback values into quality judgments.",
            "Reason about ownership, directness, ambiguity, and entity fit before making claims.",
            "Use inferred language when evidence is thin or partial, but only when the evidence supports it.",
            "Turn weak inference into validation questions or caveats.",
            "Only use normalized perceptual hints that are evidence-bound.",
            "Do not surface review-only perceptual records, raw technical noise, or unrelated corpus language.",
            "Preserve the 9 TLDR blocks.",
            "Write in the requested language.",
            "Do not copy corpus guidance verbatim in the client output.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def client_tldr_v2_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["executive_reading", "score_note", "blocks", "system_reading", "caveats"],
        "properties": {
            "executive_reading": {"type": "string"},
            "score_note": {"type": "string"},
            "blocks": {
                "type": "object",
                "additionalProperties": False,
                "required": TLDR_KEYS,
                "properties": {key: {"type": "string"} for key in TLDR_KEYS},
            },
            "system_reading": {
                "type": "object",
                "additionalProperties": False,
                "required": ["credibility_support", "strategic_tensions", "validation_questions", "diagnosis"],
                "properties": {
                    "credibility_support": {"type": "string"},
                    "strategic_tensions": {"type": "array", "items": {"type": "string"}},
                    "validation_questions": {"type": "array", "items": {"type": "string"}},
                    "diagnosis": {"type": "string"},
                },
            },
            "caveats": {"type": "array", "items": {"type": "string"}},
        },
    }


def _compact_score_state_for_prompt(score_provenance: dict[str, Any]) -> dict[str, Any]:
    replay = score_provenance.get("replay_integrity") if isinstance(score_provenance.get("replay_integrity"), dict) else {}
    return {
        "computed_composite_score": score_provenance.get("computed_composite_score"),
        "reviewed_composite_score": (
            score_provenance.get("reviewed_score", {}).get("reviewed_composite_score")
            if isinstance(score_provenance.get("reviewed_score"), dict)
            else None
        ),
        "display_score_source": score_provenance.get("display_score_source"),
        "recommended_display_score": score_provenance.get("recommended_display_score"),
        "score_integrity": replay.get("status"),
        "fingerprint_status": replay.get("fingerprint_status"),
        "drift_type": replay.get("drift_type"),
        "warnings": score_provenance.get("warnings") or [],
        "fallback_flags": score_provenance.get("fallback_flags") or {},
    }


def _compact_readiness_for_prompt(report_base: dict[str, Any]) -> dict[str, Any]:
    evaluation = report_base.get("evaluation") if isinstance(report_base.get("evaluation"), dict) else {}
    readiness = evaluation.get("readiness") if isinstance(evaluation.get("readiness"), dict) else {}
    return {
        "report_mode": readiness.get("report_mode"),
        "warnings": readiness.get("warnings") or [],
        "missing_high_weight_features": readiness.get("missing_high_weight_features") or {},
        "fallback_detected": readiness.get("fallback_detected") or {},
        "quality": evaluation.get("data_quality"),
    }


def _compact_dimensions_for_prompt(report_base: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for dim in report_base.get("dimensions") or []:
        name = str(dim.get("name") or "")
        if not name:
            continue
        out[name] = {
            "score": dim.get("score"),
            "confidence": dim.get("confidence"),
            "confidence_label": dim.get("confidence_label"),
            "confidence_status": dim.get("confidence_status"),
            "missing_signals": dim.get("missing_signals") or [],
            "recommended_next_steps": dim.get("recommended_next_steps") or [],
            "evidence": dim.get("evidence") or [],
            "observations": dim.get("observations") or [],
        }
    return out


def _compact_perceptual_hints_for_prompt(report_base: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for dim in report_base.get("dimensions") or []:
        name = str(dim.get("name") or "")
        if not name:
            continue
        hints = build_perceptual_narrative_hints(name)
        if hints.empty():
            continue
        output[name] = {
            "surface_signals": hints.surface_signals[:4],
            "signal_clusters": hints.signal_clusters[:3],
            "matched_patterns": [
                {
                    "pattern_id": item.get("pattern_id"),
                    "pattern_name": item.get("pattern_name"),
                    "perceptual_meaning": item.get("perceptual_meaning"),
                }
                for item in hints.matched_patterns[:4]
            ],
            "productive_tensions": hints.productive_tensions[:4],
            "confidence_notes": hints.confidence_notes[:3],
            "overreach_boundaries": hints.overreach_boundaries[:4],
        }
    return output


def _compact_perceptual_guidance(perceptual_hints: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(perceptual_hints, dict):
        return {}

    pattern_meanings: list[str] = []
    tone_style_examples: list[str] = []
    block_level_reasoning: list[str] = []
    strategic_patterns: list[str] = []
    reading_boundaries: list[str] = []

    for dimension, hints in perceptual_hints.items():
        if not isinstance(hints, dict):
            continue
        dimension_name = _clean_text(dimension)
        if not dimension_name:
            continue

        for signal in _normalize_list_text_values(hints.get("surface_signals")):
            if signal:
                block_level_reasoning.append(f"{dimension_name}: {signal}")

        for pattern in _normalize_list_dict_values(hints.get("matched_patterns")):
            pattern_name = _clean_text(pattern.get("pattern_name"))
            meaning = _clean_text(pattern.get("perceptual_meaning"))
            if pattern_name:
                strategic_patterns.append(pattern_name)
            if meaning:
                pattern_meanings.append(meaning)
                tone_style_examples.append(meaning)

        for tension in _normalize_list_text_values(hints.get("productive_tensions")):
            if tension:
                block_level_reasoning.append(f"{dimension_name}: {tension}")

        for note in _normalize_list_text_values(hints.get("confidence_notes")):
            if note:
                tone_style_examples.append(note)

        for boundary in _normalize_list_text_values(hints.get("overreach_boundaries")):
            if boundary:
                reading_boundaries.append(boundary)

    return {
        "strategic_reading_patterns": _unique(strategic_patterns)[:5],
        "pattern_meanings": _unique(pattern_meanings)[:6],
        "tone_style_examples": _unique(tone_style_examples)[:6],
        "block_level_reasoning": _unique(block_level_reasoning)[:8],
        "reading_boundaries": _unique(reading_boundaries)[:6],
    }


def _client_tldr_v2_system_prompt(lang: str) -> str:
    if lang == "en":
        return (
            "You are Brand3's Client TLDR v2 writer. "
            "Write a client-safe editorial TLDR first, not an audit object. "
            "Use the provided evidence to synthesize a concise strategic reading. "
            "Reason about evidence relevance, entity fit, and claim type before writing. "
            "Classify evidence as owned, direct, indirect, weak, ambiguous, or off-entity. "
            "Separate stated, performed, inferred, and absent claims. "
            "If a claim is unsupported, turn it into a validation question instead of forcing a conclusion. "
            "Do not hardcode Mission/Vision behavior. "
            "Do not mention replay, fingerprint, drift, provenance, internal audit, or technical scoring jargon. "
            "Use perceptual hints only as reasoning lenses, not as copy. "
            "Reject hints that do not fit the brand. "
            "Keep the 9-block structure, but write the blocks as short strategic prose. "
            "Never present fallback values as quality. Return strict JSON only."
        )
    return (
        "You are the writer of Brand3 TLDR v2 para cliente. "
        "Escribe primero un TLDR editorial y seguro para clientes, no un objeto de auditoría. "
        "Usa la evidencia proporcionada para sintetizar una lectura estratégica breve. "
        "Primero razona sobre la relevancia de la evidencia, el ajuste de entidad y el tipo de claim antes de escribir. "
        "Clasifica la evidencia como propia, directa, indirecta, débil, ambigua o fuera de entidad. "
        "Separa claims declarados, performados, inferidos y ausentes. "
        "Si un claim no está soportado, conviértelo en una pregunta de validación en lugar de forzar una conclusión. "
        "No hardcodees el comportamiento de Mission/Vision. "
        "No menciones replay, fingerprint, drift, provenance, auditoría interna ni jerga técnica de scoring. "
        "Usa los perceptual hints solo como lentes de razonamiento, no como texto para copiar. "
        "Rechaza hints que no encajen semánticamente con la marca. "
        "Mantén la estructura de 9 bloques, pero escribe los bloques como prosa estratégica breve. "
        "Nunca presentes valores fallback como calidad. Devuelve solo JSON válido."
    )


def _coerce_client_tldr_v2_raw_json(raw: Any) -> dict[str, Any]:
    value = raw
    for _ in range(4):
        if isinstance(value, str):
            try:
                value = json.loads(value.strip())
            except json.JSONDecodeError:
                return {}
            continue
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
            continue
        if isinstance(value, dict):
            if _looks_like_editorial_client_tldr_v2_payload(value) or (
                isinstance(value.get("tldr_brand3_v2"), dict) and isinstance(value.get("system_reading"), dict)
            ):
                return value
            for key in ("payload", "content", "output", "response", "result", "message", "data"):
                nested = value.get(key)
                if isinstance(nested, (dict, list, str)):
                    value = nested
                    break
            else:
                return value
            continue
        break
    return {} if not isinstance(value, dict) else value


def _looks_like_editorial_client_tldr_v2_payload(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if any(key in value for key in ("executive_reading", "score_note", "blocks", "caveats")):
        return True
    system_reading = value.get("system_reading")
    return isinstance(system_reading, dict) and (
        "credibility_support" in system_reading
        or "strategic_tensions" in system_reading
        or "validation_questions" in system_reading
        or "diagnosis" in system_reading
    )


def _safe_raw_response_preview(llm: Any) -> str | None:
    raw = getattr(llm, "last_raw_response", None)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    return text[:8000]


def _parse_plain_text_client_tldr_v2(text: str) -> dict[str, Any]:
    content = (text or "").strip()
    if not content:
        return {}

    sections: dict[str, list[str]] = {}
    current_key = "executive_reading"
    buffer: list[str] = []
    recognized_sections = 0

    def flush() -> None:
        if buffer:
            sections.setdefault(current_key, []).append("\n".join(buffer).strip())
            buffer.clear()

    heading_map = {
        "core purpose": "core_purpose",
        "magnetism": "magnetism",
        "value proposition": "value_proposition",
        "personality": "personality",
        "brand idea": "brand_idea",
        "attributes": "attributes",
        "values": "values",
        "mission": "mission",
        "vision": "vision",
        "credibility support": "credibility_support",
        "strategic tensions": "strategic_tensions",
        "validation questions": "validation_questions",
        "diagnosis": "diagnosis",
        "caveats": "caveats",
        "score note": "score_note",
        "executive reading": "executive_reading",
    }

    for line in content.splitlines():
        stripped = line.strip()
        normalized = stripped.lower().lstrip("#").strip()
        normalized = normalized.replace(":", "")
        matched_key = None
        for heading, key in heading_map.items():
            if normalized == heading or normalized.startswith(f"{heading} ") or normalized.startswith(f"{heading}-"):
                matched_key = key
                break
        if matched_key:
            recognized_sections += 1
            flush()
            current_key = matched_key
            continue
        if not stripped and not buffer:
            continue
        buffer.append(line)
    flush()

    if recognized_sections == 0:
        return {}

    blocks: dict[str, str] = {}
    for key in TLDR_KEYS:
        blocks[key] = sections.get(key, [""])[0].strip() if sections.get(key) else ""

    strategic_tensions = _split_plain_text_list(sections.get("strategic_tensions", []))
    validation_questions = _split_plain_text_list(sections.get("validation_questions", []))
    caveats = _split_plain_text_list(sections.get("caveats", []))
    credibility_support = sections.get("credibility_support", [""])[0].strip() if sections.get("credibility_support") else ""
    diagnosis = sections.get("diagnosis", [""])[0].strip() if sections.get("diagnosis") else ""

    executive_reading = sections.get("executive_reading", [""])[0].strip() if sections.get("executive_reading") else ""
    score_note = sections.get("score_note", [""])[0].strip() if sections.get("score_note") else ""

    if not executive_reading:
        executive_reading = _first_nonempty_paragraph(content)
    if not score_note:
        score_note = executive_reading

    return {
        "executive_reading": executive_reading,
        "score_note": score_note,
        "blocks": blocks,
        "system_reading": {
            "credibility_support": credibility_support,
            "strategic_tensions": strategic_tensions,
            "validation_questions": validation_questions,
            "diagnosis": diagnosis,
        },
        "caveats": caveats,
    }


def _split_plain_text_list(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        for line in value.splitlines():
            text = line.strip().lstrip("-•*").strip()
            if text:
                items.append(text)
    return _unique(items)


def _first_nonempty_paragraph(text: str) -> str:
    for paragraph in text.split("\n\n"):
        stripped = paragraph.strip()
        if stripped:
            return stripped
    return ""


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


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


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        text = _clean_text(item)
        if text and text not in output:
            output.append(text)
    return output


def _unique(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = _clean_text(value)
        if text and text not in output:
            output.append(text)
    return output
