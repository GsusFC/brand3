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
from src.features.magnetism.extractor import MagnetismExtractor
from src.features.magnetism.client_tldr_v2 import build_client_tldr_v2
from src.features.magnetism.moodboard import build_moodboard_model, extract_moodboard_images
from src.features.magnetism.translation import apply_magnetism_translation
from src.features.magnetism.tldr_v2 import build_audit_aware_tldr_v2
from src.scoring.provenance import build_score_provenance_report
from src.reports.dossier import build_brand_dossier
from src.storage.sqlite_store import SQLiteStore

from ..i18n import magnetism_landing_copy
from ..observatory_index import build_observatory_index
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
from .magnetism_scanner_status_copy import (
    _LOADER_PHASE_CAPTIONS,
    _MAGNETISM_PHASES,
    _MAGNETISM_PHASE_FINAL_LABELS,
    _MAGNETISM_STATUS_COPY,
    _SV9_GENERATION_PHASES,
    _SV9_GENERATION_STATUS_COPY,
)
from ..workers.queue import get_queue
from ..workers.slug import slug_from_url
from ..scanner_api.models import (
    scanner_failure_diagnostics_from_row as _scanner_failure_diagnostics,
    methodology_model as _methodology_model,
    normalized_scan_payload as _normalized_scan_payload,
    research_evidence_model as _research_evidence_model,
    scan_model_from_payload as _scan_model_from_payload,
    scanner_result_metadata_model as _scanner_result_metadata,
)
from ..scan_links import sv9_scan_id_for_run

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
        "evidence_vnext_diag": "vNext evidence",
        "evidence_vnext_json": "raw JSON",
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
        "evidence_vnext_contract": "vNext Evidence Contract",
        "evidence_vnext_contract_tag": "promotion readiness and source hygiene",
        "evidence_vnext_contract_intro": (
            "Operational summary of the vNext evidence gate for this attached Brand Audit run. It shows "
            "what can safely feed the Research Pack and what stayed in review or noise."
        ),
        "evidence_vnext_readiness": "Readiness",
        "evidence_vnext_totals": "Evidence totals",
        "evidence_vnext_exa_strategy": "Exa strategy",
        "evidence_vnext_next_action": "Next action",
        "evidence_vnext_review_reasons": "Review reasons",
        "evidence_vnext_rejected_reasons": "Rejected reasons",
        "evidence_vnext_open_diagnostic": "Open full diagnostic",
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
        "evidence_vnext_diag": "evidencia vNext",
        "evidence_vnext_json": "JSON crudo",
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
        "evidence_vnext_contract": "Contrato de evidencia vNext",
        "evidence_vnext_contract_tag": "readiness de promoción e higiene de fuentes",
        "evidence_vnext_contract_intro": (
            "Resumen operativo del gate de evidencia vNext para el Brand Audit asociado. Muestra qué puede "
            "alimentar el Research Pack y qué quedó en revisión o ruido."
        ),
        "evidence_vnext_readiness": "Readiness",
        "evidence_vnext_totals": "Totales de evidencia",
        "evidence_vnext_exa_strategy": "Estrategia Exa",
        "evidence_vnext_next_action": "Siguiente acción",
        "evidence_vnext_review_reasons": "Razones de revisión",
        "evidence_vnext_rejected_reasons": "Razones de rechazo",
        "evidence_vnext_open_diagnostic": "Abrir diagnóstico completo",
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
        from web.routes import magnetism_scanner as _public_scanner

        sv9_scan_id = await asyncio.to_thread(
            _public_scanner.ensure_sv9_scan_for_source_run,
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
