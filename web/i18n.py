"""Shared language helpers for the Brand3 web UI."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlencode

_Lang = Literal["es", "en"]


def normalize_lang(value: str | None, default: _Lang = "es") -> _Lang:
    if value in ("es", "en"):
        return value
    return default


def lang_suffix(lang: _Lang) -> str:
    return f"?lang={lang}" if lang == "en" else ""


def language_switch_url(request: object, lang: _Lang) -> str:
    """Current path with the requested UI language, preserving other query params."""
    path = getattr(getattr(request, "url", None), "path", "/") or "/"
    query_params = getattr(request, "query_params", None)
    pairs = []
    if query_params is not None:
        try:
            pairs = [(key, value) for key, value in query_params.multi_items() if key != "lang"]
        except AttributeError:
            pairs = [(key, value) for key, value in dict(query_params).items() if key != "lang"]
    pairs.append(("lang", lang))
    return f"{path}?{urlencode(pairs)}"


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
