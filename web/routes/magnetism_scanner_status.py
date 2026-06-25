"""Status and loader routes for the Magnetism Scanner."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ..templates_env import templates
from .magnetism_scanner import (
    _Lang,
    _elapsed,
    _elapsed_label,
    _inflight_moodboard_images,
    _lang_q,
    _magnetism_phase,
    _phase_steps,
    _primary_scan_ready_href,
    _ui,
    _with_lang,
)
from ..storage import get_magnetism_scan_by_token
from ..scan_links import sv9_scan_id_for_run
from ..scanner_api.models import scanner_failure_diagnostics_from_row as _scanner_failure_diagnostics


# Compatibility import kept for historical internal references and to avoid broad
# signature churn in existing call sites.
scanner_failure_diagnostics_from_row = _scanner_failure_diagnostics


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

router = APIRouter()


@router.get("/magnetism-scanner/{token}/status")
async def magnetism_scanner_status(request: Request, token: str, lang: _Lang = Query("es")):
    """Render the shared waiting page for an in-flight Magnetism scan."""
    row = await asyncio.to_thread(get_magnetism_scan_by_token, token)
    if row is None:
        return _scan_status_not_found_response(request, token, lang)
    if row.get("status") == "ready":
        return RedirectResponse(_primary_scan_ready_href(row, lang=lang), status_code=303)

    phase = _magnetism_phase(row)
    phase_labels = {
        **{key: label for key, label in _MAGNETISM_PHASES[lang]},
        **_MAGNETISM_PHASE_FINAL_LABELS[lang],
    }
    status_copy = _MAGNETISM_STATUS_COPY[lang]
    elapsed_seconds = _elapsed(row.get("started_at"))
    elapsed_label = _elapsed_label(elapsed_seconds)
    return templates.TemplateResponse(
        request,
        "status.html.j2",
        _build_scanner_status_context(
            row=row,
            token=token,
            lang=lang,
            phase=phase,
            phase_label=phase_labels.get(phase, "Working" if lang == "en" else "Trabajando"),
            phase_steps=_phase_steps(_MAGNETISM_PHASES[lang], phase, row.get("status") or "queued", lang=lang),
            failure_diagnostics=_scanner_failure_diagnostics(row),
            elapsed_seconds=elapsed_seconds,
            elapsed_label=elapsed_label,
            status_copy=status_copy,
            ready_href=_primary_scan_ready_href(row, lang=lang),
            back_href=_with_lang("/magnetism-scanner", lang),
        ),
    )


@router.get("/magnetism-scanner/{token}/assets")
async def magnetism_scanner_assets(token: str):
    """Stream representative brand images discovered so far for the loader.

    Polled by the waiting-screen scan loader; returns a small JSON document with
    the current phase plus whatever imagery acquisition has already captured.
    """
    row = get_magnetism_scan_by_token(token)
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown scan token.")
    status = str(row.get("status") or "queued")
    phase = _magnetism_phase(row)
    images: list[dict] = []
    if status in ("queued", "running"):
        images = _inflight_moodboard_images(row)
    return {"status": status, "phase": phase, "images": images}
