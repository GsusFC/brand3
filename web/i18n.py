"""Shared language helpers for the Brand3 web UI."""

from __future__ import annotations

from typing import Literal

_Lang = Literal["es", "en"]


def normalize_lang(value: str | None, default: _Lang = "es") -> _Lang:
    if value in ("es", "en"):
        return value
    return default


def lang_suffix(lang: _Lang) -> str:
    return f"?lang={lang}" if lang == "en" else ""


def magnetism_landing_copy(lang: _Lang) -> dict[str, str]:
    """Shared entry copy so home and scanner stay aligned."""
    if lang == "es":
        return {
            "title": "Escáner de Magnetismo",
            "intro": "Empieza aquí. Usa el escáner para abrir un análisis; Brand Audit sigue disponible como ruta dedicada.",
            "button": "Ejecutar escáner",
        }
    return {
        "title": "Magnetism Scanner",
        "intro": "Start here. Use the scanner to open an analysis; Brand Audit remains available as a dedicated route.",
        "button": "Run scanner",
    }
