"""Read-only Visual Signature routes for the local Brand3 platform."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from ..templates_env import templates
from ..visual_signature_data import artifact_file_response_payload
from ..visual_signature_data import build_human_review_model
from ..visual_signature_data import build_screenshot_preview_model
from ..visual_signature_data import build_visual_signature_model
from ..visual_signature_data import screenshot_file_response_payload

router = APIRouter()


@router.get("/visual-signature")
async def visual_signature_index(request: Request, lang: Literal["es", "en"] = Query("es")):
    return _render(request, "overview", lang)


@router.get("/visual-signature/governance")
async def visual_signature_governance(request: Request, lang: Literal["es", "en"] = Query("es")):
    return _render(request, "governance", lang)


@router.get("/visual-signature/calibration")
async def visual_signature_calibration(request: Request, lang: Literal["es", "en"] = Query("es")):
    return _render(request, "calibration", lang)


@router.get("/visual-signature/corpus")
async def visual_signature_corpus(request: Request, lang: Literal["es", "en"] = Query("es")):
    return _render(request, "corpus", lang)


@router.get("/visual-signature/reviewer")
async def visual_signature_reviewer(request: Request, lang: Literal["es", "en"] = Query("es")):
    return _render(request, "reviewer", lang)


@router.get("/visual-signature/reviewer/human-review")
async def visual_signature_human_review(request: Request, lang: Literal["es", "en"] = Query("es")):
    return _render_human_review(request, None, lang)


@router.get("/visual-signature/reviewer/human-review/{brand}")
async def visual_signature_human_review_brand(
    request: Request,
    brand: str,
    lang: Literal["es", "en"] = Query("es"),
):
    return _render_human_review(request, brand, lang)


@router.get("/visual-signature/artifacts/{artifact_key}")
async def visual_signature_artifact(
    request: Request,
    artifact_key: str,
    lang: Literal["es", "en"] = Query("es"),
):
    payload = artifact_file_response_payload(artifact_key)
    if payload is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"visual signature artifact {artifact_key}", "ui_lang": lang},
            status_code=404,
        )
    path, media_type = payload
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/visual-signature/screenshots/{filename}/preview")
async def visual_signature_screenshot_preview(
    request: Request,
    filename: str,
    lang: Literal["es", "en"] = Query("es"),
):
    model = build_screenshot_preview_model(filename)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"visual signature screenshot preview {filename}", "ui_lang": lang},
            status_code=404,
        )
    model["ui"] = _visual_signature_ui(lang)
    return templates.TemplateResponse(
        request,
        "visual_signature_screenshot_preview.html.j2",
        {"model": model, "ui_lang": lang},
    )


@router.get("/visual-signature/screenshots/{filename:path}")
async def visual_signature_screenshot(
    request: Request,
    filename: str,
    lang: Literal["es", "en"] = Query("es"),
):
    payload = screenshot_file_response_payload(filename)
    if payload is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": f"visual signature screenshot {filename}", "ui_lang": lang},
            status_code=404,
        )
    path, media_type = payload
    return FileResponse(path, media_type=media_type)


def _render(request: Request, section: str, lang: str):
    model = build_visual_signature_model(section)
    model["ui"] = _visual_signature_ui(lang)
    return templates.TemplateResponse(
        request,
        "visual_signature.html.j2",
        {"model": model, "ui_lang": lang},
    )


def _render_human_review(request: Request, brand: str | None, lang: str):
    model = build_human_review_model(brand)
    if model is None:
        return templates.TemplateResponse(
            request,
            "not_found.html.j2",
            {"resource": "visual signature human review evidence", "ui_lang": lang},
            status_code=404,
        )
    model["ui"] = _visual_signature_ui(lang)
    return templates.TemplateResponse(
        request,
        "visual_signature_human_review.html.j2",
        {"model": model, "ui_lang": lang},
    )


def _visual_signature_ui(lang: str) -> dict[str, object]:
    if lang == "en":
        return {
            "title_by_section": {
                "overview": "Visual Signature Lab",
                "governance": "Visual Signature Lab Governance",
                "calibration": "Visual Signature Lab Calibration",
                "corpus": "Visual Signature Lab Corpus",
                "reviewer": "Visual Signature Lab Reviewer",
            },
            "intro_by_section": {
                "overview": "Read-only Visual Signature Lab navigation. Evidence is shown separately from Brand3 Scoring and has no scoring, rubric, report, provider, or runtime mutation impact.",
                "governance": "Capability registry, runtime policy matrix, governance integrity, and validation planning for the lab. Read-only.",
                "calibration": "Calibration manifests, records, reliability report, and readiness status for the lab. Read-only.",
                "corpus": "Corpus expansion manifest, pilot metrics, queue state, and limitations for the lab. Read-only.",
                "reviewer": "Reviewer workflow pilot, selected queue items, packet links, and local reviewer viewer entry point. Read-only.",
            },
            "nav": {
                "/visual-signature": "Lab Overview",
                "/visual-signature/governance": "Governance",
                "/visual-signature/calibration": "Calibration",
                "/visual-signature/corpus": "Corpus",
                "/visual-signature/reviewer": "Reviewer",
            },
            "guardrails": {
                "evidence-only": "evidence-only",
                "no scoring impact": "no scoring impact",
                "no rubric impact": "no rubric impact",
                "no production report impact": "no production report impact",
                "no provider calls": "no provider calls",
                "no runtime mutation": "no runtime mutation",
                "read-only source artifact navigation": "read-only source artifact navigation",
                "no persistence": "no persistence",
                "no completed review records": "no completed review records",
            },
            "screenshot_labels": {
                "raw viewport": "raw viewport",
                "clean attempt": "clean attempt",
                "full page": "full page",
            },
            "overview_guardrail_title": "Brand3 Scoring remains separate.",
            "overview_guardrail_copy": "New brand scans still run through",
            "overview_guardrail_tail": "Dimension prose is render-time derived by the current report renderer; no persisted generated_texts_per_dimension artifact is invented here.",
            "visual_evidence": "visual_evidence",
            "screenshots_primary": "screenshots are primary evidence",
            "visual_evidence_first": "Visual evidence first",
            "visual_evidence_intro": "Each capture keeps the raw viewport as primary evidence. Clean attempts and full-page captures are supplemental views for understanding obstruction, dismissal behavior, and what changed without reading raw JSON.",
            "captures": "captures",
            "raw_viewport": "raw viewport",
            "clean_attempt": "clean attempt",
            "full_page": "full page",
            "preview_screenshot": "Preview",
            "no_clean_attempt": "No clean attempt available",
            "missing_screenshot": "missing screenshot",
            "open_full_resolution": "open full-resolution",
            "capture": "Capture",
            "capture_story": "raw viewport is preserved as the evidence baseline.",
            "obstruction": "Obstruction",
            "obstruction_story": "was recorded with",
            "severity": "severity",
            "clean_attempt_recorded": "a safe dismissal attempt was recorded",
            "clean_attempt_reduced": "and reduced the obstruction",
            "clean_attempt_not_reduced": "but it did not materially reduce the obstruction",
            "clean_attempt_not_attempted": "no dismissal was attempted for this capture.",
            "preservation": "Preservation",
            "preservation_story": "supplemental captures do not replace the raw viewport.",
            "evidence_notes": "evidence notes",
            "no_curated_screenshots": "No curated screenshots were found under",
            "evidence_flow": "evidence_flow",
            "capture_to_review": "capture to review",
            "flow_capture_title": "1. Capture",
            "flow_capture_copy": "The viewport screenshot records the page as observed. This is the baseline artifact used for evidence review.",
            "flow_dismiss_title": "2. Obstruction dismissal",
            "flow_dismiss_copy": "When a safe candidate exists, the system can record an attempted dismissal. Unsafe or ambiguous actions remain blocked.",
            "flow_clean_title": "3. Clean attempt",
            "flow_clean_copy": "A clean-attempt image is supplemental. It helps compare what changed, but it does not overwrite the raw capture.",
            "flow_preserve_title": "4. Evidence preservation",
            "flow_preserve_copy": "Raw, clean-attempt, full-page, manifest, and audit artifacts stay linked so reviewers can inspect the lineage.",
            "status_summary": "status_summary",
            "governance_summary": "governance_calibration_reviewer_summary",
            "source_artifacts_only": "source artifacts only",
            "artifact_available": "Source artifact is available for local review.",
            "artifact_missing": "Source artifact is missing or unknown; the platform keeps rendering without it.",
            "artifact_metadata": "artifact metadata",
            "state": "state",
            "source": "source",
            "open_source": "open source",
            "human_review": "human_review",
            "screenshot_first_draft": "screenshot first · local-only draft",
            "evidence_first_review": "Evidence-first human review",
            "human_review_intro": "Inspect Headspace and Allbirds screenshots, answer structured visual questions, and draft outcome/confidence/notes without creating completed review records.",
            "open_human_review": "open human review",
            "records": "records",
            "shown": "shown",
            "item": "item",
            "status": "status",
            "metadata": "metadata",
            "source_artifacts": "source_artifacts",
            "raw_json_hidden": "raw JSON hidden by default",
            "open_source_artifact": "open source artifact",
            "raw_json_unavailable": "raw JSON unavailable for this artifact.",
            "what_to_do_next": "what_to_do_next",
            "no_write_actions": "no write actions",
            "screenshot_preview": "screenshot_preview",
            "in_site_visual_evidence": "in-site visual evidence",
            "screenshot_preview_sentence": "screenshot preview. Visual Signature Lab remains read-only, evidence-only, and separate from Brand3 Scoring.",
            "related_nav": "Related screenshot navigation",
            "previous": "Previous",
            "next": "Next",
            "back_to_overview": "Back to overview",
            "preview": "preview",
            "simulated_viewport": "Simulated viewport",
            "preview_mode": "Screenshot preview mode",
            "fit_viewport": "Fit viewport",
            "actual_size": "Actual size",
            "open_full_resolution_image": "Open full-resolution image",
            "related_captures": "related_captures",
            "same_brand": "same brand",
            "current": "current",
            "evidence_context": "evidence_context",
            "metadata_collapsed": "metadata collapsed",
            "available": "available",
            "no_matching_source": "No matching source row was found for this brand.",
            "human_review_title": "Visual Signature Lab Human Review",
            "human_review_header_tag": "screenshot first · evidence-only · no persistence",
            "human_review_intro_full": "Evidence-first human review for the Visual Signature Lab. Draft answers are local-only in this phase and do not create completed review records.",
            "visible_evidence_only": "Use visible evidence only.",
            "human_review_guardrail": "This screen does not write review records, does not affect Brand3 Scoring, and does not call providers.",
            "review_queue": "review_queue",
            "selected": "selected",
            "pending": "pending",
            "active_capture": "active_capture",
            "primary_evidence": "Primary evidence",
            "supplemental_evidence": "Supplemental evidence",
            "primary_missing": "Primary raw viewport evidence is missing.",
            "structured_visual_questions": "structured_visual_questions",
            "answer_visible_only": "answer from visible evidence only",
            "semantic_guidance": "Semantic guidance",
            "question_category": "question category",
            "observation_type": "observation type",
            "yes": "yes",
            "partial": "partial",
            "no": "no",
            "uncertain": "uncertain",
            "what_mean": "What does this mean?",
            "category": "category",
            "answer_type": "answer type",
            "confidence": "confidence",
            "confidence_meaning": "Confidence means reviewer certainty from the available evidence.",
            "observation_vs_interpretation": "observation vs interpretation",
            "outcome_draft": "Outcome draft",
            "local_only_form": "Local-only form. Nothing is persisted from this screen.",
            "not_official_record": "This is not an official review record.",
            "drafts_validated": "Exported drafts must be validated before ingestion.",
            "reviewer_id": "Reviewer ID",
            "review_outcome": "Review outcome",
            "notes": "Notes",
            "contradiction_notes": "Contradiction notes",
            "additional_evidence_needed": "Additional evidence needed",
            "notes_placeholder": "Short evidence-based note.",
            "contradictions_placeholder": "Required when visible evidence contradicts the claim.",
            "missing_evidence_placeholder": "What would resolve uncertainty?",
            "export_draft": "Export draft review JSON",
            "review_record_preview": "review_record_preview",
            "no_completed_record": "no completed record generated",
            "preview_only": "Preview only. No review record is persisted from this screen in the current phase.",
            "selected_screenshot_refs": "selected screenshot refs",
            "local_draft_field": "local draft field",
            "advanced_metadata": "advanced_metadata",
            "collapsed_by_default": "collapsed by default",
            "source_artifacts_notes": "source artifacts and evidence notes",
            "collapsed": "collapsed",
            "artifact": "artifact",
        }
    return {
        **_visual_signature_ui("en"),
        "title_by_section": {
            "overview": "Laboratorio de firma visual",
            "governance": "Gobernanza del laboratorio de firma visual",
            "calibration": "Calibración del laboratorio de firma visual",
            "corpus": "Corpus del laboratorio de firma visual",
            "reviewer": "Revisión del laboratorio de firma visual",
        },
        "intro_by_section": {
            "overview": "Navegación de solo lectura del laboratorio de firma visual. La evidencia se muestra separada del Brand3 Scoring y no afecta al score, rúbrica, informe, proveedores ni runtime.",
            "governance": "Registro de capacidades, matriz de políticas runtime, integridad de gobernanza y plan de validación del laboratorio. Solo lectura.",
            "calibration": "Manifiestos, registros, informe de fiabilidad y estado de preparación de calibración del laboratorio. Solo lectura.",
            "corpus": "Manifiesto de expansión de corpus, métricas piloto, estado de cola y limitaciones del laboratorio. Solo lectura.",
            "reviewer": "Piloto de workflow de revisión, items seleccionados de cola, enlaces a packets y entrada local del visor de revisión. Solo lectura.",
        },
        "nav": {
            "/visual-signature": "Vista general",
            "/visual-signature/governance": "Gobernanza",
            "/visual-signature/calibration": "Calibración",
            "/visual-signature/corpus": "Corpus",
            "/visual-signature/reviewer": "Revisión",
        },
        "guardrails": {
            "evidence-only": "solo evidencia",
            "no scoring impact": "sin impacto en score",
            "no rubric impact": "sin impacto en rúbrica",
            "no production report impact": "sin impacto en informes",
            "no provider calls": "sin llamadas a proveedores",
            "no runtime mutation": "sin mutación runtime",
            "read-only source artifact navigation": "artefactos fuente en solo lectura",
            "no persistence": "sin persistencia",
            "no completed review records": "sin registros finales de revisión",
        },
        "screenshot_labels": {
            "raw viewport": "viewport bruto",
            "clean attempt": "intento limpio",
            "full page": "página completa",
        },
        "overview_guardrail_title": "Brand3 Scoring sigue separado.",
        "overview_guardrail_copy": "Los nuevos scans de marca siguen pasando por",
        "overview_guardrail_tail": "La prosa por dimensión se deriva en render desde el renderer actual; no se inventa ningún artifact persisted generated_texts_per_dimension.",
        "visual_evidence": "evidencia_visual",
        "screenshots_primary": "los screenshots son evidencia primaria",
        "visual_evidence_first": "Primero evidencia visual",
        "visual_evidence_intro": "Cada captura conserva el viewport bruto como evidencia primaria. Los intentos limpios y las capturas de página completa son vistas suplementarias para entender obstrucciones, comportamiento de cierre y qué cambió sin leer JSON bruto.",
        "captures": "capturas",
        "raw_viewport": "viewport bruto",
        "clean_attempt": "intento limpio",
        "full_page": "página completa",
        "preview_screenshot": "Previsualizar",
        "no_clean_attempt": "No hay intento limpio disponible",
        "missing_screenshot": "screenshot ausente",
        "open_full_resolution": "abrir resolución completa",
        "capture": "Captura",
        "capture_story": "el viewport bruto se conserva como baseline de evidencia.",
        "obstruction": "Obstrucción",
        "obstruction_story": "se registró con severidad",
        "severity": "",
        "clean_attempt_recorded": "se registró un intento seguro de cierre",
        "clean_attempt_reduced": "y redujo la obstrucción",
        "clean_attempt_not_reduced": "pero no redujo materialmente la obstrucción",
        "clean_attempt_not_attempted": "no se intentó cerrar nada en esta captura.",
        "preservation": "Preservación",
        "preservation_story": "las capturas suplementarias no sustituyen el viewport bruto.",
        "evidence_notes": "notas de evidencia",
        "no_curated_screenshots": "No se encontraron screenshots curados en",
        "evidence_flow": "flujo_de_evidencia",
        "capture_to_review": "de captura a revisión",
        "flow_capture_title": "1. Captura",
        "flow_capture_copy": "El screenshot del viewport registra la página tal como fue observada. Es el artefacto base para revisar evidencia.",
        "flow_dismiss_title": "2. Cierre de obstrucción",
        "flow_dismiss_copy": "Cuando existe un candidato seguro, el sistema puede registrar un intento de cierre. Las acciones ambiguas o inseguras quedan bloqueadas.",
        "flow_clean_title": "3. Intento limpio",
        "flow_clean_copy": "La imagen de intento limpio es suplementaria. Ayuda a comparar qué cambió, pero no sobrescribe la captura bruta.",
        "flow_preserve_title": "4. Preservación de evidencia",
        "flow_preserve_copy": "Viewport bruto, intento limpio, página completa, manifest y audit quedan vinculados para inspeccionar el linaje.",
        "status_summary": "resumen_de_estado",
        "governance_summary": "resumen_gobernanza_calibracion_revision",
        "source_artifacts_only": "solo artefactos fuente",
        "artifact_available": "El artefacto fuente está disponible para revisión local.",
        "artifact_missing": "El artefacto fuente falta o es desconocido; la plataforma sigue renderizando.",
        "artifact_metadata": "metadata del artefacto",
        "state": "estado",
        "source": "fuente",
        "open_source": "abrir fuente",
        "human_review": "revision_humana",
        "screenshot_first_draft": "screenshot primero · borrador local",
        "evidence_first_review": "Revisión humana centrada en evidencia",
        "human_review_intro": "Inspecciona screenshots de Headspace y Allbirds, responde preguntas visuales estructuradas y redacta outcome/confianza/notas sin crear registros finales de revisión.",
        "open_human_review": "abrir revisión humana",
        "records": "registros",
        "shown": "mostrados",
        "item": "item",
        "status": "estado",
        "metadata": "metadata",
        "source_artifacts": "artefactos_fuente",
        "raw_json_hidden": "JSON bruto oculto por defecto",
        "open_source_artifact": "abrir artefacto fuente",
        "raw_json_unavailable": "JSON bruto no disponible para este artefacto.",
        "what_to_do_next": "siguiente_paso",
        "no_write_actions": "sin acciones de escritura",
        "screenshot_preview": "preview_de_screenshot",
        "in_site_visual_evidence": "evidencia visual dentro de la app",
        "screenshot_preview_sentence": "preview de screenshot. Visual Signature Lab sigue siendo solo lectura, solo evidencia y separado de Brand3 Scoring.",
        "related_nav": "Navegación de screenshots relacionados",
        "previous": "Anterior",
        "next": "Siguiente",
        "back_to_overview": "Volver a vista general",
        "preview": "preview",
        "simulated_viewport": "Viewport simulado",
        "preview_mode": "Modo de preview del screenshot",
        "fit_viewport": "Ajustar al viewport",
        "actual_size": "Tamaño real",
        "open_full_resolution_image": "Abrir imagen en resolución completa",
        "related_captures": "capturas_relacionadas",
        "same_brand": "misma marca",
        "current": "actual",
        "evidence_context": "contexto_de_evidencia",
        "metadata_collapsed": "metadata colapsada",
        "available": "disponible",
        "no_matching_source": "No se encontró una fila fuente para esta marca.",
        "human_review_title": "Revisión humana del laboratorio de firma visual",
        "human_review_header_tag": "screenshot primero · solo evidencia · sin persistencia",
        "human_review_intro_full": "Revisión humana centrada en evidencia para Visual Signature Lab. En esta fase, las respuestas son borradores locales y no crean registros finales.",
        "visible_evidence_only": "Usa sólo evidencia visible.",
        "human_review_guardrail": "Esta pantalla no escribe registros de revisión, no afecta a Brand3 Scoring y no llama a proveedores.",
        "review_queue": "cola_de_revision",
        "selected": "seleccionados",
        "pending": "pendientes",
        "active_capture": "captura_activa",
        "primary_evidence": "Evidencia primaria",
        "supplemental_evidence": "Evidencia suplementaria",
        "primary_missing": "Falta la evidencia primaria del viewport bruto.",
        "structured_visual_questions": "preguntas_visuales_estructuradas",
        "answer_visible_only": "responder sólo desde evidencia visible",
        "semantic_guidance": "Guía semántica",
        "question_category": "categoría de pregunta",
        "observation_type": "tipo de observación",
        "yes": "sí",
        "partial": "parcial",
        "no": "no",
        "uncertain": "incierto",
        "what_mean": "Qué significa esto",
        "category": "categoría",
        "answer_type": "tipo de respuesta",
        "confidence": "confianza",
        "confidence_meaning": "Confianza significa certeza del revisor a partir de la evidencia disponible.",
        "observation_vs_interpretation": "observación vs interpretación",
        "outcome_draft": "Borrador de outcome",
        "local_only_form": "Formulario local. Nada se persiste desde esta pantalla.",
        "not_official_record": "Esto no es un registro oficial de revisión.",
        "drafts_validated": "Los borradores exportados deben validarse antes de ingerirse.",
        "reviewer_id": "ID del revisor",
        "review_outcome": "Resultado de revisión",
        "notes": "Notas",
        "contradiction_notes": "Notas de contradicción",
        "additional_evidence_needed": "Evidencia adicional necesaria",
        "notes_placeholder": "Nota breve basada en evidencia.",
        "contradictions_placeholder": "Obligatorio cuando la evidencia visible contradice el claim.",
        "missing_evidence_placeholder": "Qué resolvería la incertidumbre?",
        "export_draft": "Exportar borrador JSON",
        "review_record_preview": "preview_de_registro",
        "no_completed_record": "sin registro final generado",
        "preview_only": "Sólo preview. No se persiste ningún registro de revisión desde esta pantalla en la fase actual.",
        "selected_screenshot_refs": "referencias de screenshot seleccionadas",
        "local_draft_field": "campo de borrador local",
        "advanced_metadata": "metadata_avanzada",
        "collapsed_by_default": "colapsada por defecto",
        "source_artifacts_notes": "artefactos fuente y notas de evidencia",
        "collapsed": "colapsado",
        "artifact": "artefacto",
    }
