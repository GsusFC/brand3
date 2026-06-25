"""Readiness and context helpers for report derivation."""

from __future__ import annotations

import ast
import json
from datetime import datetime
from typing import Any

from src.quality.evidence_summary import summarize_evidence_records
from src.quality.report_readiness import evaluate_report_readiness
from src.quality.trust import quality_label
from src.reports.editorial_policy import (
    allowed_language_for_dimension_state,
    evidence_language_hint,
    label_dimension_state,
    label_report_mode,
    tone_for_dimension_state,
    tone_for_report_mode,
)


_DIMENSION_ORDER: tuple[str, ...] = (
    "coherencia",
    "presencia",
    "percepcion",
    "diferenciacion",
    "vitalidad",
)

_CORE_DIMENSIONS = ("coherencia", "diferenciacion", "presencia")

_OWNED_CONTENT_SOURCES = {
    "firecrawl",
    "browser_fallback",
    "owned_fallback",
    "official_related",
}


def parse_raw_value(raw: str | None) -> Any:
    """Parse stored raw_value. Tries literal_eval, then JSON, then returns as-is."""
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        return raw
    stripped = raw.strip()
    try:
        return ast.literal_eval(stripped)
    except (ValueError, SyntaxError, MemoryError):
        pass
    try:
        return json.loads(stripped)
    except (ValueError, TypeError):
        pass
    return raw


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def _format_analysis_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _presentation_policy_from_readiness(readiness: dict) -> dict:
    mode = readiness.get("report_mode") or ""
    dimension_states = readiness.get("dimension_states") or {}
    is_publishable = mode == "publishable_brand_report"
    is_technical_diagnostic = mode == "technical_diagnostic"
    is_insufficient_evidence = mode == "insufficient_evidence"

    if is_publishable:
        headline = "Publishable brand report"
        allow_editorial_conclusions = True
        allow_strategic_recommendations = True
    elif is_technical_diagnostic:
        headline = "Technical diagnostic"
        allow_editorial_conclusions = False
        allow_strategic_recommendations = False
    elif is_insufficient_evidence:
        headline = "Insufficient evidence"
        allow_editorial_conclusions = False
        allow_strategic_recommendations = False
    else:
        headline = "Unclassified report"
        allow_editorial_conclusions = False
        allow_strategic_recommendations = False

    return {
        "report_mode": mode,
        "is_publishable": is_publishable,
        "is_technical_diagnostic": is_technical_diagnostic,
        "is_insufficient_evidence": is_insufficient_evidence,
        "headline": headline,
        "summary": readiness.get("diagnostic_summary") or "",
        "allow_editorial_conclusions": allow_editorial_conclusions,
        "allow_strategic_recommendations": allow_strategic_recommendations,
        "dimension_presentation": {
            name: _dimension_presentation_policy(
                state,
                report_mode=mode,
                allow_editorial_conclusions=allow_editorial_conclusions,
            )
            for name, state in dimension_states.items()
        },
    }


def _dimension_presentation_policy(
    state: str,
    *,
    report_mode: str,
    allow_editorial_conclusions: bool,
) -> dict:
    if state == "not_evaluable":
        language_mode = "blocked"
    elif state == "observation_only":
        language_mode = "observational"
    elif report_mode == "technical_diagnostic" or state == "technical_only":
        language_mode = "technical_only"
    elif state == "ready" and allow_editorial_conclusions:
        language_mode = "editorial"
    elif state == "ready":
        language_mode = "technical_only"
    else:
        language_mode = "blocked"

    return {
        "state": state,
        "allow_strong_claims": (
            allow_editorial_conclusions
            and state == "ready"
            and language_mode == "editorial"
        ),
        "language_mode": language_mode,
    }


def _editorial_policy_from_readiness(readiness: dict) -> dict:
    mode = readiness.get("report_mode") or ""
    dimension_states = readiness.get("dimension_states") or {}
    return {
        "report_mode": mode,
        "report_mode_label": label_report_mode(mode),
        "report_tone": tone_for_report_mode(mode),
        "dimension_policies": {
            name: {
                "state": state,
                "state_label": label_dimension_state(state),
                "tone": tone_for_dimension_state(state),
                "allowed_language": allowed_language_for_dimension_state(state),
            }
            for name, state in dimension_states.items()
        },
        "evidence_policy": {
            evidence_type: evidence_language_hint(evidence_type)
            for evidence_type in (
                "direct",
                "indirect",
                "weak",
                "off_entity",
                "analysis_note",
                "fallback",
            )
        },
    }


def _readiness_features_from_snapshot(snapshot: dict) -> dict[str, list[dict]]:
    by_dimension: dict[str, list[dict]] = {}
    for feature in snapshot.get("features") or []:
        dimension_name = feature.get("dimension_name") or ""
        if not dimension_name:
            continue
        by_dimension.setdefault(dimension_name, []).append({
            "feature_name": feature.get("feature_name"),
            "value": feature.get("value"),
            "confidence": feature.get("confidence"),
            "source": feature.get("source") or "",
            "raw_value": feature.get("raw_value"),
        })
    return by_dimension


def _readiness_inputs_from_snapshot(
    snapshot: dict,
    *,
    evidence_summary: dict,
    confidence_summary: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "scores": _readiness_scores_from_snapshot(snapshot),
        "evidence_summary": _readiness_evidence_summary_from_snapshot(
            snapshot,
            fallback=evidence_summary,
        ),
        "confidence_summary": _readiness_confidence_from_snapshot(
            snapshot,
            fallback=confidence_summary,
        ),
        "features_by_dimension": _readiness_features_from_snapshot(snapshot),
    }


def _annotate_readiness_diagnostics(
    snapshot: dict,
    readiness: dict,
    *,
    context_readiness: dict,
) -> dict:
    annotated = dict(readiness)
    input_limitations = list(annotated.get("input_limitations") or [])
    warnings = list(annotated.get("warnings") or [])

    if _is_legacy_score_only_snapshot(snapshot):
        if "legacy_score_only_snapshot" not in input_limitations:
            input_limitations.append("legacy_score_only_snapshot")
        warning = "readiness_requires_evidence_and_confidence_metadata"
        if warning not in warnings:
            warnings.append(warning)

    annotated["input_limitations"] = input_limitations
    annotated["warnings"] = warnings
    annotated["diagnostic_summary"] = _readiness_diagnostic_summary(
        annotated,
        context_readiness=context_readiness,
    )
    return annotated


def _readiness_diagnostic_summary(readiness: dict, *, context_readiness: dict) -> str:
    mode = readiness.get("report_mode") or "unknown"
    dimension_states = readiness.get("dimension_states") or {}
    not_evaluable = _dimensions_with_state(dimension_states, "not_evaluable")
    technical_only = _dimensions_with_state(dimension_states, "technical_only")
    observation_only = _dimensions_with_state(dimension_states, "observation_only")
    input_limitations = readiness.get("input_limitations") or []

    if "legacy_score_only_snapshot" in input_limitations:
        return (
            "This is a legacy score-only snapshot. Readiness cannot be evaluated "
            "because the file lacks evidence and confidence metadata."
        )

    if mode == "publishable_brand_report":
        owned_capture = (context_readiness or {}).get("owned_content_capture") or {}
        context_note = ""
        if (
            (context_readiness or {}).get("raw_status", (context_readiness or {}).get("status"))
            == "insufficient_data"
            and owned_capture.get("usable_owned_content")
        ):
            context_note = " " + (
                owned_capture.get("message")
                or "Context pre-scan failed, but usable owned content was captured."
            )
        if observation_only:
            return (
                "This report has enough evidence and confidence for editorial use. "
                f"Some dimensions remain observation-only: {', '.join(observation_only)}."
                + context_note
            )
        return "This report has enough evidence and confidence for editorial use." + context_note

    if mode == "technical_diagnostic":
        reasons: list[str] = []
        if technical_only:
            reasons.append(f"technical-only dimensions: {', '.join(technical_only)}")
        if not_evaluable:
            reasons.append(f"not-evaluable dimensions: {', '.join(not_evaluable)}")
        if observation_only:
            reasons.append(f"observation-only dimensions: {', '.join(observation_only)}")
        if _context_is_limited(context_readiness):
            reasons.append("context readiness is limited")
        if not reasons:
            reasons.append("core dimensions lack enough supported evidence or confidence")
        return (
            "Technical diagnostic: the report can show scores and technical signals, "
            "but should not be treated as a publishable brand report because "
            + "; ".join(reasons)
            + "."
        )

    if mode == "insufficient_evidence":
        if not_evaluable:
            return (
                "Insufficient evidence: multiple dimensions are not evaluable "
                f"({', '.join(not_evaluable)})."
            )
        if _context_is_limited(context_readiness):
            return "Insufficient evidence: context readiness is limited."
        return "Insufficient evidence: required evidence or confidence metadata is missing."

    return "Readiness could not be classified from the available metadata."


def _dimensions_with_state(dimension_states: dict, state: str) -> list[str]:
    return [
        name
        for name, value in dimension_states.items()
        if value == state
    ]


def _context_is_limited(context_readiness: dict) -> bool:
    owned_capture = (context_readiness or {}).get("owned_content_capture") or {}
    if owned_capture.get("usable_owned_content"):
        return False
    return (context_readiness or {}).get("status") in {"degraded", "insufficient_data"}


def _is_legacy_score_only_snapshot(snapshot: dict) -> bool:
    dimensions = snapshot.get("dimensions")
    has_dimension_scores = isinstance(dimensions, dict) and any(
        name in dimensions for name in _DIMENSION_ORDER
    )
    if not has_dimension_scores:
        return False
    if snapshot.get("run") or snapshot.get("scores"):
        return False
    if snapshot.get("features") or snapshot.get("evidence_items"):
        return False
    if isinstance(snapshot.get("evidence_summary"), dict):
        return False
    if _looks_dimension_keyed(snapshot.get("confidence_summary")):
        return False
    if _looks_dimension_keyed(snapshot.get("dimension_confidence")):
        return False
    return True


def _readiness_scores_from_snapshot(snapshot: dict) -> dict[str, Any]:
    rows = snapshot.get("scores") or []
    if rows:
        return {
            row.get("dimension_name"): row.get("score")
            for row in rows
            if isinstance(row, dict) and row.get("dimension_name")
        }

    dimensions = snapshot.get("dimensions")
    if isinstance(dimensions, dict):
        return {
            dimension_name: score
            for dimension_name, score in dimensions.items()
            if dimension_name in _DIMENSION_ORDER
        }
    if isinstance(dimensions, list):
        scores: dict[str, Any] = {}
        for dimension in dimensions:
            if not isinstance(dimension, dict):
                continue
            name = dimension.get("name") or dimension.get("id") or dimension.get("dimension_name")
            if name:
                scores[name] = dimension.get("score")
        return scores
    return {}


def _readiness_evidence_summary_from_snapshot(snapshot: dict, *, fallback: dict) -> dict:
    existing = snapshot.get("evidence_summary")
    if isinstance(existing, dict):
        return existing
    return fallback


def _readiness_confidence_from_snapshot(
    snapshot: dict,
    *,
    fallback: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    confidence = snapshot.get("confidence_summary")
    if _looks_dimension_keyed(confidence):
        return _readiness_confidence_without_feature_penalty(snapshot, confidence)

    dimension_confidence = snapshot.get("dimension_confidence")
    if _looks_dimension_keyed(dimension_confidence):
        return _readiness_confidence_without_feature_penalty(snapshot, dimension_confidence)

    return fallback


def _readiness_confidence_without_feature_penalty(
    snapshot: dict,
    confidence: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if snapshot.get("features") or "dimensions" not in snapshot:
        return confidence

    sanitized: dict[str, dict[str, Any]] = {}
    for dimension_name, value in confidence.items():
        if isinstance(value, dict):
            sanitized[dimension_name] = dict(value)
            sanitized[dimension_name]["missing_signals"] = []
        else:
            sanitized[dimension_name] = value
    return sanitized


def _looks_dimension_keyed(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(key in value and isinstance(value.get(key), dict) for key in _DIMENSION_ORDER)


def _owned_content_capture_from_snapshot(snapshot: dict, *, evidence_summary: dict) -> dict:
    content_source = _content_source_from_snapshot(snapshot)
    dimensions_without_evidence = set(evidence_summary.get("dimensions_without_evidence") or [])
    core_dimensions_missing = sorted(
        dimension for dimension in _CORE_DIMENSIONS if dimension in dimensions_without_evidence
    )
    web_chars = _web_markdown_chars_from_snapshot(snapshot)
    usable_web_content = web_chars >= 200
    usable_owned_content = (
        content_source in _OWNED_CONTENT_SOURCES
        and not core_dimensions_missing
        and (usable_web_content or int(evidence_summary.get("total") or 0) > 0)
    )
    return {
        "available": bool(content_source),
        "content_source": content_source,
        "owned_like": content_source in _OWNED_CONTENT_SOURCES,
        "usable_web_content": usable_web_content,
        "web_text_chars": web_chars,
        "core_dimensions_missing_evidence": core_dimensions_missing,
        "usable_owned_content": usable_owned_content,
        "message": (
            f"Context pre-scan failed, but usable owned content was captured via {content_source}."
            if usable_owned_content and content_source
            else ""
        ),
    }


def _content_source_from_snapshot(snapshot: dict) -> str:
    data_sources = snapshot.get("data_sources")
    if isinstance(data_sources, dict) and data_sources.get("content_source"):
        return _as_str(data_sources.get("content_source")).strip()

    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") != "web":
            continue
        payload = item.get("payload") or {}
        if isinstance(payload, dict) and payload.get("content_source"):
            return _as_str(payload.get("content_source")).strip()

    for feature in snapshot.get("features") or []:
        raw = feature.get("raw_value")
        parsed = parse_raw_value(raw)
        if isinstance(parsed, dict) and parsed.get("content_source"):
            return _as_str(parsed.get("content_source")).strip()
        if isinstance(raw, str) and "content_source" in raw:
            try:
                literal = ast.literal_eval(raw.strip())
            except (ValueError, SyntaxError, MemoryError):
                literal = None
            if isinstance(literal, dict) and literal.get("content_source"):
                return _as_str(literal.get("content_source")).strip()

    return ""


def _web_markdown_chars_from_snapshot(snapshot: dict) -> int:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") != "web":
            continue
        payload = item.get("payload") or {}
        if isinstance(payload, dict):
            return len(_as_str(payload.get("markdown_content")).strip())
    return 0


def _effective_context_readiness_for_trust(
    context_readiness: dict,
    *,
    owned_content_capture: dict,
) -> dict:
    effective = dict(context_readiness or {})
    effective["raw_status"] = (context_readiness or {}).get("status")
    effective["owned_content_capture"] = owned_content_capture
    if (
        effective.get("status") == "insufficient_data"
        and owned_content_capture.get("usable_owned_content")
    ):
        effective["status"] = "good"
        effective["effective_status"] = "good"
        effective["message"] = owned_content_capture.get("message") or effective.get("message")
    return effective


def _context_readiness_from_snapshot(snapshot: dict) -> dict:
    raw_inputs = snapshot.get("raw_inputs") or []
    payload = None
    for item in reversed(raw_inputs):
        if item.get("source") == "context":
            payload = item.get("payload") or {}
            break
    if not isinstance(payload, dict):
        return {
            "available": False,
            "status": "insufficient_data",
            "coverage_label": "baja",
            "confidence_label": "baja",
            "message": "No context pre-scan was stored for this run.",
        }

    coverage = float(payload.get("coverage") or 0.0)
    confidence = float(payload.get("confidence") or 0.0)
    if coverage < 0.3:
        status = "insufficient_data"
    elif confidence < 0.6:
        status = "degraded"
    else:
        status = "good"
    return {
        "available": True,
        "status": status,
        "context_score": payload.get("context_score"),
        "coverage": coverage,
        "confidence": confidence,
        "coverage_label": quality_label(coverage),
        "confidence_label": quality_label(confidence),
        "robots_found": bool(payload.get("robots_found")),
        "sitemap_found": bool(payload.get("sitemap_found")),
        "sitemap_url_count": int(payload.get("sitemap_url_count") or 0),
        "llms_txt_found": bool(payload.get("llms_txt_found")),
        "llms_full_found": bool(payload.get("llms_full_found")),
        "ai_plugin_found": bool(payload.get("ai_plugin_found")),
        "schema_types": payload.get("schema_types") or [],
        "key_pages": payload.get("key_pages") or {},
        "avg_words": int(payload.get("avg_words") or 0),
        "avg_internal_links": int(payload.get("avg_internal_links") or 0),
        "confidence_reason": payload.get("confidence_reason") or [],
        "opportunities": payload.get("opportunities") or [],
    }


def _confidence_reason_labels(reasons: list[str]) -> list[str]:
    labels = [_confidence_reason_label(reason) for reason in reasons]
    return [label for label in labels if label]


def _confidence_reason_label(reason: str) -> str:
    labels = {
        "low_coverage": "",
        "low_feature_confidence": "confianza baja en señales",
        "no_evidence": "sin evidencia directa",
        "insufficient_data_quality": "calidad de datos insuficiente",
        "context_low_coverage": "pre-scan contextual limitado",
    }
    return labels.get(reason, reason.replace("_", " "))
