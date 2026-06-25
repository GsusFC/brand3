"""Shared runtime helpers for Magnetism Scanner routes."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from typing import Literal

from src.config import BRAND3_DB_PATH
from src.features.magnetism.moodboard import build_moodboard_model, extract_moodboard_images
from ..scan_links import sv9_scan_id_for_run
from src.storage.sqlite_store import SQLiteStore

from ..observatory_index import build_observatory_index
from .magnetism_scanner_ui_copy import _MAGNETISM_UI

_Log = logging.getLogger(__name__)

_Lang = Literal["es", "en"]


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


def _sv9_scan_id_for_run(source_run_id: object) -> int | None:
    return sv9_scan_id_for_run(source_run_id, db_path=BRAND3_DB_PATH)


async def _attach_sv9_link(model: dict) -> None:
    """Nav link to the SV9 scan for this run, when one exists."""
    model.setdefault("sv9_scan_id", None)
    source_run_id = model.get("source_run_id")
    if not source_run_id:
        return
    scan_id = await asyncio.to_thread(_sv9_scan_id_for_run, source_run_id)
    if isinstance(scan_id, int):
        model["sv9_scan_id"] = scan_id


def _primary_scan_ready_href(row: dict, *, lang: _Lang = "es") -> str:
    sv9_scan_id = _sv9_scan_id_for_run(row.get("source_run_id"))
    if sv9_scan_id:
        return _with_lang(f"/sv9/scan/{sv9_scan_id}", lang)
    return _with_lang("/magnetism-scanner/scan/{}".format(row["id"]), lang)


def _ui(lang: _Lang) -> dict:
    labels = dict(_MAGNETISM_UI["en"])
    labels.update(_MAGNETISM_UI.get(lang, {}))
    return labels


def _lang_q(lang: _Lang) -> str:
    return f"?lang={lang}"


def _with_lang(path: str, lang: _Lang) -> str:
    return f"{path}{_lang_q(lang)}"


def _load_magnetism_index_data(
    *,
    query: str | None = None,
    sort: str = "newest",
    category: str | None = None,
    tag: str | None = None,
    page: int = 1,
    lang: _Lang = "es",
) -> dict:
    observatory = build_observatory_index(
        db_path=BRAND3_DB_PATH,
        query=query,
        sort=sort,
        category=category,
        tag=tag,
        page=page,
        per_page=25,
        lang=lang,
    )
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        audit_runs = store.list_runs(limit=12)
    finally:
        store.close()
    return {"observatory": observatory, "audit_runs": audit_runs}


def _load_run_summary(run_id: int) -> dict | None:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        return store.get_run_summary(run_id)
    finally:
        store.close()


def _inflight_moodboard_images(row: dict) -> list[dict]:
    """Best-effort representative images for an in-flight scan."""
    brand_name = str(row.get("brand_name") or "").strip()
    url = str(row.get("url") or "").strip()
    if not brand_name or not url or url in ("manual", "Manual Upload"):
        return []
    try:
        store = SQLiteStore(BRAND3_DB_PATH)
        try:
            payload = store.get_latest_raw_input(brand_name, url, "web", max_age_hours=24)
        finally:
            store.close()
    except Exception:
        _Log.exception("Failed to load in-flight moodboard images for %s", brand_name)
        return []
    if not isinstance(payload, dict):
        return []
    return extract_moodboard_images(payload)


def _moodboard_model(model: dict) -> dict:
    """Build the moodboard view model from the scan's persisted source run."""
    web_payload: dict | None = None
    brand_logo_url: str | None = None
    source_run_id = model.get("source_run_id")
    if source_run_id:
        store = SQLiteStore(BRAND3_DB_PATH)
        try:
            snapshot = store.get_run_snapshot(int(source_run_id))
        finally:
            store.close()
        if snapshot:
            brand_logo_url = (snapshot.get("run") or {}).get("brand_logo_url")
            for item in snapshot.get("raw_inputs") or []:
                if item.get("source") == "web" and isinstance(item.get("payload"), dict):
                    web_payload = item["payload"]
    return build_moodboard_model(
        model.get("payload") or {},
        web_payload,
        brand_logo_url=brand_logo_url,
    )


def _elapsed(started_at: str | None) -> int:
    if not started_at:
        return 0
    try:
        dt = datetime.fromisoformat(str(started_at).replace(" ", "T"))
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))


def _elapsed_label(seconds: int) -> str:
    minutes, rest = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{rest:02d}"


def _magnetism_phase(row: dict) -> str:
    phase = row.get("phase") or row.get("status") or "queued"
    if row.get("status") == "queued":
        return "queued"
    if row.get("status") == "failed":
        return "failed"
    if row.get("status") == "ready":
        return "ready"
    return str(phase)


def _phase_steps(
    phases: list[tuple[str, str]],
    current_phase: str,
    status: str,
    *,
    lang: _Lang = "es",
) -> list[dict]:
    if status == "failed":
        current_phase = "failed"
    if status == "ready":
        current_phase = "ready"

    current_index = next(
        (idx for idx, (key, _label) in enumerate(phases) if key == current_phase),
        -1,
    )
    steps = []
    for idx, (key, label) in enumerate(phases):
        if current_phase == "ready" or (current_index >= 0 and idx < current_index):
            state = "done"
        elif key == current_phase:
            state = "active"
        elif current_phase == "failed" and current_index >= 0 and idx == current_index:
            state = "failed"
        else:
            state = "pending"
        steps.append({"key": key, "label": label, "state": state})
    if current_phase == "failed":
        steps.append({"key": "failed", "label": _MAGNETISM_PHASE_FINAL_LABELS[lang]["failed"], "state": "failed"})
    if current_phase == "ready":
        steps.append({"key": "ready", "label": _MAGNETISM_PHASE_FINAL_LABELS[lang]["ready"], "state": "done"})
    return steps


def _sv9_generation_copy(lang: _Lang) -> dict:
    return _SV9_GENERATION_STATUS_COPY.get(lang, _SV9_GENERATION_STATUS_COPY["es"])


def _sv9_generation_phase(job: dict) -> str:
    status = str(job.get("status") or "queued")
    if status == "queued":
        return "queued"
    if status == "failed":
        return "failed"
    if status == "ready":
        return "ready"
    phase = str(job.get("phase") or "queued")
    return phase if phase in {"queued", "generating", "saving"} else "generating"


def _sv9_generation_phase_label(phase: str, status: str | None, *, lang: _Lang = "es") -> str:
    if status == "ready":
        return "SV9 ready" if lang == "en" else "SV9 listo"
    if status == "failed":
        return "SV9 failed" if lang == "en" else "SV9 fallido"
    for key, label in _SV9_GENERATION_PHASES[lang]:
        if key == phase:
            return label
    return "Generating SV9" if lang == "en" else "Generando SV9"


def _sv9_generation_phase_steps(
    phase: str,
    status: str | None,
    *,
    lang: _Lang = "es",
) -> list[dict]:
    phases = _SV9_GENERATION_PHASES[lang]
    current_phase = phase
    if status == "failed":
        current_phase = "failed"
    if status == "ready":
        current_phase = "ready"

    current_index = next(
        (idx for idx, (key, _label) in enumerate(phases) if key == current_phase),
        -1,
    )
    steps = []
    for idx, (key, label) in enumerate(phases):
        if current_phase == "ready" or (current_index >= 0 and idx < current_index):
            state = "done"
        elif key == current_phase:
            state = "active"
        elif current_phase == "failed" and current_index >= 0 and idx == current_index:
            state = "failed"
        else:
            state = "pending"
        steps.append({"key": key, "label": label, "state": state})
    if current_phase == "failed":
        steps.append({"key": "failed", "label": "SV9 failed" if lang == "en" else "SV9 fallido", "state": "failed"})
    if current_phase == "ready":
        steps.append({"key": "ready", "label": "SV9 ready" if lang == "en" else "SV9 listo", "state": "done"})
    return steps


def _attach_ui(model: dict, lang: _Lang) -> None:
    model["lang"] = lang
    model["other_lang"] = "en" if lang == "es" else "es"
    model["lang_query"] = _lang_q(lang)
    model["t"] = _ui(lang)
