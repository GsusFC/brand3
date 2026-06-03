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


def translate_executive_analysis_v2(
    payload: dict[str, Any],
    *,
    target_lang: str,
    analyzer,
) -> dict[str, Any] | None:
    """Translate Brand Audit analyst pass prose while preserving its schema."""
    if target_lang not in {"es", "en"} or analyzer is None or not isinstance(payload, dict):
        return None
    call_json = getattr(analyzer, "_call_json", None)
    if not callable(call_json):
        return None

    source = _executive_analysis_translation_input(payload)
    if not _has_executive_analysis_text(source):
        return None

    result = call_json(
        system=(
            "You are a precise Brand3 analyst-pass translator. Return only valid JSON. "
            "Translate prose into the requested language without adding analysis, facts, "
            "recommendations, evidence, URLs, scores, or claims. Preserve exact dimension keys, "
            "list lengths where possible, proper nouns, product names, and confidence values."
        ),
        user=(
            f"Target language: {target_lang}\n\n"
            "Translate this Brand Audit executive_analysis_v2 JSON. Preserve the exact schema.\n"
            "JSON:\n"
            f"{json.dumps(source, ensure_ascii=False, sort_keys=True)}"
        ),
        max_tokens=6000,
    )
    if not isinstance(result, dict):
        return None
    translated = _validated_executive_analysis_translation(source, result)
    if not translated:
        return None
    translated.update(
        {
            "translation_version": REPORT_TRANSLATION_VERSION,
            "translation_source": REPORT_TRANSLATION_SOURCE,
            "target_lang": target_lang,
            "translated_at": datetime.now().isoformat(),
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


def _executive_analysis_translation_input(payload: dict[str, Any]) -> dict[str, Any]:
    dimensions = payload.get("dimensions") if isinstance(payload.get("dimensions"), dict) else {}
    return {
        "executive_summary": str(payload.get("executive_summary") or ""),
        "primary_risk": str(payload.get("primary_risk") or ""),
        "primary_opportunity": str(payload.get("primary_opportunity") or ""),
        "dimensions": {
            str(name): _executive_dimension_translation_input(item)
            for name, item in dimensions.items()
            if isinstance(item, dict)
        },
    }


def _executive_dimension_translation_input(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "diagnosis": str(item.get("diagnosis") or ""),
        "findings": _clean_string_list(item.get("findings")),
        "evidence": _clean_string_list(item.get("evidence")),
        "recommendation": str(item.get("recommendation") or ""),
        "confidence": str(item.get("confidence") or ""),
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


def _has_executive_analysis_text(payload: dict[str, Any]) -> bool:
    if payload.get("executive_summary") or payload.get("primary_risk") or payload.get("primary_opportunity"):
        return True
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, dict):
        return False
    for item in dimensions.values():
        if not isinstance(item, dict):
            continue
        if item.get("diagnosis") or item.get("recommendation"):
            return True
        if item.get("findings") or item.get("evidence"):
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


def _validated_executive_analysis_translation(source: dict[str, Any], result: dict[str, Any]) -> dict[str, Any] | None:
    dimensions = result.get("dimensions")
    if not isinstance(dimensions, dict):
        return None
    source_dimensions = source.get("dimensions")
    if not isinstance(source_dimensions, dict):
        source_dimensions = {}

    translated_dimensions: dict[str, dict[str, Any]] = {}
    for name, source_item in source_dimensions.items():
        translated_item = dimensions.get(name)
        if not isinstance(source_item, dict):
            continue
        translated_dimensions[name] = _validated_executive_dimension(
            source_item,
            translated_item if isinstance(translated_item, dict) else {},
        )

    return {
        "executive_summary": _clean_text(result.get("executive_summary")) or source.get("executive_summary", ""),
        "primary_risk": _clean_text(result.get("primary_risk")) or source.get("primary_risk", ""),
        "primary_opportunity": _clean_text(result.get("primary_opportunity")) or source.get("primary_opportunity", ""),
        "dimensions": translated_dimensions,
    }


def _validated_executive_dimension(source_item: dict[str, Any], translated_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "diagnosis": _clean_text(translated_item.get("diagnosis")) or str(source_item.get("diagnosis") or ""),
        "findings": _validated_string_list(source_item.get("findings"), translated_item.get("findings")),
        "evidence": _validated_string_list(source_item.get("evidence"), translated_item.get("evidence")),
        "recommendation": _clean_text(translated_item.get("recommendation")) or str(source_item.get("recommendation") or ""),
        "confidence": str(source_item.get("confidence") or translated_item.get("confidence") or ""),
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


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean_text(item) for item in value if _clean_text(item)]


def _validated_string_list(source_value: Any, translated_value: Any) -> list[str]:
    source_items = _clean_string_list(source_value)
    translated_items = _clean_string_list(translated_value)
    if not source_items:
        return []
    if not translated_items:
        return source_items
    if len(translated_items) < len(source_items):
        translated_items.extend(source_items[len(translated_items):])
    return translated_items[: len(source_items)]
