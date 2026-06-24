"""Status and loader routes for the Magnetism Scanner."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ..templates_env import templates
from .magnetism_scanner_impl import (
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
from .magnetism_scanner_status_copy import (
    _LOADER_PHASE_CAPTIONS,
    _MAGNETISM_PHASE_FINAL_LABELS,
    _MAGNETISM_PHASES,
    _MAGNETISM_STATUS_COPY,
)
from ..storage import get_magnetism_scan_by_token
from ..scan_links import sv9_scan_id_for_run
from ..scanner_api.models import scanner_failure_diagnostics_from_row as _scanner_failure_diagnostics


# Compatibility import kept for historical internal references and to avoid broad
# signature churn in existing call sites.
scanner_failure_diagnostics_from_row = _scanner_failure_diagnostics

router = APIRouter()


@router.get("/magnetism-scanner/{token}/status")
async def magnetism_scanner_status(request: Request, token: str, lang: _Lang = Query("es")):
    """Render the shared waiting page for an in-flight Magnetism scan."""
    row = await asyncio.to_thread(get_magnetism_scan_by_token, token)
    if row is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan token {token}", "ui_lang": lang},
            status_code=404,
        )
    if row.get("status") == "ready":
        return RedirectResponse(_primary_scan_ready_href(row, lang=lang), status_code=303)

    phase = _magnetism_phase(row)
    phase_labels = {
        **{key: label for key, label in _MAGNETISM_PHASES[lang]},
        **_MAGNETISM_PHASE_FINAL_LABELS[lang],
    }
    status_copy = _MAGNETISM_STATUS_COPY[lang]
    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {
            "ui_lang": lang,
            "token": token,
            "brand_slug": row.get("brand_name") or "brand scan",
            "status": row.get("status") or "queued",
            "elapsed_seconds": _elapsed(row.get("started_at")),
            "elapsed_label": _elapsed_label(_elapsed(row.get("started_at"))),
            "error_message": row.get("error_message"),
            "failure_diagnostics": _scanner_failure_diagnostics(row),
            "phase": phase,
            "phase_label": phase_labels.get(phase, "Working" if lang == "en" else "Trabajando"),
            "phase_steps": _phase_steps(_MAGNETISM_PHASES[lang], phase, row.get("status") or "queued", lang=lang),
            "assets_href": "/magnetism-scanner/{}/assets".format(token),
            "loader_phase_captions": _LOADER_PHASE_CAPTIONS[lang],
            "ready_href": _primary_scan_ready_href(row, lang=lang),
            "back_href": _with_lang("/magnetism-scanner", lang),
            "status_label": "brand_scanner_status",
            "typical_run_label": "3-5 min",
            "status_note": status_copy["note"],
            "queued_message": status_copy["queued"],
            "ready_message": status_copy["ready"],
            "ready_link_label": status_copy["ready_link"],
            "back_link_label": status_copy["back_link"],
            "failed_headline": status_copy["failed"],
            "retry_url": row.get("url") if (row.get("status") == "failed" and row.get("url") not in (None, "", "manual")) else None,
        },
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
