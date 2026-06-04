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
from src.reports.dossier import build_brand_dossier
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
from ..scanner_api.models import (
    methodology_model as _methodology_model,
    normalized_scan_payload as _normalized_scan_payload,
    research_evidence_model as _research_evidence_model,
    scan_model_from_payload as _scan_model_from_payload,
    scanner_result_metadata_model as _scanner_result_metadata,
)

router = APIRouter()


_Lang = Literal["es", "en"]


class _ReportReadAnalyzer:
    """Keep scanner audit reads deterministic and side-effect free."""

    def _call(self, *args, **kwargs) -> str:
        return ""

    def _call_json(self, *args, **kwargs) -> dict:
        return {}


_REPORT_READ_ANALYZER = _ReportReadAnalyzer()


_MAGNETISM_UI = {
    "en": {
        "language": "Language",
        "other_lang": "ES",
        "scanner_title": "Brand3 Scanner",
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
        "back": "Back to Brand3 Scanner",
        "research_evidence": "Research Evidence",
        "audit": "Audit",
        "audit_tag": "Brand Audit inside the scanner result",
        "audit_intro": "Executive Brand Audit reading attached to this scanner result.",
        "audit_unavailable": "No Brand Audit snapshot is attached to this scan.",
        "audit_run": "Brand Audit run",
        "executive_summary": "Executive summary",
        "primary_risk": "Primary risk",
        "primary_opportunity": "Primary opportunity",
        "dimension_audit": "Dimension audit",
        "findings": "Findings",
        "recommendation": "Recommendation",
        "confidence": "Confidence",
        "legacy_audit": "Legacy audit fallback",
        "evidence_reliability": "Evidence Reliability",
        "evidence": "Evidence",
        "evidence_basis": "Evidence basis",
        "total_evidence": "Total evidence",
        "overall_status": "Overall status",
        "report_mode": "Report mode",
        "dimension_names": {
            "coherencia": "Coherence",
            "presencia": "Presence",
            "percepcion": "Perception",
            "diferenciacion": "Differentiation",
            "vitalidad": "Vitality",
        },
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
        "research_sections": "Sections",
        "surface_map": "Surface Map",
        "surface_map_tag": "owned, product, proof, and external surfaces",
        "product_surfaces": "Product surfaces",
        "source_map": "Source map",
        "competitive_context": "Competitive context",
        "competitive_context_tag": "context only, not audited-brand evidence",
        "parallel_shadow": "Parallel Shadow",
        "parallel_shadow_tag": "external signals for manual review",
        "parallel_shadow_intro": (
            "Parallel is running as an observational provider. This readout summarizes external coverage "
            "candidates for review; it is not used for scoring, TLDR claims, proof points, or recommendations."
        ),
        "parallel_shadow_readout": "External signal readout",
        "parallel_shadow_coverage": "Coverage",
        "parallel_shadow_candidate_count": "External candidates",
        "parallel_shadow_domain_count": "Domains",
        "parallel_shadow_signal_types": "Signal types",
        "parallel_shadow_manual_review": "Manual review candidates",
        "parallel_shadow_missing": "No Parallel shadow data was persisted for this scan.",
        "parallel_shadow_domains": "Domains",
        "parallel_shadow_intents": "Intents",
        "parallel_shadow_results": "Source candidates",
        "tldr_evidence": "TLDR Evidence",
        "tldr_evidence_tag": "what each block used",
        "rejected_gaps": "Rejected / Gaps",
        "rejected_gaps_tag": "bounded interpretation",
        "evidence_gaps": "Evidence gaps",
        "rejected_noise": "Rejected noise",
        "entity_boundary_warnings": "Entity boundary warnings",
        "entity_boundary_warnings_tag": "external evidence quarantined before TLDR input",
        "entity_boundary_rejections": "Quarantined evidence",
        "entity_boundary_open_source": "Open source",
        "no_entity_boundary_warnings": "No entity boundary collisions were persisted for this scan.",
        "methodology_intro": "Method, interpretation rules, and limits behind this scan.",
        "methodology_tag": "methodology details",
        "result_metadata": "Result metadata",
        "result_metadata_tag": "derived compatibility flags",
        "result_version": "Result version",
        "pipeline_version": "Pipeline version",
        "scanner_readiness": "Scanner readiness",
        "generated_with": "Generated with",
        "stale_against_current_pipeline": "Historic against current pipeline",
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
        "scanner_title": "Brand3 Scanner",
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
        "back": "Volver a Brand3 Scanner",
        "research_evidence": "Evidencia de investigación",
        "audit": "Auditoría",
        "audit_tag": "Brand Audit dentro del resultado del scanner",
        "audit_intro": "Lectura ejecutiva de Brand Audit asociada a este resultado del scanner.",
        "audit_unavailable": "Este scan no tiene un snapshot de Brand Audit asociado.",
        "audit_run": "Brand Audit run",
        "executive_summary": "Resumen ejecutivo",
        "primary_risk": "Riesgo principal",
        "primary_opportunity": "Oportunidad principal",
        "dimension_audit": "Auditoría por dimensión",
        "findings": "Hallazgos",
        "recommendation": "Recomendación",
        "confidence": "Confianza",
        "legacy_audit": "Fallback de auditoría legacy",
        "evidence_reliability": "Fiabilidad de evidencia",
        "evidence": "Evidencia",
        "evidence_basis": "Base de evidencia",
        "total_evidence": "Evidencia total",
        "overall_status": "Estado general",
        "report_mode": "Modo de informe",
        "dimension_names": {
            "coherencia": "Coherencia",
            "presencia": "Presencia",
            "percepcion": "Percepción",
            "diferenciacion": "Diferenciación",
            "vitalidad": "Vitalidad",
        },
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
        "research_sections": "Secciones",
        "surface_map": "Mapa de superficies",
        "surface_map_tag": "superficies owned, producto, prueba y externas",
        "product_surfaces": "Superficies de producto",
        "source_map": "Mapa de fuentes",
        "competitive_context": "Contexto competitivo",
        "competitive_context_tag": "solo contexto, no evidencia de la marca auditada",
        "parallel_shadow": "Parallel Shadow",
        "parallel_shadow_tag": "señales externas para revisión manual",
        "parallel_shadow_intro": (
            "Parallel está corriendo como proveedor observacional. Esta lectura resume candidatos de "
            "cobertura externa para revisión; no se usa en scoring, claims TLDR, proof points ni recomendaciones."
        ),
        "parallel_shadow_readout": "Lectura de señales externas",
        "parallel_shadow_coverage": "Cobertura",
        "parallel_shadow_candidate_count": "Candidatos externos",
        "parallel_shadow_domain_count": "Dominios",
        "parallel_shadow_signal_types": "Tipos de señal",
        "parallel_shadow_manual_review": "Candidatos a revisión manual",
        "parallel_shadow_missing": "No se persistió data shadow de Parallel para este escaneo.",
        "parallel_shadow_domains": "Dominios",
        "parallel_shadow_intents": "Intents",
        "parallel_shadow_results": "Fuentes candidatas",
        "tldr_evidence": "Evidencia TLDR",
        "tldr_evidence_tag": "qué usó cada bloque",
        "rejected_gaps": "Rechazado / Gaps",
        "rejected_gaps_tag": "interpretación acotada",
        "evidence_gaps": "Gaps de evidencia",
        "rejected_noise": "Ruido rechazado",
        "entity_boundary_warnings": "Warnings de límite de entidad",
        "entity_boundary_warnings_tag": "evidencia externa en cuarentena antes del TLDR",
        "entity_boundary_rejections": "Evidencia cuarentenada",
        "entity_boundary_open_source": "Abrir fuente",
        "no_entity_boundary_warnings": "No se persistieron colisiones de límite de entidad para este escaneo.",
        "methodology_intro": "Método, reglas de interpretación y límites detrás de este escaneo.",
        "methodology_tag": "detalles de metodología",
        "result_metadata": "Metadata del resultado",
        "result_metadata_tag": "flags derivados de compatibilidad",
        "result_version": "Versión del resultado",
        "pipeline_version": "Versión del pipeline",
        "scanner_readiness": "Readiness del scanner",
        "generated_with": "Generado con",
        "stale_against_current_pipeline": "Histórico frente al pipeline actual",
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


_MAGNETISM_PHASES = {
    "es": [
        ("queued", "En cola"),
        ("collecting", "Recopilando web pública"),
        ("extracting", "Leyendo señales externas"),
        ("interpreting", "Construyendo evidencia"),
        ("scoring", "Calculando salud de marca"),
        ("finalizing", "Generando TLDR estratégico"),
    ],
    "en": [
        ("queued", "Queued"),
        ("collecting", "Collecting public web evidence"),
        ("extracting", "Reading external signals"),
        ("interpreting", "Building evidence"),
        ("scoring", "Calculating brand health"),
        ("finalizing", "Generating strategic TLDR"),
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
        "note": "La página se actualiza cada 5 segundos. Esta lista muestra la fase del Brand3 Scanner, no una estimación porcentual.",
        "queued": "esperando turno de análisis",
        "ready": "abriendo informe ...",
        "ready_link": "→ abrir informe",
        "back_link": "← volver al scanner",
    },
    "en": {
        "note": "Page auto-refreshes every 5 seconds. This list shows the Brand3 Scanner phase, not a percentage estimate.",
        "queued": "waiting for analysis slot",
        "ready": "opening report ...",
        "ready_link": "→ open report",
        "back_link": "← back to scanner",
    },
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
            "phase": phase,
            "phase_label": phase_labels.get(phase, "Working" if lang == "en" else "Trabajando"),
            "phase_steps": _phase_steps(_MAGNETISM_PHASES[lang], phase, row.get("status") or "queued", lang=lang),
            "ready_href": _with_lang("/magnetism-scanner/scan/{}".format(row["id"]), lang),
            "back_href": _with_lang("/magnetism-scanner", lang),
            "status_label": "brand_scanner_status",
            "typical_run_label": "1-4 min",
            "status_note": status_copy["note"],
            "queued_message": status_copy["queued"],
            "ready_message": status_copy["ready"],
            "ready_link_label": status_copy["ready_link"],
            "back_link_label": status_copy["back_link"],
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


def _phase_steps(phases: list[tuple[str, str]], current_phase: str, status: str, *, lang: _Lang = "es") -> list[dict]:
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


@router.get("/magnetism-scanner/scan/{scan_id}/audit")
async def magnetism_scanner_audit(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the Brand Audit tab inside the unified Scanner layout."""
    model = _magnetism_scan_model(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "audit"
    _attach_ui(model, lang)
    source_run_id = model.get("source_run_id")
    if not source_run_id:
        model["audit"] = {"available": False, "reason": "missing_source_run"}
        return templates.TemplateResponse(
            request,
            "magnetism_audit.html.j2",
            {"model": model, "ui_lang": lang},
        )

    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        snapshot = store.get_run_snapshot(int(source_run_id))
        narrative_payload = _report_translation_payload(store, int(source_run_id), lang)
    finally:
        store.close()
    if snapshot is None:
        model["audit"] = {
            "available": False,
            "reason": "missing_snapshot",
            "source_run_id": source_run_id,
        }
    else:
        audit_context = build_brand_dossier(
            snapshot,
            theme="light",
            analyzer=_REPORT_READ_ANALYZER,
            narrative_payload=narrative_payload,
        )
        audit_context["executive_analysis_v2"] = _executive_analysis_for_language(
            audit_context,
            narrative_payload,
            lang,
        )
        model["audit"] = {
            "available": True,
            "source_run_id": int(source_run_id),
            "context": audit_context,
        }

    return templates.TemplateResponse(
        request,
        "magnetism_audit.html.j2",
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

    payload = _normalized_scan_payload(row)
    payload = _payload_for_language(scan_id, payload, lang)
    return _scan_model_from_payload(row, payload, scan_id=scan_id)


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


def _report_translation_payload(store: SQLiteStore, run_id: int, lang: _Lang) -> dict | None:
    if lang == "en":
        return None
    try:
        return store.get_report_translation(run_id, lang)
    except Exception:
        return None


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

