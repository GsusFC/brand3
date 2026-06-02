"""FastAPI routes for the Brand3 Magnetism Scanner."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from typing import Literal

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH, BRAND3_LLM_API_KEY, LLM_CHEAP_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.extractor import MagnetismExtractor
from src.features.magnetism.translation import apply_magnetism_translation, translate_magnetism_payload
from src.storage.sqlite_store import SQLiteStore

from ..i18n import magnetism_landing_copy
from ..storage import (
    get_magnetism_scan,
    get_magnetism_scan_by_token,
    insert_magnetism_job,
    insert_magnetism_scan,
    list_magnetism_scans,
    update_magnetism_scan_payload,
)
from ..templates_env import templates
from ..workers.queue import get_queue
from ..workers.slug import slug_from_url
from ..workers.url_validator import validate_url

router = APIRouter()


_Lang = Literal["es", "en"]


_MAGNETISM_UI = {
    "en": {
        "language": "Language",
        "other_lang": "ES",
        "scanner_title": "Magnetism Scanner",
        "scanner_tag": "competitive analysis and 7-layer audit",
        "manual_summary": "Manual text block input (legacy/debug, not comparable)",
        "manual_label": "Raw website content / landing page copy:",
        "manual_placeholder": "Paste website homepage text copy here...",
        "manual_note": (
            "Manual input bypasses Brand Audit acquisition and is marked as legacy direct evidence. Use it "
            "only for debugging or ad-hoc review; production/comparable scans should use URL or an existing "
            "Brand Audit run."
        ),
        "from_audit": "from_brand_audit",
        "from_audit_tag": "reuse existing evidence packet",
        "from_audit_intro": (
            "Canonical path: generate Magnetism from an existing Brand Audit run. URL scans above create the "
            "same kind of Brand Audit snapshot first; this table simply reuses one that already exists."
        ),
        "use_evidence": "use evidence",
        "no_audits": "// no Brand Audit runs available yet — run a URL scan above or create a normal audit first.",
        "recent_scans": "recent_scans",
        "latest_runs": "latest runs",
        "view_sheet": "view sheet",
        "audit_score": "audit score",
        "no_scans": "// no magnetism scans recorded yet — run the first scan above.",
        "date": "date",
        "brand": "brand",
        "score": "score",
        "coherence": "coherence",
        "quadrant": "positioning quadrant",
        "url": "url",
        "run": "run",
        "result": "result",
        "back": "Back to Magnetism Scanner",
        "research_evidence": "Research Evidence",
        "evidence_reliability": "Evidence Reliability",
        "methodology_details": "Methodology Details",
        "detail_tag": "9 strategic blocks derived from 7 Magenta signals",
        "no_detected": "(not detected)",
        "system_reading": "TLDR System Reading",
        "system_reading_tag": "tensions and validation questions inside TLDR Brand3",
        "credibility_support": "Credibility support",
        "strategic_tensions": "Strategic tensions",
        "validation_questions": "Validation questions",
        "diagnosis": "diagnosis",
        "diagnosis_tag": "bounded by observed and missing signals",
        "limitations": "limitations",
        "research_intro": "Evidence graph and Research Pack used to produce the TLDR Brand3 reading.",
        "research_tag": "research evidence",
        "evidence_reliability_intro": (
            "Objective diagnostic for the Research Pack used as TLDR input. It evaluates evidence quality, "
            "not the brand, and does not change the TLDR blocks."
        ),
        "evidence_reliability_tag": "input quality, not brand quality",
        "quality_status": "Status",
        "quality_score": "Score",
        "quality_gate": "Gate",
        "quality_dimensions": "Quality dimensions",
        "quality_dimensions_tag": "offer, audience, proof, traceability, and noise",
        "quality_warnings": "Warnings",
        "quality_failures": "Gate failures",
        "quality_pack_summary": "Pack summary",
        "quality_missing": "No Research Pack quality diagnostic was persisted for this scan.",
        "no_quality_warnings": "No warnings persisted.",
        "no_quality_failures": "No gate failures.",
        "pack_source": "Pack Source",
        "tldr_mode": "TLDR Mode",
        "entity_resolution": "Entity Resolution",
        "entity_tag": "product and company boundaries",
        "research_pack": "Research Pack",
        "research_pack_tag": "normalized strategic inputs",
        "surface_map": "Surface Map",
        "surface_map_tag": "owned, product, proof, and external surfaces",
        "product_surfaces": "Product surfaces",
        "source_map": "Source map",
        "tldr_evidence": "TLDR Evidence",
        "tldr_evidence_tag": "what each block used",
        "rejected_gaps": "Rejected / Gaps",
        "rejected_gaps_tag": "bounded interpretation",
        "evidence_gaps": "Evidence gaps",
        "rejected_noise": "Rejected noise",
        "methodology_intro": "Method, interpretation rules, and limits behind this scan.",
        "methodology_tag": "methodology details",
        "research_pack_metric": "Research Pack",
        "tldr_generation": "TLDR Generation",
        "pipeline": "Pipeline",
        "pipeline_tag": "deterministic steps and LLM step",
        "block_method": "TLDR Block Method",
        "block_method_tag": "what each block is allowed to answer",
        "magenta_signals": "Magenta Circle Signals",
        "magenta_signals_tag": "7 technical inputs",
        "run_limits": "Run Limits",
        "run_limits_tag": "warnings and bounded interpretation",
        "source_basis": "Source basis",
        "validation_notes": "Validation notes",
        "no_validation_notes": "No validation notes were persisted for this scan.",
        "no_limitations": "No explicit limitations were persisted for this scan.",
        "no_clear_signal": "No clear signal detected in the provided sources.",
        "evidence": "Evidence",
    },
    "es": {
        "language": "Idioma",
        "other_lang": "EN",
        "scanner_title": "Escáner de Magnetismo",
        "scanner_tag": "análisis competitivo y auditoría de 7 capas",
        "manual_summary": "Entrada manual de texto (legacy/debug, no comparable)",
        "manual_label": "Contenido web bruto / copy de landing:",
        "manual_placeholder": "Pega aquí el texto de la homepage...",
        "manual_note": (
            "La entrada manual evita la adquisición de Brand Audit y se marca como evidencia directa legacy. "
            "Úsala solo para debug o revisión ad hoc; los escaneos comparables de producción deben usar URL "
            "o un Brand Audit existente."
        ),
        "from_audit": "desde_brand_audit",
        "from_audit_tag": "reutilizar paquete de evidencia existente",
        "from_audit_intro": (
            "Ruta canónica: generar Magnetism desde un Brand Audit existente. Los escaneos por URL de arriba "
            "crean primero ese mismo tipo de snapshot; esta tabla solo reutiliza uno ya disponible."
        ),
        "use_evidence": "usar evidencia",
        "no_audits": "// todavía no hay Brand Audits disponibles — ejecuta una URL arriba o crea un audit normal primero.",
        "recent_scans": "escaneos_recientes",
        "latest_runs": "últimas ejecuciones",
        "view_sheet": "ver ficha",
        "audit_score": "score audit",
        "no_scans": "// todavía no hay escaneos Magnetism — ejecuta el primero arriba.",
        "date": "fecha",
        "brand": "marca",
        "score": "score",
        "coherence": "coherencia",
        "quadrant": "cuadrante de posicionamiento",
        "url": "url",
        "run": "run",
        "result": "resultado",
        "back": "Volver a Magnetism Scanner",
        "research_evidence": "Evidencia de investigación",
        "evidence_reliability": "Fiabilidad de evidencia",
        "methodology_details": "Detalles de metodología",
        "detail_tag": "9 bloques estratégicos derivados de 7 señales Magenta",
        "no_detected": "(no detectado)",
        "system_reading": "Lectura de sistema TLDR",
        "system_reading_tag": "tensiones y preguntas de validación dentro del TLDR Brand3",
        "credibility_support": "Soporte de credibilidad",
        "strategic_tensions": "Tensiones estratégicas",
        "validation_questions": "Preguntas de validación",
        "diagnosis": "diagnóstico",
        "diagnosis_tag": "limitado por señales observadas y ausentes",
        "limitations": "limitaciones",
        "research_intro": "Grafo de evidencia y Research Pack usados para producir la lectura TLDR Brand3.",
        "research_tag": "evidencia de investigación",
        "evidence_reliability_intro": (
            "Diagnóstico objetivo del Research Pack usado como input del TLDR. Evalúa calidad de evidencia, "
            "no la marca, y no cambia los bloques TLDR."
        ),
        "evidence_reliability_tag": "calidad del input, no de la marca",
        "quality_status": "Estado",
        "quality_score": "Score",
        "quality_gate": "Gate",
        "quality_dimensions": "Dimensiones de calidad",
        "quality_dimensions_tag": "oferta, audiencia, prueba, trazabilidad y ruido",
        "quality_warnings": "Warnings",
        "quality_failures": "Fallos de gate",
        "quality_pack_summary": "Resumen del pack",
        "quality_missing": "No se persistió diagnóstico de calidad del Research Pack para este escaneo.",
        "no_quality_warnings": "No se persistieron warnings.",
        "no_quality_failures": "No hay fallos de gate.",
        "pack_source": "Fuente del pack",
        "tldr_mode": "Modo TLDR",
        "entity_resolution": "Resolución de entidad",
        "entity_tag": "límites entre producto y compañía",
        "research_pack": "Research Pack",
        "research_pack_tag": "inputs estratégicos normalizados",
        "surface_map": "Mapa de superficies",
        "surface_map_tag": "superficies owned, producto, prueba y externas",
        "product_surfaces": "Superficies de producto",
        "source_map": "Mapa de fuentes",
        "tldr_evidence": "Evidencia TLDR",
        "tldr_evidence_tag": "qué usó cada bloque",
        "rejected_gaps": "Rechazado / Gaps",
        "rejected_gaps_tag": "interpretación acotada",
        "evidence_gaps": "Gaps de evidencia",
        "rejected_noise": "Ruido rechazado",
        "methodology_intro": "Método, reglas de interpretación y límites detrás de este escaneo.",
        "methodology_tag": "detalles de metodología",
        "research_pack_metric": "Research Pack",
        "tldr_generation": "Generación TLDR",
        "pipeline": "Pipeline",
        "pipeline_tag": "pasos deterministas y paso LLM",
        "block_method": "Método de bloques TLDR",
        "block_method_tag": "qué puede responder cada bloque",
        "magenta_signals": "Señales Magenta Circle",
        "magenta_signals_tag": "7 inputs técnicos",
        "run_limits": "Límites de ejecución",
        "run_limits_tag": "warnings e interpretación acotada",
        "source_basis": "Base de fuentes",
        "validation_notes": "Notas de validación",
        "no_validation_notes": "No se persistieron notas de validación para este escaneo.",
        "no_limitations": "No se persistieron limitaciones explícitas para este escaneo.",
        "no_clear_signal": "No se detectó una señal clara en las fuentes proporcionadas.",
        "evidence": "Evidencia",
    },
}


def _ui(lang: _Lang) -> dict:
    labels = dict(_MAGNETISM_UI["en"])
    labels.update(_MAGNETISM_UI.get(lang, {}))
    return labels


def _lang_q(lang: _Lang) -> str:
    return f"?lang={lang}"


def _with_lang(path: str, lang: _Lang) -> str:
    return f"{path}{_lang_q(lang)}"


@router.get("/magnetism-scanner")
async def magnetism_scanner_index(request: Request, lang: _Lang = Query("es")):
    """Render index page of Magnetism Scanner showing past analyses and inputs."""
    scans = list_magnetism_scans(limit=25)
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        audit_runs = store.list_runs(limit=12)
    finally:
        store.close()

    # Format dates nicely for template listing
    for scan in scans:
        try:
            dt = datetime.fromisoformat(scan["created_at"].replace("Z", "+00:00"))
            scan["formatted_date"] = dt.strftime("%b %d, %Y · %H:%M")
        except Exception:
            scan["formatted_date"] = scan["created_at"]

    return templates.TemplateResponse(
        request,
        "magnetism_scanner.html.j2",
        {
            "ui_lang": lang,
            "landing": magnetism_landing_copy(lang),
            "model": {
                "scans": scans,
                "audit_runs": audit_runs,
                "lang": lang,
                "other_lang": "en" if lang == "es" else "es",
                "lang_query": _lang_q(lang),
                "t": _ui(lang),
            }
        },
    )


@router.post("/magnetism-scanner/analyze")
async def magnetism_scanner_analyze(
    request: Request,
    url: str = Form(None),
    manual_text: str = Form(None),
    lang: _Lang = Form("es"),
):
    """Queue analysis on the provided URL or copy-pasted text block."""
    url_val = (url or "").strip()
    manual_val = (manual_text or "").strip()

    if not url_val and not manual_val:
        return templates.TemplateResponse(
            request,
            "error.html.j2",
            {
                "status_code": 400,
                "error": "Input required: Please provide either a website URL to scan or paste manual text content.",
                "ui_lang": lang,
            },
            status_code=400,
        )

    normalized_url = ""
    if url_val:
        valid, result = validate_url(url_val)
        if not valid:
            return templates.TemplateResponse(
                request,
                "error.html.j2",
                {"status_code": 400, "error": f"URL rejected: {result}", "ui_lang": lang},
                status_code=400,
            )
        normalized_url = result

    token = secrets.token_urlsafe(12)
    if normalized_url:
        input_type = "url"
        input_value = normalized_url
        brand_name = slug_from_url(normalized_url)
        display_url = normalized_url
    else:
        input_type = "manual"
        input_value = manual_val
        brand_name = "Manual Upload Brand"
        display_url = "Manual Upload"

    insert_magnetism_job(
        token=token,
        brand_name=brand_name,
        url=display_url,
        input_type=input_type,
        input_value=input_value,
    )
    await get_queue().enqueue_magnetism(token)
    return RedirectResponse(_with_lang(f"/magnetism-scanner/{token}/status", lang), status_code=303)


@router.post("/magnetism-scanner/from-run")
async def magnetism_scanner_from_run(
    request: Request,
    run_id: int = Form(...),
    lang: _Lang = Form("es"),
):
    """Queue a Magnetism scan from an existing Brand Audit run snapshot."""
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(run_id)
    finally:
        store.close()

    if snapshot is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Brand Audit run #{run_id}", "ui_lang": lang},
            status_code=404,
        )

    run = snapshot.get("run") or {}
    token = secrets.token_urlsafe(12)
    insert_magnetism_job(
        token=token,
        brand_name=str(run.get("brand_name") or f"Brand Audit run #{run_id}"),
        url=str(run.get("url") or "Brand Audit snapshot"),
        input_type="audit_run",
        input_value=str(run_id),
        source_run_id=run_id,
    )
    await get_queue().enqueue_magnetism(token)
    return RedirectResponse(_with_lang(f"/magnetism-scanner/{token}/status", lang), status_code=303)


_MAGNETISM_PHASES = [
    ("queued", "Queued"),
    ("collecting", "Collecting Brand Audit evidence"),
    ("extracting", "Extracting Magnetism signals"),
    ("interpreting", "Interpreting TLDR Brand3 blocks"),
    ("scoring", "Scoring magnetism and coherence"),
    ("finalizing", "Writing Magnetism report"),
]

_MAGNETISM_PHASE_LABELS = {
    **{key: label for key, label in _MAGNETISM_PHASES},
    "ready": "Magnetism report ready",
    "failed": "Magnetism scan failed",
}


@router.get("/magnetism-scanner/{token}/status")
async def magnetism_scanner_status(request: Request, token: str, lang: _Lang = Query("es")):
    """Render the shared waiting page for an in-flight Magnetism scan."""
    row = get_magnetism_scan_by_token(token)
    if row is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan token {token}", "ui_lang": lang},
            status_code=404,
        )
    if row.get("status") == "ready":
        return RedirectResponse(_with_lang("/magnetism-scanner/scan/{}".format(row["id"]), lang), status_code=303)

    phase = _magnetism_phase(row)
    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {
            "ui_lang": lang,
            "token": token,
            "brand_slug": row.get("brand_name") or "magnetism scan",
            "status": row.get("status") or "queued",
            "elapsed_seconds": _elapsed(row.get("started_at")),
            "elapsed_label": _elapsed_label(_elapsed(row.get("started_at"))),
            "error_message": row.get("error_message"),
            "phase": phase,
            "phase_label": _MAGNETISM_PHASE_LABELS.get(phase, "Working"),
            "phase_steps": _phase_steps(_MAGNETISM_PHASES, phase, row.get("status") or "queued"),
            "ready_href": _with_lang("/magnetism-scanner/scan/{}".format(row["id"]), lang),
            "back_href": _with_lang("/magnetism-scanner", lang),
            "status_label": "magnetism_status",
            "typical_run_label": "1-4 min",
            "status_note": "Page auto-refreshes every 5 seconds. This checklist reflects Magnetism Scanner phase, not a percentage estimate.",
        },
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


def _phase_steps(phases: list[tuple[str, str]], current_phase: str, status: str) -> list[dict]:
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
        steps.append({"key": "failed", "label": "Magnetism scan failed", "state": "failed"})
    if current_phase == "ready":
        steps.append({"key": "ready", "label": "Magnetism report ready", "state": "done"})
    return steps


@router.get("/magnetism-scanner/scan/{scan_id}")
async def magnetism_scanner_detail(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render details sheet of a specific magnetism scan."""
    model = _magnetism_scan_model(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "tldr"
    _attach_ui(model, lang)

    return templates.TemplateResponse(
        request,
        "magnetism_detail.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/research")
async def magnetism_scanner_research(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render research evidence for a specific Magnetism scan."""
    model = _magnetism_scan_model(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "research"
    model["research"] = _research_evidence_model(model["payload"])
    _attach_ui(model, lang)

    return templates.TemplateResponse(
        request,
        "magnetism_research.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/evidence-reliability")
async def magnetism_scanner_evidence_reliability(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render Research Pack quality diagnostics for a specific Magnetism scan."""
    model = _magnetism_scan_model(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "evidence_reliability"
    model["quality"] = _evidence_reliability_model(model["payload"])
    _attach_ui(model, lang)

    return templates.TemplateResponse(
        request,
        "magnetism_evidence_reliability.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/methodology")
async def magnetism_scanner_methodology(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render methodology details for a specific Magnetism scan."""
    model = _magnetism_scan_model(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "methodology"
    model["methodology"] = _methodology_model(model["payload"])
    _attach_ui(model, lang)

    return templates.TemplateResponse(
        request,
        "magnetism_methodology.html.j2",
        {"model": model, "ui_lang": lang},
    )


def _attach_ui(model: dict, lang: _Lang) -> None:
    model["lang"] = lang
    model["other_lang"] = "en" if lang == "es" else "es"
    model["lang_query"] = _lang_q(lang)
    model["t"] = _ui(lang)


def _magnetism_scan_model(scan_id: int, *, lang: _Lang = "es") -> dict | None:
    row = get_magnetism_scan(scan_id)
    if row is None:
        return None

    try:
        payload = json.loads(row["raw_payload"])
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupted scan payload in database.")
    if not payload.get("metrics") or not payload.get("tldr_brand3"):
        payload = MagnetismExtractor(llm=None)._normalize_analysis(payload)
    else:
        payload = MagnetismExtractor(llm=None).ensure_tldr_v03_contract(payload)
    payload = _payload_for_language(scan_id, payload, lang)

    # Format timestamp nicely
    try:
        # In SQLite, row['created_at'] is 'YYYY-MM-DD HH:MM:SS' or ISO format
        dt = datetime.fromisoformat(row["created_at"].replace(" ", "T"))
        formatted_date = dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except Exception:
        formatted_date = row["created_at"]

    return {
        "id": scan_id,
        "title": f"Magnetism: {payload['brand_name']}",
        "brand_name": payload["brand_name"],
        "url": payload["url"],
        "created_at": formatted_date,
        "magnetism_score": payload["magnetism_score"],
        "coherence_score": payload["coherence_score"],
        "quadrant": payload["quadrant"],
        "executive_headline": payload["executive_headline"],
        "observations": payload["observations"],
        "tldr_grid": payload["tldr_grid"],
        "tldr_brand3": payload.get("tldr_brand3") or {},
        "tldr_strategy": payload.get("tldr_strategy") or {},
        "metrics": payload.get("metrics") or {},
        "diagnosis": payload.get("diagnosis") or {},
        "limitations": payload.get("limitations") or [],
        "source": payload.get("source") or "direct_scan",
        "source_run_id": payload.get("source_run_id"),
        "extraction_mode": payload.get("extraction_mode") or "unknown",
        "canonical_evidence_source": payload.get("canonical_evidence_source"),
        "direct_source_provider": payload.get("direct_source_provider"),
        "deprecation": payload.get("deprecation") or {},
        "evidence_packet_summary": payload.get("evidence_packet_summary") or {},
        "content_distillation_summary": payload.get("content_distillation_summary") or {},
        "system_reading": payload.get("system_reading") or {},
        "score_breakdown": payload["score_breakdown"],
        "magenta_circle": payload["magenta_circle"],
        "fallback_used": payload.get("fallback_used", False),
        "payload": payload,
    }


def _payload_for_language(scan_id: int, payload: dict, lang: _Lang) -> dict:
    """Translate Magnetism prose on first read and reuse cached payload afterwards."""
    translations = payload.get("translations")
    if not isinstance(translations, dict):
        translations = {}
    magnetism_translations = translations.get("magnetism_tldr")
    if not isinstance(magnetism_translations, dict):
        magnetism_translations = {}

    cached = magnetism_translations.get(lang)
    if isinstance(cached, dict):
        return apply_magnetism_translation(payload, cached)

    if not BRAND3_LLM_API_KEY:
        return payload

    analyzer = LLMAnalyzer(api_key=BRAND3_LLM_API_KEY, model=LLM_CHEAP_MODEL)
    translated = translate_magnetism_payload(payload, target_lang=lang, analyzer=analyzer)
    if not translated:
        return payload

    updated_payload = dict(payload)
    updated_translations = dict(translations)
    updated_magnetism_translations = dict(magnetism_translations)
    updated_magnetism_translations[lang] = translated
    updated_translations["magnetism_tldr"] = updated_magnetism_translations
    updated_payload["translations"] = updated_translations
    update_magnetism_scan_payload(scan_id, json.dumps(updated_payload, ensure_ascii=False))
    return apply_magnetism_translation(updated_payload, translated)


def _research_evidence_model(payload: dict) -> dict:
    research_pack = payload.get("research_pack") or {}
    entity = research_pack.get("resolved_entity") or {}
    source_map = research_pack.get("source_map") or {}
    graph_summary = payload.get("evidence_graph_summary") or {}
    entity_packet = _entity_research_packet(payload)
    product_surfaces = list(entity_packet.get("product_surfaces") or [])
    owned_surfaces = list(entity_packet.get("owned_surfaces") or [])
    tldr_blocks = payload.get("analyst_tldr_validated", {}).get("tldr_brand3") or payload.get("tldr_brand3") or {}

    block_evidence = []
    for key, block in tldr_blocks.items():
        if not isinstance(block, dict):
            continue
        block_evidence.append({
            "key": key,
            "label": str(key).replace("_", " ").title(),
            "answer": block.get("answer") or block.get("content"),
            "claim_type": block.get("claim_type") or "unknown",
            "confidence": block.get("confidence") or "unknown",
            "evidence_used": block.get("evidence_used") or block.get("evidence") or [],
            "evidence_sources": block.get("evidence_sources") or [],
        })

    source_counts = graph_summary.get("source_counts") or {}
    source_rows = [
        {
            "url": url,
            "source_type": source.get("source_type") or "unknown",
            "surface_role": source.get("surface_role") or "",
            "entity_scope": source.get("entity_scope") or "",
            "title": source.get("title") or source.get("label") or url,
        }
        for url, source in source_map.items()
        if isinstance(source, dict)
    ]
    source_rows.sort(key=lambda item: (item["source_type"], item["url"]))
    if not product_surfaces:
        product_surfaces = [
            {
                "url": item["url"],
                "role": item["surface_role"] or item["source_type"],
                "entity_scope": item["entity_scope"],
                "reason": "Detected from persisted Research Pack source map.",
            }
            for item in source_rows
            if str(item.get("entity_scope") or "").startswith("product:")
        ]
    if not owned_surfaces:
        owned_surfaces = [
            {
                "url": item["url"],
                "role": item["surface_role"] or item["source_type"],
                "entity_scope": item["entity_scope"],
                "reason": "Persisted Research Pack source.",
            }
            for item in source_rows
            if str(item.get("source_type") or "").startswith("owned_")
        ]

    return {
        "entity": entity,
        "entity_packet": entity_packet,
        "research_pack_source": payload.get("research_pack_source") or "legacy_snapshot",
        "tldr_generation_mode": payload.get("tldr_generation_mode") or "unknown",
        "category": research_pack.get("category") or "",
        "offer": research_pack.get("offer") or "",
        "company_summary": research_pack.get("company_summary") or "",
        "product_summary": research_pack.get("product_summary") or "",
        "audience": research_pack.get("audience") or "",
        "outcome": research_pack.get("outcome") or "",
        "declared_mission": research_pack.get("declared_mission") or "",
        "future_direction": research_pack.get("future_direction") or "",
        "owned_surfaces": owned_surfaces,
        "product_surfaces": product_surfaces,
        "source_counts": source_counts,
        "source_rows": source_rows,
        "block_evidence": block_evidence,
        "proof_points": research_pack.get("proof_points") or [],
        "noise_rejected": research_pack.get("noise_rejected") or [],
        "evidence_gaps": research_pack.get("evidence_gaps") or [],
        "confidence_notes": research_pack.get("confidence_notes") or [],
        "graph_summary": graph_summary,
    }


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


def _methodology_model(payload: dict) -> dict:
    return {
        "tldr_generation_mode": payload.get("tldr_generation_mode") or "unknown",
        "research_pack_source": payload.get("research_pack_source") or "legacy_snapshot",
        "analysis_error": payload.get("analyst_tldr_analysis_error"),
        "strategy": payload.get("tldr_strategy") or {},
        "magenta_circle": payload.get("magenta_circle") or {},
        "metrics": payload.get("metrics") or {},
        "score_breakdown": payload.get("score_breakdown") or {},
        "evidence_packet_summary": payload.get("evidence_packet_summary") or {},
        "content_distillation_summary": payload.get("content_distillation_summary") or {},
        "extraction_mode": payload.get("extraction_mode") or "unknown",
        "source": payload.get("source") or "direct_scan",
        "canonical_evidence_source": payload.get("canonical_evidence_source"),
        "direct_source_provider": payload.get("direct_source_provider"),
        "limitations": payload.get("limitations") or [],
        "warnings": payload.get("warnings") or [],
        "research_pack": payload.get("research_pack") or {},
    }


def _entity_research_packet(payload: dict) -> dict:
    research_pack = payload.get("research_pack") or {}
    entity = research_pack.get("entity") or {}
    if isinstance(entity, dict) and (entity.get("owned_surfaces") or entity.get("product_surfaces")):
        return entity
    return {}
