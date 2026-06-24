"""Static copy and status helpers used by Magnetism Scanner templates."""

from __future__ import annotations

from typing import Literal

from fastapi import Request

from ..templates_env import templates

_Lang = Literal["es", "en"]


def _scan_status_not_found_response(request: Request, token: str, lang: _Lang) -> object:
    return templates.TemplateResponse(
        request,
        "not_found.html.j2",
        {"resource": f"Magnetism scan token {token}", "ui_lang": lang},
        status_code=404,
    )


def _build_scanner_status_context(
    row: dict,
    token: str,
    lang: _Lang,
    phase: str,
    phase_label: str,
    phase_steps: list[dict],
    failure_diagnostics: object,
    elapsed_seconds: int,
    elapsed_label: str,
    status_copy: dict,
    ready_href: str,
    back_href: str,
) -> dict:
    return {
        "ui_lang": lang,
        "token": token,
        "brand_slug": row.get("brand_name") or "brand scan",
        "status": row.get("status") or "queued",
        "elapsed_seconds": elapsed_seconds,
        "elapsed_label": elapsed_label,
        "error_message": row.get("error_message"),
        "failure_diagnostics": failure_diagnostics,
        "phase": phase,
        "phase_label": phase_label,
        "phase_steps": phase_steps,
        "assets_href": "/magnetism-scanner/{}/assets".format(token),
        "loader_phase_captions": _LOADER_PHASE_CAPTIONS[lang],
        "ready_href": ready_href,
        "back_href": back_href,
        "status_label": "brand_scanner_status",
        "typical_run_label": "3-5 min",
        "status_note": status_copy["note"],
        "queued_message": status_copy["queued"],
        "ready_message": status_copy["ready"],
        "ready_link_label": status_copy["ready_link"],
        "back_link_label": status_copy["back_link"],
        "failed_headline": status_copy["failed"],
        "retry_url": row.get("url") if (row.get("status") == "failed" and row.get("url") not in (None, "", "manual")) else None,
    }


_MAGNETISM_PHASES = {
    "es": [
        ("queued", "En cola — un worker lo coge en segundos"),
        ("collecting", "Leyendo su web pública (~1 min)"),
        ("extracting", "Buscando qué dice el mundo de la marca (~1 min)"),
        ("interpreting", "Organizando la evidencia encontrada"),
        ("scoring", "Puntuando los componentes Brand3"),
        ("finalizing", "Escribiendo la lectura estratégica (~1-2 min)"),
    ],
    "en": [
        ("queued", "Queued — a worker picks it up in seconds"),
        ("collecting", "Reading its public website (~1 min)"),
        ("extracting", "Searching what the world says about the brand (~1 min)"),
        ("interpreting", "Organizing the evidence found"),
        ("scoring", "Scoring the Brand3 components"),
        ("finalizing", "Writing the strategic reading (~1-2 min)"),
    ],
}

_MAGNETISM_PHASE_FINAL_LABELS = {
    "es": {
        "ready": "Informe de marca listo",
        "failed": "Análisis de marca fallido",
    },
    "en": {
        "ready": "Brand report ready",
        "failed": "Brand analysis failed",
    },
}

_MAGNETISM_STATUS_COPY = {
    "es": {
        "note": "Un escaneo completo tarda 3-5 minutos. Puedes dejar esta pestaña abierta: te llevaremos al resultado solos.",
        "queued": "esperando turno de análisis",
        "ready": "abriendo informe ...",
        "ready_link": "→ abrir informe",
        "back_link": "← volver al scanner",
        "failed": "el escaneo no pudo completarse — suele ser temporal, reintenta en un minuto",
    },
    "en": {
        "note": "A full scan takes 3-5 minutes. Keep this tab open — we'll take you to the result automatically.",
        "queued": "waiting for analysis slot",
        "ready": "opening report ...",
        "ready_link": "→ open report",
        "back_link": "← back to scanner",
        "failed": "the scan could not complete — usually temporary, retry in a minute",
    },
}

_SV9_GENERATION_PHASES = {
    "es": [
        ("queued", "En cola"),
        ("generating", "Generando SV9"),
        ("saving", "Guardando scan"),
    ],
    "en": [
        ("queued", "Queued"),
        ("generating", "Generating SV9"),
        ("saving", "Saving scan"),
    ],
}

_SV9_GENERATION_STATUS_COPY = {
    "es": {
        "status_label": "Generación SV9",
        "status_note": "La página se actualiza cada 5 segundos mientras se materializa el scan sombra.",
        "queued_message": "esperando para materializar el scan sombra",
        "ready_message": "scan sombra listo ...",
        "ready_link_label": "→ abrir scan SV9",
        "back_link_label": "← volver al scan",
    },
    "en": {
        "status_label": "SV9 generation",
        "status_note": "Page auto-refreshes every 5 seconds while the shadow scan is materialized.",
        "queued_message": "waiting to materialize the shadow scan",
        "ready_message": "shadow scan ready ...",
        "ready_link_label": "→ open SV9 scan",
        "back_link_label": "← back to scan",
    },
}

_LOADER_PHASE_CAPTIONS = {
    "es": {
        "queued": "Inicializando el escáner…",
        "collecting": "Capturando señales de la marca…",
        "extracting": "Leyendo la firma visual…",
        "interpreting": "Interpretando el significado…",
        "scoring": "Puntuando los componentes Brand3…",
        "finalizing": "Componiendo el resultado…",
        "ready": "Escaneo completo.",
    },
    "en": {
        "queued": "Booting the scanner…",
        "collecting": "Capturing brand signals…",
        "extracting": "Reading the visual signature…",
        "interpreting": "Interpreting meaning…",
        "scoring": "Scoring the Brand3 components…",
        "finalizing": "Composing the result…",
        "ready": "Scan complete.",
    },
}
