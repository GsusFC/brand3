"""Cached translation for persisted Brand Audit report narrative."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .dossier import REPORT_NARRATIVE_VERSION

REPORT_TRANSLATION_VERSION = 1
REPORT_TRANSLATION_SOURCE = "report_translation"


def latest_report_narrative_payload(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") != "report_narrative":
            continue
        payload = item.get("payload")
        if isinstance(payload, dict) and payload.get("version") == REPORT_NARRATIVE_VERSION:
            return payload
    return None


def translate_report_narrative_payload(
    payload: dict[str, Any],
    *,
    target_lang: str,
    analyzer,
) -> dict[str, Any] | None:
    """Translate persisted report prose without changing evidence or scores."""
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
            "You are a precise report translator for Brand3. Return only valid JSON. "
            "Translate prose into the requested language without adding analysis, facts, "
            "recommendations, evidence, URLs, or claims. Preserve all URLs, evidence_urls, "
            "dimension keys, scores, proper nouns, and product names. Do not translate literal "
            "quoted evidence unless it appears inside a narrative sentence."
        ),
        user=(
            f"Target language: {target_lang}\n\n"
            "Translate this Brand Audit narrative JSON. Preserve the exact schema.\n"
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
            "version": REPORT_NARRATIVE_VERSION,
            "source": "report_narrative",
            "translation_version": REPORT_TRANSLATION_VERSION,
            "translation_source": REPORT_TRANSLATION_SOURCE,
            "target_lang": target_lang,
            "translated_at": datetime.now().isoformat(),
            "run_id": payload.get("run_id"),
        }
    )
    return translated


def _translation_input(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "synthesis_prose": str(payload.get("synthesis_prose") or payload.get("summary") or ""),
        "summary": str(payload.get("summary") or payload.get("synthesis_prose") or ""),
        "tensions_prose": str(payload.get("tensions_prose") or ""),
        "findings_by_dimension": payload.get("findings_by_dimension") or {},
    }


def _has_translatable_text(payload: dict[str, Any]) -> bool:
    if payload.get("synthesis_prose") or payload.get("summary") or payload.get("tensions_prose"):
        return True
    findings = payload.get("findings_by_dimension")
    if not isinstance(findings, dict):
        return False
    for items in findings.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("title") or item.get("observation") or item.get("implication"):
                return True
    return False


def _validated_translation(source: dict[str, Any], result: dict[str, Any]) -> dict[str, Any] | None:
    findings = result.get("findings_by_dimension")
    if not isinstance(findings, dict):
        return None
    source_findings = source.get("findings_by_dimension")
    if not isinstance(source_findings, dict):
        source_findings = {}

    validated_findings: dict[str, list[dict[str, Any]]] = {}
    for dimension, source_items in source_findings.items():
        translated_items = findings.get(dimension)
        if not isinstance(source_items, list) or not isinstance(translated_items, list):
            validated_findings[dimension] = source_items if isinstance(source_items, list) else []
            continue
        validated_findings[dimension] = [
            _validated_finding(source_item, translated_item)
            for source_item, translated_item in zip(source_items, translated_items)
            if isinstance(source_item, dict) and isinstance(translated_item, dict)
        ]
        if len(validated_findings[dimension]) < len(source_items):
            validated_findings[dimension].extend(source_items[len(validated_findings[dimension]):])

    synthesis = _clean_text(result.get("synthesis_prose")) or source.get("synthesis_prose", "")
    summary = _clean_text(result.get("summary")) or synthesis
    return {
        "synthesis_prose": synthesis,
        "summary": summary,
        "tensions_prose": _clean_text(result.get("tensions_prose")),
        "findings_by_dimension": validated_findings,
    }


def _validated_finding(source_item: dict[str, Any], translated_item: dict[str, Any]) -> dict[str, Any]:
    return {
        **source_item,
        "title": _clean_text(translated_item.get("title")) or str(source_item.get("title") or ""),
        "observation": _clean_text(translated_item.get("observation"))
        or str(source_item.get("observation") or source_item.get("prose") or ""),
        "implication": _clean_text(translated_item.get("implication"))
        or str(source_item.get("implication") or ""),
        "typical_decision": _clean_text(translated_item.get("typical_decision"))
        or str(source_item.get("typical_decision") or ""),
        "evidence_urls": [
            str(url)
            for url in (source_item.get("evidence_urls") or [])
            if isinstance(url, str)
        ],
    }


def _clean_text(value: Any) -> str:
    return str(value or "").strip()
