"""FastAPI routes for the Brand3 Magnetism Scanner."""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from urllib.parse import urlparse

from typing import Literal

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from src.config import BRAND3_DB_PATH
from src.features.magnetism.extractor import MagnetismExtractor
from src.features.magnetism.client_tldr_v2 import build_client_tldr_v2
from src.features.magnetism.moodboard import build_moodboard_model, extract_moodboard_images
from src.features.magnetism.translation import apply_magnetism_translation
from src.features.magnetism.tldr_v2 import build_audit_aware_tldr_v2
from src.scoring.provenance import build_score_provenance_report
from src.reports.dossier import build_brand_dossier
from src.services.magnetism_service import ensure_sv9_scan_for_source_run
from src.storage.sqlite_store import SQLiteStore

from ..i18n import magnetism_landing_copy
from ..storage import (
    get_magnetism_scan,
    get_magnetism_scan_by_token,
    get_sv9_generation_job,
    get_sv9_generation_job_by_scan_id,
    insert_magnetism_job,
    insert_magnetism_scan,
    insert_sv9_generation_job,
    list_magnetism_scans,
    update_sv9_generation_job,
)
from ..templates_env import templates
from ..workers.queue import get_queue
from ..workers.slug import slug_from_url
from ..workers.url_validator import validate_url
from ..scanner_api.models import (
    scanner_failure_diagnostics_from_row as _scanner_failure_diagnostics,
    methodology_model as _methodology_model,
    normalized_scan_payload as _normalized_scan_payload,
    research_evidence_model as _research_evidence_model,
    scan_model_from_payload as _scan_model_from_payload,
    scanner_result_metadata_model as _scanner_result_metadata,
)
from ..scan_links import attach_primary_scan_hrefs, sv9_scan_id_for_run

router = APIRouter()

_LOG = logging.getLogger(__name__)


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
        "home": "Home",
        "recent_scans_nav": "Recent scans",
        "new_scan": "New scan",
        "sv9_shadow": "SV9 shadow",
        "ranking": "Ranking",
        "tools": "tools",
        "scanner_history_intro": "Review previous scanner results and open their SV9 score, evidence, audit and methodology.",
        "base_reading": "Base reading",
        "research_evidence": "Research Evidence",
        "audit": "Audit",
        "audit_tag": "Brand Audit inside the scanner result",
        "audit_intro": "Executive Brand Audit reading attached to this scanner result.",
        "audit_unavailable": "No Brand Audit snapshot is attached to this scan.",
        "audit_run": "Brand Audit run",
        "executive_summary": "Executive summary",
        "primary_risk": "Primary risk",
        "primary_opportunity": "Primary opportunity",
        "internal_audit": "Internal score audit",
        "internal_audit_tag": "score provenance and TLDR v2",
        "audit_status": "Audit status",
        "score_integrity": "Score integrity",
        "score_summary": "Score summary",
        "computed_score": "Computed score",
        "reviewed_score": "Reviewed score",
        "display_score": "Display score",
        "display_score_source": "Display source",
        "display_score_status": "Display status",
        "dimension_breakdown": "Dimension breakdown",
        "confidence_summary": "Confidence summary",
        "fallback_flags": "Fallback flags",
        "rules_caps": "Rules / caps",
        "warnings": "Warnings",
        "recommended_action": "Recommended action",
        "tldr_v2_internal_summary": "TLDR v2 internal summary",
        "fingerprint_details": "Fingerprint details",
        "raw_feature_provenance": "Raw feature provenance",
        "reviewed_score_block": "Reviewed score block",
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
        "methodology": "Methodology",
        "moodboard": "Moodboard",
        "moodboard_tag": "visual board built from captured brand assets",
        "moodboard_intro": (
            "Representative images the brand publishes on its owned surfaces, captured during this scan and "
            "arranged as a moodboard next to the strategic reading."
        ),
        "moodboard_hint": "drag images to rearrange",
        "moodboard_shuffle": "shuffle",
        "moodboard_empty": (
            "No representative images were captured for this scan. The moodboard needs a Brand Audit run "
            "with a persisted web acquisition."
        ),
        "moodboard_visual_reading": "Visual reading",
        "moodboard_visual_reading_tag": "strategic blocks that frame the imagery",
        "moodboard_inventory": "Image inventory",
        "moodboard_inventory_tag": "captured assets and their roles",
        "moodboard_role": "role",
        "moodboard_alt": "alt text",
        "moodboard_roles": {
            "logo": "logo / icon",
            "social_card": "social card",
            "content": "page image",
        },
        "moodboard_source_note": (
            "Images are linked directly from the brand's own pages as captured at scan time; an empty slot "
            "means the asset is no longer reachable."
        ),
        "detail_tag": "9 strategic blocks derived from 7 Magenta signals",
        "no_detected": "(not detected)",
        "system_reading": "TLDR System Reading",
        "system_reading_tag": "tensions and validation questions inside TLDR Brand3",
        "client_tldr_v2": "Client TLDR v2",
        "client_tldr_v2_tag": "score-aware client preview",
        "generate_sv9": "Generate SV9",
        "sv9_generation_status": "SV9 generation",
        "sv9_generation_tag": "shadow scan materialization",
        "sv9_generation_intro": "Generating the shadow V9 scan from the persisted Brand Audit snapshot.",
        "sv9_generation_queued": "waiting to materialize the shadow scan",
        "sv9_generation_ready": "shadow scan ready ...",
        "sv9_generation_ready_link": "→ open SV9 scan",
        "sv9_generation_back": "← back to scan",
        "score_reading": "Score reading",
        "score_status": "Score status",
        "score_note": "Score note",
        "evidence_refs": "Evidence refs",
        "tldr_block_names": {
            "core_purpose": "CORE PURPOSE",
            "magnetism": "MAGNETISM",
            "value_proposition": "VALUE PROPOSITION",
            "personality": "PERSONALITY",
            "brand_idea": "BRAND IDEA",
            "attributes": "ATTRIBUTES",
            "values": "VALUES",
            "mission": "MISSION",
            "vision": "VISION",
        },
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
        "home": "Inicio",
        "recent_scans_nav": "Scans recientes",
        "new_scan": "Nuevo scan",
        "sv9_shadow": "SV9 sombra",
        "ranking": "Ranking",
        "tools": "herramientas",
        "scanner_history_intro": "Revisa resultados anteriores y abre su score SV9, evidencia, auditoría y metodología.",
        "base_reading": "Lectura base",
        "research_evidence": "Evidencia de investigación",
        "audit": "Auditoría",
        "audit_tag": "Brand Audit dentro del resultado del scanner",
        "audit_intro": "Lectura ejecutiva de Brand Audit asociada a este resultado del scanner.",
        "audit_unavailable": "Este scan no tiene un snapshot de Brand Audit asociado.",
        "audit_run": "Brand Audit run",
        "executive_summary": "Resumen ejecutivo",
        "primary_risk": "Riesgo principal",
        "primary_opportunity": "Oportunidad principal",
        "internal_audit": "Auditoría interna de score",
        "internal_audit_tag": "proveniencia del score y TLDR v2",
        "audit_status": "Estado de auditoría",
        "score_integrity": "Integridad del score",
        "score_summary": "Resumen de score",
        "computed_score": "Score computado",
        "reviewed_score": "Score revisado",
        "display_score": "Score mostrado",
        "display_score_source": "Fuente del display",
        "display_score_status": "Estado del display",
        "dimension_breakdown": "Desglose por dimensión",
        "confidence_summary": "Resumen de confianza",
        "fallback_flags": "Fallback flags",
        "rules_caps": "Rules / caps",
        "warnings": "Warnings",
        "recommended_action": "Acción recomendada",
        "tldr_v2_internal_summary": "Resumen interno TLDR v2",
        "fingerprint_details": "Detalles del fingerprint",
        "raw_feature_provenance": "Proveniencia cruda de features",
        "reviewed_score_block": "Bloque de score revisado",
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
        "methodology": "Metodología",
        "moodboard": "Moodboard",
        "moodboard_tag": "tablero visual con assets capturados de la marca",
        "moodboard_intro": (
            "Imágenes representativas que la marca publica en sus superficies propias, capturadas durante "
            "este escaneo y organizadas como moodboard junto a la lectura estratégica."
        ),
        "moodboard_hint": "arrastra las imágenes para reorganizar",
        "moodboard_shuffle": "reorganizar",
        "moodboard_empty": (
            "No se capturaron imágenes representativas para este escaneo. El moodboard necesita un run de "
            "Brand Audit con adquisición web persistida."
        ),
        "moodboard_visual_reading": "Lectura visual",
        "moodboard_visual_reading_tag": "bloques estratégicos que enmarcan las imágenes",
        "moodboard_inventory": "Inventario de imágenes",
        "moodboard_inventory_tag": "assets capturados y su rol",
        "moodboard_role": "rol",
        "moodboard_alt": "texto alt",
        "moodboard_roles": {
            "logo": "logo / icono",
            "social_card": "tarjeta social",
            "content": "imagen de página",
        },
        "moodboard_source_note": (
            "Las imágenes se enlazan directamente desde las páginas de la marca tal como se capturaron; un "
            "hueco vacío significa que el asset ya no es accesible."
        ),
        "detail_tag": "9 bloques estratégicos derivados de 7 señales Magenta",
        "no_detected": "(no detectado)",
        "system_reading": "Lectura de sistema TLDR",
        "system_reading_tag": "tensiones y preguntas de validación dentro del TLDR Brand3",
        "client_tldr_v2": "TLDR v2 para cliente",
        "client_tldr_v2_tag": "preview de cliente con score y evidencia",
        "generate_sv9": "Generar SV9",
        "sv9_generation_status": "Generación de SV9",
        "sv9_generation_tag": "materialización del scan sombra",
        "sv9_generation_intro": "Generando el scan sombra V9 desde el snapshot persistido de Brand Audit.",
        "sv9_generation_queued": "esperando para materializar el scan sombra",
        "sv9_generation_ready": "scan sombra listo ...",
        "sv9_generation_ready_link": "→ abrir scan SV9",
        "sv9_generation_back": "← volver al scan",
        "score_reading": "Lectura del score",
        "score_status": "Estado del score",
        "score_note": "Nota del score",
        "evidence_refs": "Referencias de evidencia",
        "tldr_block_names": {
            "core_purpose": "PROPÓSITO CENTRAL",
            "magnetism": "MAGNETISMO",
            "value_proposition": "PROPUESTA DE VALOR",
            "personality": "PERSONALIDAD",
            "brand_idea": "IDEA DE MARCA",
            "attributes": "ATRIBUTOS",
            "values": "VALORES",
            "mission": "MISIÓN",
            "vision": "VISIÓN",
        },
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


async def _attach_sv9_link(model: dict) -> None:
    """Nav link to the SV9 scan for this run, when one exists.

    Team gating intentionally disabled for now (product decision,
    2026-06-11). Read-only lookup; failures stay silent.
    """
    model.setdefault("sv9_scan_id", None)
    source_run_id = model.get("source_run_id")
    if not source_run_id:
        return
    scan_id = await asyncio.to_thread(_sv9_scan_id_for_run, source_run_id)
    if isinstance(scan_id, int):
        model["sv9_scan_id"] = scan_id


def _sv9_scan_id_for_run(source_run_id: object) -> int | None:
    return sv9_scan_id_for_run(source_run_id, db_path=BRAND3_DB_PATH)


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


def _load_magnetism_index_data() -> tuple[list[dict], list[dict]]:
    scans = list_magnetism_scans(limit=25)
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        audit_runs = store.list_runs(limit=12)
    finally:
        store.close()
    return scans, audit_runs


def _load_run_summary(run_id: int) -> dict | None:
    store = SQLiteStore(BRAND3_DB_PATH)
    try:
        return store.get_run_summary(run_id)
    finally:
        store.close()


@router.get("/magnetism-scanner")
async def magnetism_scanner_index(request: Request, lang: _Lang = Query("es")):
    """Render index page of Magnetism Scanner showing past analyses and inputs."""
    scans, audit_runs = await asyncio.to_thread(_load_magnetism_index_data)

    # Format dates nicely for template listing
    scans = attach_primary_scan_hrefs(scans, db_path=BRAND3_DB_PATH, lang=lang)
    for scan in scans:
        scan["display_name"] = _magnetism_display_name(
            str(scan.get("brand_name") or ""),
            str(scan.get("url") or ""),
        )
        try:
            dt = datetime.fromisoformat(scan["created_at"].replace("Z", "+00:00"))
            scan["formatted_date"] = dt.strftime("%y/%m/%d")
        except Exception:
            scan["formatted_date"] = scan["created_at"]
    for run in audit_runs:
        run["display_name"] = _magnetism_display_name(
            str(run.get("brand_name") or ""),
            str(run.get("url") or ""),
        )

    return templates.TemplateResponse(
        request,
        "magnetism_scanner.html.j2",
        {
            "ui_lang": lang,
            "landing": magnetism_landing_copy(lang),
            # Team gating intentionally disabled for now (product decision).
            "show_sv9_nav": True,
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

    await asyncio.to_thread(
        insert_magnetism_job,
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
    run = await asyncio.to_thread(_load_run_summary, run_id)

    if run is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Brand Audit run #{run_id}", "ui_lang": lang},
            status_code=404,
        )

    token = secrets.token_urlsafe(12)
    await asyncio.to_thread(
        insert_magnetism_job,
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


# Narrative captions shown by the scan loader as the pipeline advances. Keyed
# by the same phase tokens the worker reports through progress_cb.
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


def _inflight_moodboard_images(row: dict) -> list[dict]:
    """Best-effort representative images for an in-flight scan.

    Reads the most recent persisted ``web`` raw input for this brand/url and
    runs the same deterministic extractor the report moodboard uses. Returns an
    empty list until acquisition has persisted something, so the loader simply
    stays in its procedural phase meanwhile. Never raises into the request path.
    """
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


def _sv9_generation_phase_steps(phase: str, status: str | None, *, lang: _Lang = "es") -> list[dict]:
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


@router.get("/magnetism-scanner/scan/{scan_id}")
async def magnetism_scanner_detail(
    request: Request,
    scan_id: int,
    lang: _Lang = Query("es"),
    base: bool = Query(False),
):
    """Render details sheet of a specific magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "tldr"
    _attach_ui(model, lang)
    await _attach_sv9_link(model)
    if model.get("sv9_scan_id") and not base:
        return RedirectResponse(
            _with_lang(f"/sv9/scan/{model['sv9_scan_id']}", lang),
            status_code=303,
        )

    return templates.TemplateResponse(
        request,
        "magnetism_detail.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.post("/magnetism-scanner/scan/{scan_id}/generate-sv9")
async def magnetism_scanner_generate_sv9(
    request: Request,
    scan_id: int,
    lang: _Lang = Query("es"),
):
    """Queue SV9 generation and redirect to a loading page."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )

    source_run_id = model.get("source_run_id")
    if not source_run_id:
        raise HTTPException(status_code=409, detail="scan does not have a Brand Audit source run")

    existing_job = await asyncio.to_thread(get_sv9_generation_job_by_scan_id, scan_id)
    if existing_job:
        return RedirectResponse(_with_lang(f"/magnetism-scanner/sv9/{existing_job['token']}/status", lang), status_code=303)

    token = secrets.token_urlsafe(12)
    await asyncio.to_thread(
        insert_sv9_generation_job,
        token=token,
        scan_id=scan_id,
        source_run_id=int(source_run_id),
        brand_name=str(model.get("brand_name") or f"Magnetism scan #{scan_id}"),
    )
    asyncio.create_task(_run_sv9_generation_job(token))
    return RedirectResponse(_with_lang(f"/magnetism-scanner/sv9/{token}/status", lang), status_code=303)


@router.get("/magnetism-scanner/sv9/{token}/status")
async def magnetism_scanner_sv9_status(request: Request, token: str, lang: _Lang = Query("es")):
    """Intermediate loading page while the shadow SV9 scan is materialized."""
    job = await asyncio.to_thread(get_sv9_generation_job, token)
    if job is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"SV9 generation job {token}", "ui_lang": lang},
            status_code=404,
        )
    if job.get("status") == "ready" and job.get("sv9_scan_id"):
        return RedirectResponse(_with_lang(f"/sv9/scan/{job['sv9_scan_id']}", lang), status_code=303)

    phase = _sv9_generation_phase(job)
    copy = _sv9_generation_copy(lang)
    return templates.TemplateResponse(
        request,
        "status.html.j2",
        {
            "token": token,
            "brand_slug": job.get("brand_name") or f"SV9 scan #{job.get('scan_id')}",
            "status": job.get("status") or "queued",
            "elapsed_seconds": _elapsed(job.get("started_at")),
            "elapsed_label": _elapsed_label(_elapsed(job.get("started_at"))),
            "error_message": job.get("error_message"),
            "phase": phase,
            "phase_label": _sv9_generation_phase_label(phase, job.get("status"), lang=lang),
            "phase_steps": _sv9_generation_phase_steps(phase, job.get("status"), lang=lang),
            "ready_href": _with_lang(f"/sv9/scan/{job['sv9_scan_id']}", lang) if job.get("sv9_scan_id") else None,
            "back_href": _with_lang(f"/magnetism-scanner/scan/{job['scan_id']}", lang),
            "status_label": copy["status_label"],
            "typical_run_label": "30-90 sec",
            "status_note": copy["status_note"],
            "queued_message": copy["queued_message"],
            "ready_message": copy["ready_message"],
            "ready_link_label": copy["ready_link_label"],
            "back_link_label": copy["back_link_label"],
            "ui_lang": lang,
        },
    )


@router.get("/magnetism-scanner/scan/{scan_id}/research")
async def magnetism_scanner_research(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render research evidence for a specific Magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
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
    await _attach_sv9_link(model)

    return templates.TemplateResponse(
        request,
        "magnetism_research.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/moodboard")
async def magnetism_scanner_moodboard(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the visual moodboard for a specific Magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "moodboard"
    model["moodboard"] = _moodboard_model(model)
    _attach_ui(model, lang)
    await _attach_sv9_link(model)

    return templates.TemplateResponse(
        request,
        "magnetism_moodboard.html.j2",
        {"model": model, "ui_lang": lang},
    )


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


@router.get("/magnetism-scanner/scan/{scan_id}/audit")
async def magnetism_scanner_audit(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the Brand Audit tab inside the unified Scanner layout."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "audit"
    _attach_ui(model, lang)
    await _attach_sv9_link(model)
    source_run_id = model.get("source_run_id")
    if not source_run_id:
        model["audit"] = {"available": False, "reason": "missing_source_run"}
        model["internal_audit"] = {"available": False, "reason": "missing_source_run"}
        return templates.TemplateResponse(
            request,
            "magnetism_audit.html.j2",
            {"model": model, "ui_lang": lang},
        )

    snapshot, narrative_payload, score_provenance = await asyncio.to_thread(
        _load_audit_read_context,
        int(source_run_id),
        lang,
    )
    if snapshot is None:
        model["audit"] = {
            "available": False,
            "reason": "missing_snapshot",
            "source_run_id": source_run_id,
        }
        model["internal_audit"] = {
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
        current_tldr = {}
        if isinstance(model.get("payload"), dict):
            current_tldr = model["payload"].get("tldr_brand3") or {}
        tldr_v2 = build_audit_aware_tldr_v2(
            score_provenance=score_provenance,
            current_tldr=current_tldr,
        )
        status_label = _internal_audit_status_label(tldr_v2.get("score_state") or {}, score_provenance)
        model["audit"] = {
            "available": True,
            "source_run_id": int(source_run_id),
            "context": audit_context,
        }
        model["internal_audit"] = {
            "available": True,
            "source_run_id": int(source_run_id),
            "score_provenance": score_provenance,
            "tldr_v2": tldr_v2,
            "score_state": tldr_v2.get("score_state") or {},
            "reviewed_score": score_provenance.get("reviewed_score") or None,
            "status_label": status_label,
            "display_decision_label": _internal_audit_display_decision(tldr_v2.get("score_state") or {}),
            "status_class": _internal_audit_status_class(status_label),
            "summary": _internal_audit_summary_text(score_provenance, tldr_v2, lang=lang),
        }

    return templates.TemplateResponse(
        request,
        "magnetism_audit.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/client-tldr-v2")
async def magnetism_scanner_client_tldr_v2(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render the experimental client-facing TLDR v2 preview."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"Magnetism scan #{scan_id}", "ui_lang": lang},
            status_code=404,
        )
    model["active_tab"] = "client_tldr_v2"
    _attach_ui(model, lang)
    await _attach_sv9_link(model)
    source_run_id = model.get("source_run_id")
    if not source_run_id:
        model["client_tldr_v2"] = {
            "available": False,
            "reason": "missing_source_run",
            "message": "This preview requires an attached Brand Audit run.",
        }
        return templates.TemplateResponse(
            request,
            "magnetism_client_tldr_v2.html.j2",
            {"model": model, "ui_lang": lang},
        )

    snapshot, narrative_payload, score_provenance = await asyncio.to_thread(
        _load_audit_read_context,
        int(source_run_id),
        lang,
    )

    if snapshot is None:
        model["client_tldr_v2"] = {
            "available": False,
            "reason": "missing_snapshot",
            "message": "The attached Brand Audit snapshot is unavailable.",
        }
    else:
        report_context = build_brand_dossier(
            snapshot,
            theme="light",
            analyzer=_REPORT_READ_ANALYZER,
            narrative_payload=narrative_payload,
        )
        current_tldr = {}
        if isinstance(model.get("payload"), dict):
            current_tldr = model["payload"].get("tldr_brand3") or {}
        model["client_tldr_v2"] = {
            "available": True,
            **build_client_tldr_v2(
                brand_name=str(model.get("brand_name") or "brand scan"),
                url=str(model.get("url") or ""),
                current_tldr=current_tldr,
                score_provenance=score_provenance,
                report_base=report_context,
                lang=lang,
                scanner_display_score=model.get("magnetism_score"),
            ),
        }

    return templates.TemplateResponse(
        request,
        "magnetism_client_tldr_v2.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/evidence-reliability")
async def magnetism_scanner_evidence_reliability(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render Research Pack quality diagnostics for a specific Magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
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
    await _attach_sv9_link(model)

    return templates.TemplateResponse(
        request,
        "magnetism_evidence_reliability.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/magnetism-scanner/scan/{scan_id}/methodology")
async def magnetism_scanner_methodology(request: Request, scan_id: int, lang: _Lang = Query("es")):
    """Render methodology details for a specific Magnetism scan."""
    model = await _magnetism_scan_model_async(scan_id, lang=lang)
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
    await _attach_sv9_link(model)

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
