"""Deterministic Spanish presentation guard for SV9 generated prose.

The SV9 scanner is a Spanish product surface. Source evidence may remain in the
source language, but Brand3-generated explanations (`motivo`,
`contexto_requerido`, `veredicto`, editorial messages and product-facing reason
codes) must not leak English when rendering the Spanish scanner.
"""

from __future__ import annotations

import re
from typing import Any

from src.sv9.rubric import COMPONENTS, ESTADO_NO, ESTADO_SIN_EVIDENCIA

_ENGLISH_PHRASE_RE = re.compile(
    r"\b("
    r"the snapshot|snapshot does not|does not provide|doesn't provide|does not include|"
    r"access to|full product interface|error states|transactional microcopy|"
    r"social media|product usage documentation|direct competitors|competitive analysis|"
    r"the brand idea|clearly articulated|consistently executed|cohesive visual system|"
    r"the available evidence|logged-in product|customer|competitor|requires evidence"
    r")\b",
    re.IGNORECASE,
)
_ENGLISH_WORD_RE = re.compile(
    r"\b(the|this|that|does|provide|include|access|full|product|interface|brand|idea|"
    r"clearly|executed|consistent|customer|competitor|social|media|documentation|"
    r"available|evidence|requires|logged|dashboard|states|microcopy)\b",
    re.IGNORECASE,
)
_SPANISH_WORD_RE = re.compile(
    r"\b(el|la|los|las|una|uno|que|marca|evidencia|snapshot|contexto|producto|"
    r"competidores|redes|requiere|aporta|no|sin|porque|para|con|del|de)\b",
    re.IGNORECASE,
)

_STATUS_LABELS_ES = {
    "reliable": "confiable",
    "usable": "usable",
    "shadow": "sombra",
    "broken": "rota",
    "canonical": "canónico",
    "non_canonical": "no canónico",
    "invalid": "inválido",
}

_REASON_LABELS_ES = {
    "scan_not_complete": "scan incompleto",
    "coherencia_needs_review": "coherencia requiere revisión",
    "components_not_detected": "componentes no detectados",
    "blind_spots_above_usable_threshold": "puntos ciegos por encima del umbral usable",
    "blind_spots_present": "puntos ciegos presentes",
    "needs_review": "requiere revisión",
    "usable_not_canonical": "usable, no canónico",
    "shadow_not_canonical": "sombra, no canónico",
    "invalid_scan_state": "estado de scan inválido",
}


def spanish_status_label(value: object) -> str:
    raw = str(value or "").strip()
    return _STATUS_LABELS_ES.get(raw, raw or "desconocido")


def spanish_reason_labels(codes: list[object] | tuple[object, ...] | None) -> list[str]:
    return [_REASON_LABELS_ES.get(str(code), str(code)) for code in (codes or [])]


def looks_like_generated_english(text: object) -> bool:
    """Detect common English LLM prose, while avoiding literal quote handling.

    This is intentionally conservative: it catches the exact failure family seen
    in SV9 reports without translating source-language evidence or short product
    phrases.
    """
    value = str(text or "").strip()
    if not value:
        return False
    if _ENGLISH_PHRASE_RE.search(value):
        return True
    english_hits = len(_ENGLISH_WORD_RE.findall(value))
    spanish_hits = len(_SPANISH_WORD_RE.findall(value))
    word_count = len(re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", value))
    return word_count >= 8 and english_hits >= 4 and spanish_hits == 0


def spanish_generated_text(text: object, fallback: str = "") -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    if looks_like_generated_english(value):
        return fallback
    return value


def spanish_tile_motivo(text: object, *, estado: object) -> str:
    fallback = (
        "El snapshot no aporta evidencia suficiente para evaluar esta baldosa sin contexto adicional."
        if str(estado or "") == ESTADO_SIN_EVIDENCIA
        else "El snapshot no comunica evidencia suficiente para encender esta baldosa."
    )
    return spanish_generated_text(text, fallback) or fallback


def spanish_tile_contexto(text: object) -> str:
    return spanish_generated_text(
        text,
        "Aporta contexto externo verificable: comparativa, experiencia de producto, canales activos o documentación operativa.",
    )


def spanish_component_verdict(component_key: str, text: object, tile_profile: list[Any] | None) -> str:
    value = str(text or "").strip()
    if value and not looks_like_generated_english(value):
        return value
    if not value:
        return ""
    return fallback_component_verdict(component_key, tile_profile or [])


def fallback_component_verdict(component_key: str, tile_profile: list[Any]) -> str:
    scale = int(COMPONENTS.get(component_key, {}).get("scale") or len(tile_profile) or 0)
    ok = sum(1 for item in tile_profile if _estado(item) == "ok")
    off = sum(1 for item in tile_profile if _estado(item) == ESTADO_NO)
    blind = sum(1 for item in tile_profile if _estado(item) == ESTADO_SIN_EVIDENCIA)
    parts = [f"{ok}/{scale} baldosas encendidas"]
    if off:
        parts.append(f"{off} apagada{'s' if off != 1 else ''}")
    if blind:
        parts.append(f"{blind} punto{'s' if blind != 1 else ''} ciego{'s' if blind != 1 else ''}")
    return "Síntesis automática: " + ", ".join(parts) + "."


def _estado(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("estado") or "")
    return str(getattr(item, "estado", "") or "")
