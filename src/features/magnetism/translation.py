"""Cached translation helpers for Magnetism Scanner TLDR payloads."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any


MAGNETISM_TRANSLATION_VERSION = 1
MAGNETISM_TRANSLATION_SOURCE = "magnetism_tldr_translation"


def translate_magnetism_payload(
    payload: dict[str, Any],
    *,
    target_lang: str,
    analyzer,
) -> dict[str, Any] | None:
    """Translate persisted Magnetism prose without changing evidence or scores."""
    if target_lang not in {"es", "en"} or analyzer is None:
        return None
    call_json = getattr(analyzer, "_call_json", None)
    if not callable(call_json):
        return None

    source = _translation_input(payload)
    if not _has_translatable_text(source):
        return None

    result = call_json(
        system=(
            "You are a precise translator for Brand3 Magnetism Scanner. Return only valid JSON. "
            "Translate prose into the requested language without adding strategy, facts, evidence, "
            "recommendations, URLs, scores, claims, or methodology. Preserve all JSON keys, block keys, "
            "scores, source_signal_path values, claim_type, mode, confidence, URLs, proper nouns, product "
            "names, and literal evidence. Do not translate evidence_used or evidence quotes."
        ),
        user=(
            f"Target language: {target_lang}\n\n"
            "Translate this Magnetism Scanner TLDR JSON. Preserve the exact schema and array lengths.\n"
            "JSON:\n"
            f"{json.dumps(source, ensure_ascii=False, sort_keys=True)}"
        ),
        max_tokens=6000,
    )
    if not isinstance(result, dict):
        return None
    translated = _validated_translation(source, result)
    if not translated:
        return None
    translated.update(
        {
            "translation_version": MAGNETISM_TRANSLATION_VERSION,
            "translation_source": MAGNETISM_TRANSLATION_SOURCE,
            "target_lang": target_lang,
            "translated_at": datetime.now().isoformat(),
        }
    )
    return translated


def apply_magnetism_translation(payload: dict[str, Any], translation: dict[str, Any] | None) -> dict[str, Any]:
    """Return a copy of payload with translated prose overlaid."""
    if not translation:
        return payload
    out = copy.deepcopy(payload)

    for key in ("quadrant", "executive_headline"):
        if translation.get(key):
            out[key] = translation[key]

    if isinstance(translation.get("observations"), list):
        out["observations"] = translation["observations"]
    if isinstance(translation.get("limitations"), list):
        out["limitations"] = translation["limitations"]

    if isinstance(translation.get("diagnosis"), dict):
        diagnosis = dict(out.get("diagnosis") or {})
        diagnosis.update({k: v for k, v in translation["diagnosis"].items() if v})
        out["diagnosis"] = diagnosis

    if isinstance(translation.get("system_reading"), dict):
        system_reading = dict(out.get("system_reading") or {})
        system_reading.update({k: v for k, v in translation["system_reading"].items() if v})
        out["system_reading"] = system_reading

    translated_blocks = translation.get("tldr_brand3")
    if isinstance(translated_blocks, dict):
        blocks = copy.deepcopy(out.get("tldr_brand3") or {})
        for block_key, translated_block in translated_blocks.items():
            if not isinstance(translated_block, dict):
                continue
            source_block = dict(blocks.get(block_key) or {})
            for text_key in ("content", "answer", "reasoning", "rationale"):
                if translated_block.get(text_key):
                    source_block[text_key] = translated_block[text_key]
            if isinstance(translated_block.get("counter_evidence"), list):
                source_block["counter_evidence"] = translated_block["counter_evidence"]
            blocks[block_key] = source_block
        out["tldr_brand3"] = blocks

    translated_layers = translation.get("magenta_circle")
    if isinstance(translated_layers, dict):
        layers = copy.deepcopy(out.get("magenta_circle") or {})
        for layer_key, translated_layer in translated_layers.items():
            if not isinstance(translated_layer, dict):
                continue
            layer = dict(layers.get(layer_key) or {})
            for text_key in ("finding", "findings"):
                if translated_layer.get(text_key):
                    layer[text_key] = translated_layer[text_key]
            layers[layer_key] = layer
        out["magenta_circle"] = layers

    return out


def _translation_input(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "quadrant": _clean(payload.get("quadrant")),
        "executive_headline": _clean(payload.get("executive_headline")),
        "observations": _clean_list(payload.get("observations")),
        "limitations": _clean_list(payload.get("limitations")),
        "diagnosis": _diagnosis_input(payload.get("diagnosis")),
        "system_reading": _system_reading_input(payload.get("system_reading")),
        "tldr_brand3": _tldr_input(payload.get("tldr_brand3")),
        "magenta_circle": _magenta_input(payload.get("magenta_circle")),
    }


def _diagnosis_input(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "headline": _clean(value.get("headline")),
        "key_observations": _clean_list(value.get("key_observations")),
    }


def _system_reading_input(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    credibility = value.get("credibility_support")
    return {
        "strategic_tensions": _clean_list(value.get("strategic_tensions")),
        "validation_questions": _clean_list(value.get("validation_questions")),
        "credibility_support": {
            "reading": _clean(credibility.get("reading")) if isinstance(credibility, dict) else "",
        },
    }


def _tldr_input(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, Any] = {}
    for key, block in value.items():
        if not isinstance(block, dict):
            continue
        out[key] = {
            "content": block.get("content"),
            "answer": block.get("answer"),
            "reasoning": block.get("reasoning"),
            "rationale": block.get("rationale"),
            "counter_evidence": _clean_list(block.get("counter_evidence")),
        }
    return out


def _magenta_input(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, Any] = {}
    for key, layer in value.items():
        if not isinstance(layer, dict):
            continue
        out[key] = {
            "finding": _clean(layer.get("finding")),
            "findings": _clean(layer.get("findings")),
        }
    return out


def _has_translatable_text(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_has_translatable_text(item) for item in value)
    if isinstance(value, dict):
        return any(_has_translatable_text(item) for item in value.values())
    return False


def _validated_translation(source: dict[str, Any], result: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(result.get("tldr_brand3"), dict):
        return None
    return {
        "quadrant": _clean(result.get("quadrant")) or source.get("quadrant", ""),
        "executive_headline": _clean(result.get("executive_headline")) or source.get("executive_headline", ""),
        "observations": _same_len_list(source.get("observations"), result.get("observations")),
        "limitations": _same_len_list(source.get("limitations"), result.get("limitations")),
        "diagnosis": _validated_diagnosis(source.get("diagnosis"), result.get("diagnosis")),
        "system_reading": _validated_system_reading(source.get("system_reading"), result.get("system_reading")),
        "tldr_brand3": _validated_blocks(source.get("tldr_brand3"), result.get("tldr_brand3")),
        "magenta_circle": _validated_layers(source.get("magenta_circle"), result.get("magenta_circle")),
    }


def _validated_diagnosis(source: Any, result: Any) -> dict[str, Any]:
    source = source if isinstance(source, dict) else {}
    result = result if isinstance(result, dict) else {}
    return {
        "headline": _clean(result.get("headline")) or source.get("headline", ""),
        "key_observations": _same_len_list(source.get("key_observations"), result.get("key_observations")),
    }


def _validated_system_reading(source: Any, result: Any) -> dict[str, Any]:
    source = source if isinstance(source, dict) else {}
    result = result if isinstance(result, dict) else {}
    source_cred = source.get("credibility_support") if isinstance(source.get("credibility_support"), dict) else {}
    result_cred = result.get("credibility_support") if isinstance(result.get("credibility_support"), dict) else {}
    return {
        "strategic_tensions": _same_len_list(source.get("strategic_tensions"), result.get("strategic_tensions")),
        "validation_questions": _same_len_list(source.get("validation_questions"), result.get("validation_questions")),
        "credibility_support": {
            "reading": _clean(result_cred.get("reading")) or source_cred.get("reading", ""),
        },
    }


def _validated_blocks(source: Any, result: Any) -> dict[str, Any]:
    source = source if isinstance(source, dict) else {}
    result = result if isinstance(result, dict) else {}
    out: dict[str, Any] = {}
    for key, source_block in source.items():
        if not isinstance(source_block, dict):
            continue
        translated_block = result.get(key) if isinstance(result.get(key), dict) else {}
        out[key] = {
            "content": _translated_value(source_block.get("content"), translated_block.get("content")),
            "answer": _translated_value(source_block.get("answer"), translated_block.get("answer")),
            "reasoning": _clean(translated_block.get("reasoning")) or source_block.get("reasoning", ""),
            "rationale": _clean(translated_block.get("rationale")) or source_block.get("rationale", ""),
            "counter_evidence": _same_len_list(source_block.get("counter_evidence"), translated_block.get("counter_evidence")),
        }
    return out


def _validated_layers(source: Any, result: Any) -> dict[str, Any]:
    source = source if isinstance(source, dict) else {}
    result = result if isinstance(result, dict) else {}
    out: dict[str, Any] = {}
    for key, source_layer in source.items():
        if not isinstance(source_layer, dict):
            continue
        translated_layer = result.get(key) if isinstance(result.get(key), dict) else {}
        out[key] = {
            "finding": _clean(translated_layer.get("finding")) or source_layer.get("finding", ""),
            "findings": _clean(translated_layer.get("findings")) or source_layer.get("findings", ""),
        }
    return out


def _translated_value(source: Any, result: Any) -> Any:
    if isinstance(source, list):
        return _same_len_list(source, result)
    return _clean(result) or source


def _same_len_list(source: Any, result: Any) -> list[str]:
    source_items = _clean_list(source)
    result_items = _clean_list(result)
    if len(result_items) != len(source_items):
        return source_items
    return [result_items[idx] or source_items[idx] for idx in range(len(source_items))]


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean(item) for item in value if _clean(item)]


def _clean(value: Any) -> str:
    return str(value or "").strip()
