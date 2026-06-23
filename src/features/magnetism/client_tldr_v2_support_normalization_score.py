"""Scoring and score-provenance helpers for client TLDR v2 normalization."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_SCORE_LABELS = {
    "en": {
        "computed": "Calculated score",
        "reviewed": "Reviewed score",
        "blocked": "Score withheld",
        "limited_confidence": "Limited-confidence score",
        "unavailable": "Score unavailable",
    },
    "es": {
        "computed": "Score calculado",
        "reviewed": "Score revisado",
        "blocked": "Score retenido",
        "limited_confidence": "Score con confianza limitada",
        "unavailable": "Score no disponible",
    },
}


_SCORE_NOTES = {
    "en": {
        "computed": "Based on the current evidence set.",
        "reviewed": "A human-reviewed score is available for display.",
        "blocked": "The score is being held back until the technical review settles.",
        "limited_confidence": "The score is usable, but the underlying check is limited.",
        "unavailable": "No displayable score is available for this run.",
    },
    "es": {
        "computed": "Basado en el conjunto de evidencia actual.",
        "reviewed": "Hay un score revisado por una persona disponible para mostrar.",
        "blocked": "El score se retiene hasta que se resuelva la revisión técnica.",
        "limited_confidence": "El score es utilizable, pero la base de verificación sigue siendo limitada.",
        "unavailable": "No hay un score mostrable para esta ejecución.",
    },
}


_SYSTEM_READING_LABELS = {
    "en": {
        "credibility_support": "Credibility support",
        "strategic_tensions": "Strategic tensions",
        "validation_questions": "Validation questions",
        "diagnosis": "Diagnosis",
        "limitations": "Limitations",
    },
    "es": {
        "credibility_support": "Soporte de credibilidad",
        "strategic_tensions": "Tensiones estratégicas",
        "validation_questions": "Preguntas de validación",
        "diagnosis": "Diagnóstico",
        "limitations": "Limitaciones",
    },
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _normalize_score_reading(
    raw: Any,
    provenance: dict[str, Any],
    lang: str,
    *,
    score_note: str | None = None,
) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    fallback = _build_score_reading(provenance, lang)
    status = fallback["status"]
    value = fallback.get("value")
    label = fallback["label"]
    note = (
        fallback["note"]
        if value is not None
        else (_clean_text(source.get("note")) or _clean_text(score_note) or fallback["note"])
    )
    confidence = fallback["confidence"]
    return {
        "status": status,
        "display_source": fallback.get("display_source"),
        "label": label,
        "note": note,
        "value": value,
        "confidence": confidence,
        "limited_confidence": fallback.get("limited_confidence", False) or status == "limited_confidence",
    }


def _client_score_provenance(
    score_provenance: dict[str, Any],
    *,
    scanner_display_score: Any | None,
) -> dict[str, Any]:
    """Prefer the persisted Magnetism scan score for client TLDR display."""
    provenance = deepcopy(score_provenance or {})
    score = _display_score_number(scanner_display_score)
    if score is None:
        return provenance
    if (
        provenance.get("display_score_source") != "blocked"
        and provenance.get("recommended_display_score") is not None
    ):
        return provenance

    provenance["display_score_source"] = "computed"
    provenance["recommended_display_score"] = score
    provenance["client_display_score_source"] = "magnetism_scan"
    provenance["client_score_fallback"] = {
        "source": "magnetism_scan",
        "reason": "audit_display_blocked",
    }
    return provenance


def _display_score_number(value: Any) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0 or score > 100:
        return None
    return score


def _build_score_reading(provenance: dict[str, Any], lang: str) -> dict[str, Any]:
    replay = provenance.get("replay_integrity") or {}
    status = str(replay.get("status") or "unavailable")
    display_source = str(provenance.get("display_score_source") or "blocked")
    limited_confidence = status == "unverifiable"

    if display_source == "reviewed":
        status_key = "reviewed"
    elif display_source == "computed":
        status_key = "limited_confidence" if limited_confidence else "computed"
    elif display_source == "blocked":
        status_key = "blocked"
    else:
        status_key = "unavailable"

    value = provenance.get("recommended_display_score")
    if status_key == "blocked":
        value = None

    note_key = status_key if status_key in _SCORE_NOTES[lang] else "unavailable"
    return {
        "status": status_key,
        "display_source": display_source,
        "label": _SCORE_LABELS[lang][note_key],
        "note": _SCORE_NOTES[lang][note_key],
        "value": value,
        "confidence": "low" if status_key in {"blocked", "limited_confidence", "unavailable"} else "high",
        "limited_confidence": limited_confidence,
    }

