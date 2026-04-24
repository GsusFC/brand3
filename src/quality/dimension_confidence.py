"""Per-dimension confidence metadata.

This module deliberately does not alter scoring. It adds an explainability
layer over the existing features, evidence and run-level data quality.
"""

from __future__ import annotations

import ast
import json
from typing import Any

from src.dimensions import DIMENSIONS

_EVIDENCE_KEYS = (
    "evidence",
    "quotes",
    "examples",
    "messaging_gaps",
    "tone_examples",
    "evidence_snippet",
)


def dimension_confidence_from_features(
    features_by_dim: dict[str, dict[str, Any]],
    *,
    evidence_items: list[dict[str, Any]] | None = None,
    data_quality: str | None = None,
    context_summary: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    for dimension_name, features in (features_by_dim or {}).items():
        normalized[dimension_name] = [
            {
                "feature_name": feature_name,
                "confidence": getattr(feature, "confidence", 0.0),
                "source": getattr(feature, "source", ""),
                "raw_value": getattr(feature, "raw_value", None),
            }
            for feature_name, feature in (features or {}).items()
        ]
    return dimension_confidence_from_records(
        normalized,
        evidence_items=evidence_items,
        data_quality=data_quality,
        context_summary=context_summary,
    )


def dimension_confidence_from_snapshot(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    features_by_dim: dict[str, list[dict[str, Any]]] = {}
    for feature in snapshot.get("features") or []:
        dimension_name = feature.get("dimension_name") or ""
        features_by_dim.setdefault(dimension_name, []).append(feature)

    run = snapshot.get("run") or {}
    return dimension_confidence_from_records(
        features_by_dim,
        evidence_items=snapshot.get("evidence_items") or [],
        data_quality=run.get("data_quality"),
        context_summary=_context_summary_from_snapshot(snapshot),
    )


def dimension_confidence_from_records(
    features_by_dim: dict[str, list[dict[str, Any]]],
    *,
    evidence_items: list[dict[str, Any]] | None = None,
    data_quality: str | None = None,
    context_summary: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    evidence_by_dim: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_items or []:
        dim = item.get("dimension_name")
        if dim:
            evidence_by_dim.setdefault(dim, []).append(item)

    result: dict[str, dict[str, Any]] = {}
    for dimension_name, config in DIMENSIONS.items():
        expected = set((config.get("features") or {}).keys())
        records = features_by_dim.get(dimension_name) or []
        present = {
            record.get("feature_name")
            for record in records
            if record.get("feature_name") in expected
        }
        expected_count = max(len(expected), 1)
        coverage = round(min(1.0, len(present) / expected_count), 2)

        feature_confidences = [
            _as_float(record.get("confidence"))
            for record in records
            if record.get("feature_name") in expected
        ]
        avg_feature_confidence = (
            round(sum(feature_confidences) / len(feature_confidences), 2)
            if feature_confidences
            else 0.0
        )

        evidenced_features = {
            record.get("feature_name")
            for record in records
            if record.get("feature_name") in expected and _has_feature_evidence(record)
        }
        evidence_coverage = len(evidenced_features) / expected_count
        if evidence_by_dim.get(dimension_name):
            evidence_coverage += 0.25
        evidence_coverage = round(min(1.0, evidence_coverage), 2)

        confidence = round(
            (0.5 * avg_feature_confidence)
            + (0.3 * coverage)
            + (0.2 * evidence_coverage),
            2,
        )

        reasons: list[str] = []
        if coverage < 0.3:
            reasons.append("low_coverage")
        if avg_feature_confidence < 0.6:
            reasons.append("low_feature_confidence")
        if evidence_coverage < 0.25:
            reasons.append("no_evidence")
        if data_quality == "insufficient":
            reasons.append("insufficient_data_quality")
        if (context_summary or {}).get("coverage", 1.0) < 0.3:
            reasons.append("context_low_coverage")

        status = "good"
        if coverage < 0.3:
            status = "insufficient_data"
        elif confidence < 0.6:
            status = "degraded"

        missing = sorted(expected - present)
        weak = sorted(
            record.get("feature_name")
            for record in records
            if record.get("feature_name") in expected
            and (_as_float(record.get("confidence")) < 0.35 or record.get("source") in ("none", ""))
        )
        missing_signals = missing + [name for name in weak if name not in missing]

        result[dimension_name] = {
            "coverage": coverage,
            "confidence": confidence,
            "status": status,
            "confidence_reason": reasons,
            "missing_signals": missing_signals,
            "recommended_next_steps": _recommended_next_steps(missing_signals, reasons),
            "feature_confidence": avg_feature_confidence,
            "evidence_coverage": evidence_coverage,
        }
    return result


def _recommended_next_steps(missing_signals: list[str], reasons: list[str]) -> list[str]:
    steps: list[str] = []
    for reason in reasons:
        step = _REASON_STEPS.get(reason)
        if step and step not in steps:
            steps.append(step)
    for signal in missing_signals:
        step = _SIGNAL_STEPS.get(signal)
        if step and step not in steps:
            steps.append(step)
    return steps[:4]


def _context_summary_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    for item in reversed(snapshot.get("raw_inputs") or []):
        if item.get("source") == "context" and isinstance(item.get("payload"), dict):
            payload = item["payload"]
            return {
                "coverage": _as_float(payload.get("coverage")),
                "confidence": _as_float(payload.get("confidence")),
            }
    return {}


def _has_feature_evidence(record: dict[str, Any]) -> bool:
    raw = _parse_raw(record.get("raw_value"))
    if isinstance(raw, dict):
        for key in _EVIDENCE_KEYS:
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return True
            if isinstance(value, (list, tuple)) and len(value) > 0:
                return True
    if isinstance(raw, list):
        return len(raw) > 0
    return False


def _parse_raw(raw_value: Any) -> Any:
    if isinstance(raw_value, (dict, list)):
        return raw_value
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    try:
        return json.loads(raw_value)
    except Exception:
        pass
    try:
        return ast.literal_eval(raw_value)
    except Exception:
        return raw_value


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


_REASON_STEPS = {
    "low_coverage": "Ampliar cobertura de fuentes antes de interpretar la dimension.",
    "low_feature_confidence": "Revisar senales debiles o sustituir heuristicas por evidencia directa.",
    "no_evidence": "Anadir evidencia trazable con cita o URL para soportar la lectura.",
    "insufficient_data_quality": "Repetir el analisis con inputs primarios completos.",
    "context_low_coverage": "Mejorar el pre-scan contextual del sitio antes del analisis profundo.",
}

_SIGNAL_STEPS = {
    "visual_consistency": "Capturar screenshots y validar consistencia visual entre paginas clave.",
    "messaging_consistency": "Comparar claims principales de la web con menciones externas.",
    "tone_consistency": "Contrastar tono propio con citas de terceros.",
    "cross_channel_coherence": "Detectar enlaces oficiales a redes, contacto y touchpoints externos.",
    "web_presence": "Verificar que la web sea accesible, segura y con identidad clara.",
    "social_footprint": "Conectar senales sociales relevantes para la categoria.",
    "search_visibility": "Medir resultados de busqueda y menciones indexadas de la marca.",
    "directory_presence": "Buscar presencia en directorios, marketplaces o listings del sector.",
    "brand_sentiment": "Recolectar menciones externas suficientes para estimar sentimiento.",
    "mention_volume": "Aumentar cobertura de noticias, blogs y menciones publicas.",
    "sentiment_trend": "Comparar menciones recientes contra historicas para detectar tendencia.",
    "review_quality": "Incorporar reviews verificables o ratings agregados cuando existan.",
    "positioning_clarity": "Extraer el posicionamiento principal y contrastarlo con competidores.",
    "uniqueness": "Medir lenguaje propio frente a frases genericas del sector.",
    "competitor_distance": "Definir competidores comparables y calcular distancia de posicionamiento.",
    "content_authenticity": "Auditar profundidad y originalidad del contenido clave.",
    "brand_personality": "Evaluar voz de marca en paginas owned y menciones externas.",
    "content_recency": "Detectar fechas de publicaciones recientes en blog, changelog o noticias.",
    "publication_cadence": "Medir cadencia de publicacion en los ultimos 12 meses.",
    "momentum": "Buscar senales recientes de lanzamientos, actividad o crecimiento.",
}
