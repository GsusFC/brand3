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
            "title": "Brand3 Scanner",
            "intro": "Auditoría, evidencia y TLDR estratégico de una marca pública.",
            "button": "Analizar marca",
            "result_label": "Resultado incluido",
            "result_tldr": "TLDR Brand3",
            "result_audit": "Auditoría de Marca",
            "result_evidence": "Evidencia",
            "result_methodology": "Metodología",
        }
    return {
        "title": "Brand3 Scanner",
        "intro": "Brand audit, evidence, and strategic TLDR for a public brand.",
        "button": "Analyze brand",
        "result_label": "Included result",
        "result_tldr": "TLDR Brand3",
        "result_audit": "Brand Audit",
        "result_evidence": "Evidence",
        "result_methodology": "Methodology",
    }
