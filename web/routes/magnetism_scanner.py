"""FastAPI routes for the Brand3 Magnetism Scanner."""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from urllib.parse import urlparse

from typing import Literal

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from src.config import BRAND3_DB_PATH
from src.features.magnetism.moodboard import build_moodboard_model, extract_moodboard_images
from src.features.magnetism.client_tldr_v2 import build_client_tldr_v2
from src.features.magnetism.translation import apply_magnetism_translation
from src.features.magnetism.tldr_v2 import build_audit_aware_tldr_v2
from src.scoring.provenance import build_score_provenance_report
from src.reports.dossier import build_brand_dossier
from src.storage.sqlite_store import SQLiteStore
from src.research.evidence_semantic_llm import build_llm_semantic_assessment
from ..observatory_index import build_observatory_index
from ..scan_links import sv9_scan_id_for_run as _scan_links_sv9_scan_id_for_run

from ..i18n import magnetism_landing_copy
from ..storage import (
    get_magnetism_scan,
    get_magnetism_scan_by_token,
    get_sv9_generation_job,
    get_sv9_generation_job_by_scan_id,
    insert_magnetism_job,
    insert_magnetism_scan,
    insert_sv9_generation_job,
    update_sv9_generation_job,
)
from ..templates_env import templates
from ..workers.queue import get_queue
from ..workers.slug import slug_from_url
from ..workers import url_validator
from ..workers.url_validator import validate_url
from ..scanner_api.models import (
    scanner_failure_diagnostics_from_row as _scanner_failure_diagnostics,
    methodology_model as _methodology_model,
    normalized_scan_payload as _normalized_scan_payload,
    research_evidence_model as _research_evidence_model,
    scan_model_from_payload as _scan_model_from_payload,
    scanner_result_metadata_model as _scanner_result_metadata,
)
from .magnetism_scanner_ui_copy import _MAGNETISM_UI


_LOG = logging.getLogger(__name__)


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
    return _scan_links_sv9_scan_id_for_run(source_run_id, db_path=BRAND3_DB_PATH)


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
        _LOG.exception("Failed to load in-flight moodboard images for %s", brand_name)
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


class _ReportReadAnalyzer:
    """Keep scanner audit reads deterministic and side-effect free."""

    def _call(self, *args, **kwargs) -> str:
        return ""

    def _call_json(self, *args, **kwargs) -> dict:
        return {}


_REPORT_READ_ANALYZER = _ReportReadAnalyzer()


async def _run_sv9_generation_job(token: str) -> None:
    await _update_sv9_generation_job_async(
        token,
        status="running",
        phase="generating",
        phase_updated_at=datetime.now(timezone.utc).isoformat(),
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    job = await asyncio.to_thread(get_sv9_generation_job, token)
    if job is None:
        return
    try:
        await _update_sv9_generation_job_async(
            token,
            phase="generating",
            phase_updated_at=datetime.now(timezone.utc).isoformat(),
        )
        sv9_scan_id = await asyncio.to_thread(
            ensure_sv9_scan_for_source_run,
            int(job["source_run_id"]),
            db_path=BRAND3_DB_PATH,
        )
        if sv9_scan_id is None:
            raise RuntimeError("SV9 generation failed")
        await _update_sv9_generation_job_async(
            token,
            status="ready",
            phase="ready",
            sv9_scan_id=int(sv9_scan_id),
            phase_updated_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            error_message=None,
        )
    except Exception as exc:  # noqa: BLE001
        await _update_sv9_generation_job_async(
            token,
            status="failed",
            phase="failed",
            phase_updated_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            error_message=str(exc)[:500],
        )


async def _update_sv9_generation_job_async(token: str, **columns) -> None:
    await asyncio.to_thread(update_sv9_generation_job, token, **columns)


async def _magnetism_scan_model_async(scan_id: int, *, lang: _Lang = "es") -> dict | None:
    row = await asyncio.to_thread(get_magnetism_scan, scan_id)
    if row is None:
        return None

    payload = _normalized_scan_payload(row)
    payload = _payload_for_language(scan_id, payload, lang)
    model = _scan_model_from_payload(row, payload, scan_id=scan_id)
    model["display_name"] = _magnetism_display_name(
        str(model.get("brand_name") or ""),
        str(model.get("url") or ""),
    )
    model["display_url"] = _display_url(str(model.get("url") or ""))
    return model


def _magnetism_display_name(brand_name: str, url: str) -> str:
    raw_name = str(brand_name or "").strip()
    if raw_name and not _looks_like_url_or_domain(raw_name):
        return raw_name
    return _domain_label(url or raw_name) or raw_name or "Brand"


def _looks_like_url_or_domain(value: str) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith(("http://", "https://")) or ("." in text and " " not in text)


def _domain_label(url: str) -> str:
    parsed = urlparse(str(url or "").strip() if "://" in str(url or "") else f"https://{url}")
    host = (parsed.hostname or "").removeprefix("www.")
    if not host:
        return ""
    stem = host.split(".")[0]
    return stem.replace("-", " ").replace("_", " ").title()


def _display_url(url: str) -> str:
    value = str(url or "").strip()
    if value.startswith(("http://", "https://")):
        return value
    return ""


def _payload_for_language(scan_id: int, payload: dict, lang: _Lang) -> dict:
    """Apply cached Magnetism prose translations without mutating persisted scans."""
    translations = payload.get("translations")
    if not isinstance(translations, dict):
        translations = {}
    magnetism_translations = translations.get("magnetism_tldr")
    if not isinstance(magnetism_translations, dict):
        magnetism_translations = {}

    cached = magnetism_translations.get(lang)
    if isinstance(cached, dict):
        return apply_magnetism_translation(payload, cached)
    return payload


def _report_translation_payload(store: SQLiteStore, run_id: int, lang: _Lang) -> dict | None:
    if lang == "en":
        return None
    try:
        return store.get_report_translation(run_id, lang)
    except Exception:
        return None


def _load_audit_read_context(run_id: int, lang: _Lang) -> tuple[dict | None, dict | None, dict]:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
        narrative_payload = _report_translation_payload(store, run_id, lang)
        score_provenance = build_score_provenance_report(store, run_id)
        return snapshot, narrative_payload, score_provenance
    finally:
        store.close()


def _executive_analysis_for_language(
    audit_context: dict,
    narrative_payload: dict | None,
    lang: _Lang,
) -> dict:
    original = audit_context.get("executive_analysis_v2")
    if not isinstance(original, dict):
        original = {}
    if lang == "en":
        return original

    translated_from_report = (
        narrative_payload.get("executive_analysis_v2")
        if isinstance(narrative_payload, dict)
        else None
    )
    if isinstance(translated_from_report, dict) and translated_from_report:
        return translated_from_report

    translations = audit_context.get("executive_analysis_v2_translations")
    translated = translations.get(lang) if isinstance(translations, dict) else None
    if isinstance(translated, dict) and translated:
        return translated
    return original


def _internal_audit_summary_text(
    score_provenance: dict,
    tldr_v2: dict,
    *,
    lang: _Lang,
) -> str:
    state = tldr_v2.get("score_state") if isinstance(tldr_v2, dict) else {}
    if not isinstance(state, dict):
        state = {}

    computed = state.get("computed_composite_score")
    reviewed = state.get("reviewed_composite_score")
    display = state.get("recommended_display_score")
    source = str(state.get("display_score_source") or "blocked")
    integrity = str(state.get("score_integrity") or "unverifiable")
    drift_type = str(state.get("drift_type") or "none")
    score_values_match = state.get("score_values_match_persisted_data")
    limited_confidence = bool(state.get("limited_confidence"))
    fallback_flags = score_provenance.get("fallback_flags") if isinstance(score_provenance, dict) else {}
    neutral_fallback_dimensions = []
    if isinstance(fallback_flags, dict):
        neutral_fallback_dimensions = list(fallback_flags.get("replay_neutral_fallback_dimensions") or [])

    def _base_message() -> str:
        if lang == "en":
            if integrity == "valid":
                return "Score replay is valid. Persisted, recomputed and artifact scores match."
            if drift_type == "fingerprint_only_mismatch" and score_values_match is True:
                return "Score values match persisted data, but the scoring fingerprint differs from the current config. Treat as legacy/config mismatch, not data tampering."
            if drift_type == "artifact_mismatch" and score_values_match is True:
                return "Artifact score does not match persisted scoring data. Technical review required."
            if drift_type in {"feature_score_mismatch", "score_data_mismatch"}:
                return "Persisted score values differ from recomputed scoring data. Do not use as definitive."
            return "Replay could not verify this score with available persisted data."
        if integrity == "valid":
            return "La replay del score es válida. Los scores persistidos, recomputados y del artifact coinciden."
        if drift_type == "fingerprint_only_mismatch" and score_values_match is True:
            return "Los score values coinciden con los datos persistidos, pero el fingerprint de scoring difiere de la config actual. Trátalo como mismatch legacy/config, no como data tampering."
        if drift_type == "artifact_mismatch" and score_values_match is True:
            return "El score del artifact no coincide con los datos de scoring persistidos. Requiere revisión técnica."
        if drift_type in {"feature_score_mismatch", "score_data_mismatch"}:
            return "Los score values persistidos difieren de los datos recomputados. No lo uses como definitivo."
        return "La replay no pudo verificar este score con los datos persistidos disponibles."

    def _display_message() -> str:
        if source == "reviewed":
            if lang == "en":
                return f"Reviewed score {display} is the internal display recommendation; computed score is {computed}."
            return f"El score revisado {display} es la recomendación interna de display; el score computado es {computed}."
        if lang == "en":
            return f"Computed score {display} is the internal display recommendation."
        return f"El score computado {display} es la recomendación interna de display."

    if lang == "en":
        summary = _base_message()
        if source == "blocked":
            summary += " Display is blocked for internal use."
        else:
            summary += f" {_display_message()}"
        if reviewed is not None and source != "reviewed":
            summary += f" A reviewed score of {reviewed} is also present."
        if limited_confidence:
            summary += " Replay integrity is unverifiable, so treat this as limited confidence."
        if neutral_fallback_dimensions:
            summary += f" Neutral fallback 50.0 was used for: {', '.join(neutral_fallback_dimensions)}."
        return summary

    summary = _base_message()
    if source == "blocked":
        summary += " El display está bloqueado para uso interno."
    else:
        summary += f" {_display_message()}"
    if reviewed is not None and source != "reviewed":
        summary += f" También existe un score revisado de {reviewed}."
    if limited_confidence:
        summary += " La replay integrity es unverifiable, así que debe tratarse como confianza limitada."
    if neutral_fallback_dimensions:
        summary += f" El fallback neutral 50.0 se usó en: {', '.join(neutral_fallback_dimensions)}."
    return summary


def _internal_audit_status_label(score_state: dict, provenance: dict) -> str:
    integrity = str(score_state.get("score_integrity") or "unverifiable")
    source = str(score_state.get("display_score_source") or "blocked")
    if source == "blocked":
        return "blocked"
    if integrity == "valid":
        return "valid"
    if integrity == "unverifiable":
        return "review-required"
    if provenance.get("warnings"):
        return "warning"
    return "internal-only"


def _internal_audit_status_class(status_label: str) -> str:
    if status_label == "valid":
        return "badge-ready"
    if status_label == "blocked":
        return "badge-error"
    if status_label == "warning":
        return "badge-missing"
    if status_label == "review-required":
        return "badge-missing"
    return "badge"


def _internal_audit_display_decision(score_state: dict) -> str:
    source = str(score_state.get("display_score_source") or "blocked")
    if source == "reviewed":
        return "reviewed"
    if source == "computed":
        return "computed"
    return "blocked"


def _evidence_reliability_model(payload: dict) -> dict:
    quality = payload.get("research_pack_quality")
    if not isinstance(quality, dict):
        return {
            "available": False,
            "status": "missing",
            "total_score": None,
            "gate": {"passed": False, "failures": []},
            "dimensions": [],
            "warnings": [],
            "pack_summary": {},
            "reason": "missing_research_pack_quality",
        }

    raw_dimensions = quality.get("dimensions") if isinstance(quality.get("dimensions"), dict) else {}
    dimensions = []
    for name in ("offer", "audience", "differentiation", "frictions", "proof", "traceability", "noise"):
        dimension = raw_dimensions.get(name)
        if not isinstance(dimension, dict):
            continue
        dimensions.append(
            {
                "name": name,
                "label": name.replace("_", " ").title(),
                "score": dimension.get("score"),
                "status": dimension.get("status") or "unknown",
                "reasons": dimension.get("reasons") or [],
            }
        )

    gate = quality.get("gate") if isinstance(quality.get("gate"), dict) else {}
    return {
        "available": True,
        "version": quality.get("version") or "unknown",
        "status": quality.get("status") or "unknown",
        "total_score": quality.get("total_score"),
        "gate": {
            "passed": bool(gate.get("passed")),
            "failures": gate.get("failures") or [],
        },
        "dimensions": dimensions,
        "warnings": quality.get("warnings") or [],
        "pack_summary": quality.get("pack_summary") or {},
        "reason": quality.get("reason") or "",
    }


def ensure_sv9_scan_for_source_run(*args, **kwargs):
    from src.services.magnetism_service import ensure_sv9_scan_for_source_run as _service_ensure

    return _service_ensure(*args, **kwargs)


# Public router consumed by the app entrypoint.
from .magnetism_scanner_list import router as _list_router
from .magnetism_scanner_scan import router as _scan_router
from .magnetism_scanner_status import router as _status_router

router = APIRouter()
router.include_router(_list_router)
router.include_router(_status_router)
router.include_router(_scan_router)
