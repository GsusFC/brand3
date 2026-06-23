"""System-reading normalization helpers for client TLDR v2."""

from __future__ import annotations

from typing import Any

from src.features.magnetism.analyst_tldr import TLDR_KEYS
from src.features.magnetism.client_tldr_v2_support_contract import CLIENT_TLDR_V2_PROMPT_VERSION
from src.features.magnetism.client_tldr_v2_support_normalization_score import (
    _SYSTEM_READING_LABELS,
    _build_score_reading,
)
from src.features.magnetism.client_tldr_v2_support_runtime import _normalize_choice
from src.features.magnetism.client_tldr_v2_support_normalization_system_text import (
    _block_label,
    _question_for_block,
)
from src.reports.experimental_perceptual_narrative import build_perceptual_narrative_hints


def _normalize_system_reading(
    raw: Any,
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    *,
    executive_reading: str = "",
    caveats: list[str] | None = None,
) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    fallback = _build_system_reading(
        brand_name=str((report_base.get("brand") or {}).get("name") or ""),
        url=str((report_base.get("brand") or {}).get("url") or ""),
        current_tldr={},
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
    )
    credibility_raw = source.get("credibility_support")
    if isinstance(credibility_raw, dict):
        credibility_status = _normalize_choice(
            credibility_raw.get("status"),
            {"observed", "partial"},
            fallback=fallback["credibility_support"]["status"],
        )
        credibility_reading = _clean_text(credibility_raw.get("reading")) or fallback["credibility_support"]["reading"]
        credibility_refs = _clean_list(credibility_raw.get("evidence_refs")) or fallback["credibility_support"]["evidence_refs"]
    else:
        credibility_status = fallback["credibility_support"]["status"]
        credibility_reading = _clean_text(credibility_raw) or fallback["credibility_support"]["reading"]
        credibility_refs = fallback["credibility_support"]["evidence_refs"]
    strategic_tensions = _clean_list(source.get("strategic_tensions")) or fallback["strategic_tensions"]
    validation_questions = _clean_list(source.get("validation_questions")) or fallback["validation_questions"]
    diagnosis = _clean_text(source.get("diagnosis")) or _clean_text(executive_reading) or fallback["diagnosis"]
    limitations = _clean_list(source.get("limitations")) or _clean_list(caveats) or fallback["limitations"]
    return {
        "credibility_support": {
            "status": credibility_status,
            "reading": credibility_reading,
            "evidence_refs": credibility_refs,
        },
        "strategic_tensions": strategic_tensions,
        "validation_questions": validation_questions,
        "diagnosis": diagnosis,
        "limitations": limitations,
        "labels": fallback["labels"],
    }


def _client_system_reading(system_reading: dict[str, Any]) -> dict[str, Any]:
    source = system_reading if isinstance(system_reading, dict) else {}
    credibility = source.get("credibility_support")
    credibility_reading = ""
    if isinstance(credibility, dict):
        credibility_reading = _clean_text(credibility.get("reading"))
    else:
        credibility_reading = _clean_text(credibility)
    return {
        "credibility_support": credibility_reading,
        "strategic_tensions": _clean_list(source.get("strategic_tensions")),
        "validation_questions": _clean_list(source.get("validation_questions")),
        "diagnosis": _clean_text(source.get("diagnosis")),
        "limitations": _clean_list(source.get("limitations")),
    }


def _legacy_system_reading(system_reading: dict[str, Any]) -> dict[str, Any]:
    source = system_reading if isinstance(system_reading, dict) else {}
    credibility = source.get("credibility_support")
    if isinstance(credibility, dict):
        credibility_status = _clean_text(credibility.get("status")) or "partial"
        credibility_reading = _clean_text(credibility.get("reading"))
        credibility_refs = _clean_list(credibility.get("evidence_refs"))
    else:
        credibility_status = "partial"
        credibility_reading = _clean_text(credibility)
        credibility_refs = []
    return {
        "credibility_support": {
            "status": credibility_status,
            "reading": credibility_reading,
            "evidence_refs": credibility_refs,
        },
        "strategic_tensions": _clean_list(source.get("strategic_tensions")),
        "validation_questions": _clean_list(source.get("validation_questions")),
        "diagnosis": _clean_text(source.get("diagnosis")),
        "limitations": _clean_list(source.get("limitations")),
    }


def _fallback_payload(
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
) -> dict[str, Any]:
    score_reading = _build_score_reading(score_provenance, lang)
    system_reading = _build_system_reading(
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
    )
    evidence_refs = _collect_evidence_refs(current_tldr, score_provenance)
    validation_notes = _validation_notes(current_tldr, score_provenance, system_reading)
    return {
        "prompt_version": CLIENT_TLDR_V2_PROMPT_VERSION,
        "generation_mode": "fallback_client_v2",
        "brand_name": brand_name,
        "url": url,
        "score_reading": score_reading,
        "legacy_tldr_brand3_v2": current_tldr,
        "system_reading": system_reading,
        "evidence_refs": evidence_refs,
        "validation_notes": validation_notes,
        "display_score_source": score_reading.get("display_source"),
        "recommended_display_score": score_reading.get("value"),
    }


def _build_system_reading(
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
) -> dict[str, Any]:
    del brand_name
    del url
    evaluation = report_base.get("evaluation") if isinstance(report_base.get("evaluation"), dict) else {}
    readiness = evaluation.get("readiness") if isinstance(evaluation.get("readiness"), dict) else {}
    trust_summary = evaluation.get("trust_summary") if isinstance(evaluation.get("trust_summary"), dict) else {}
    confidence_summary = score_provenance.get("confidence_summary") if isinstance(score_provenance.get("confidence_summary"), dict) else {}
    fallback_flags = score_provenance.get("fallback_flags") if isinstance(score_provenance.get("fallback_flags"), dict) else {}
    warnings = [str(item) for item in (score_provenance.get("warnings") or []) if str(item).strip()]
    status = str((score_provenance.get("display_score_source") or "blocked"))
    score_status = str((score_provenance.get("replay_integrity") or {}).get("status") or "unverifiable")

    credibility_status = "observed"
    if status == "blocked" or score_status == "unverifiable":
        credibility_status = "partial"
    elif warnings or fallback_flags.get("replay_neutral_fallback_dimensions"):
        credibility_status = "partial"

    credibility_refs = [ref for ref in _collect_evidence_refs(current_tldr, score_provenance)[:3]]
    credibility_reading = _credibility_reading(
        language=lang,
        credibility_status=credibility_status,
        trust_summary=trust_summary,
        warnings=warnings,
        evidence_refs=credibility_refs,
        score_status=status,
    )

    strategic_tensions = _collect_strategic_tensions(
        language=lang,
        report_base=report_base,
        score_provenance=score_provenance,
    )
    validation_questions = _collect_validation_questions(
        language=lang,
        current_tldr=current_tldr,
        confidence_summary=confidence_summary,
        fallback_flags=fallback_flags,
    )
    diagnosis = _diagnosis_text(
        language=lang,
        score_reading=_build_score_reading(score_provenance, lang),
        report_base=report_base,
    )
    limitations = _collect_limitations(
        language=lang,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
    )

    return {
        "credibility_support": {
            "status": credibility_status,
            "reading": credibility_reading,
            "evidence_refs": credibility_refs,
        },
        "strategic_tensions": strategic_tensions,
        "validation_questions": validation_questions,
        "diagnosis": diagnosis,
        "limitations": limitations,
        "labels": _SYSTEM_READING_LABELS[lang],
    }


def _credibility_reading(
    *,
    language: str,
    credibility_status: str,
    trust_summary: dict[str, Any],
    warnings: list[str],
    evidence_refs: list[dict[str, str]],
    score_status: str,
) -> str:
    has_refs = bool(evidence_refs)
    if language == "en":
        if credibility_status == "observed":
            text = "The available evidence supports a cautious, evidence-bound reading."
        else:
            text = "The reading is useful, but some parts still rely on partial or support-level signals."
        if warnings:
            text += " Some signals remain provisional."
        if has_refs:
            text += " Traceable references are attached."
        return text

    if credibility_status == "observed":
        text = "La evidencia disponible sostiene una lectura cauta y bien acotada."
    else:
        text = "La lectura es útil, pero algunas partes siguen dependiendo de señales parciales o de respaldo."
    if warnings:
        text += " Algunas señales siguen siendo provisionales."
    if has_refs:
        text += " Se adjuntan referencias trazables."
    if str(trust_summary.get("overall_status") or "") == "insufficient":
        text += " La cobertura total aún es limitada."
    if score_status == "blocked":
        text += " El score final todavía no se muestra."
    return text


def _collect_strategic_tensions(
    *,
    language: str,
    report_base: dict[str, Any],
    score_provenance: dict[str, Any],
) -> list[str]:
    tensions: list[str] = []
    dimensions = report_base.get("dimensions") or []
    for dim in dimensions:
        name = str(dim.get("name") or "")
        if not name:
            continue
        hints = build_perceptual_narrative_hints(name)
        for pattern in hints.matched_patterns:
            pattern_id = str(pattern.get("pattern_id") or "")
            pattern_name = str(pattern.get("pattern_name") or "")
            tension = _tension_from_pattern(pattern_id, pattern_name, language)
            if tension and tension not in tensions:
                tensions.append(tension)
            if len(tensions) >= 4:
                return tensions

    for warning in score_provenance.get("warnings") or []:
        warning_text = _warning_to_tension(str(warning), language)
        if warning_text and warning_text not in tensions:
            tensions.append(warning_text)
        if len(tensions) >= 4:
            break
    return tensions[:4]


def _collect_validation_questions(
    *,
    language: str,
    current_tldr: dict[str, Any],
    confidence_summary: dict[str, Any],
    fallback_flags: dict[str, Any],
) -> list[str]:
    if not isinstance(current_tldr, dict):
        current_tldr = {}
    del confidence_summary
    questions: list[str] = []
    for key in TLDR_KEYS:
        block = current_tldr.get(key) if isinstance(current_tldr.get(key), dict) else {}
        confidence = str(block.get("confidence") or "low")
        if confidence not in {"low", "medium"} and not block.get("human_review_recommended"):
            continue
        question = _question_for_block(key, language)
        if question and question not in questions:
            questions.append(question)
        if len(questions) >= 4:
            break

    if fallback_flags.get("replay_neutral_fallback_dimensions"):
        fallback_question = (
            "Which parts of the reading still depend on fallback signals?"
            if language == "en"
            else "¿Qué partes de la lectura siguen dependiendo de señales de respaldo?"
        )
        if fallback_question not in questions:
            questions.append(fallback_question)
    return questions[:4]


def _diagnosis_text(
    *,
    language: str,
    score_reading: dict[str, Any],
    report_base: dict[str, Any],
) -> str:
    value = score_reading.get("value")
    if language == "en":
        if score_reading.get("status") == "reviewed":
            return "The client reading combines observed evidence with a human-reviewed score."
        if score_reading.get("status") == "blocked":
            return "The strategic reading is available, but the final score remains withheld for review."
        if score_reading.get("limited_confidence"):
            return "The reading is usable, but some parts should still be treated as provisional."
        if value is not None:
            return f"The current reading is anchored by a {float(value):.1f}/100 score and the available evidence."
        return "The current reading is supported by the available evidence."

    if score_reading.get("status") == "reviewed":
        return "La lectura para cliente combina evidencia observada con un score revisado por una persona."
    if score_reading.get("status") == "blocked":
        return "La lectura estratégica está disponible, pero el score final sigue retenido para revisión."
    if score_reading.get("limited_confidence"):
        return "La lectura es utilizable, pero algunas partes todavía deben tratarse como provisionales."
    if value is not None:
        return f"La lectura actual se apoya en un score de {float(value):.1f}/100 y en la evidencia disponible."
    return "La lectura actual se apoya en la evidencia disponible."


def _collect_limitations(
    *,
    language: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
) -> list[str]:
    if not isinstance(current_tldr, dict):
        current_tldr = {}
    limitations: list[str] = []
    if language == "en":
        add = limitations.append
    else:
        add = limitations.append

    if score_provenance.get("warnings"):
        if language == "en":
            add("Some score signals still rely on support-level evidence.")
        else:
            add("Algunas señales del score siguen dependiendo de evidencia de respaldo.")

    if (score_provenance.get("fallback_flags") or {}).get("replay_neutral_fallback_dimensions"):
        if language == "en":
            add("A few dimensions still depend on fallback signals.")
        else:
            add("Algunas dimensiones todavía dependen de señales de respaldo.")

    for key in TLDR_KEYS:
        block = current_tldr.get(key) if isinstance(current_tldr.get(key), dict) else {}
        if block.get("human_review_recommended") or str(block.get("confidence") or "") == "low":
            label = _block_label(key, language)
            if language == "en":
                add(f"{label} remains provisional.")
            else:
                add(f"{label} sigue siendo provisional.")
            break

    readiness = report_base.get("evaluation", {}).get("readiness") if isinstance(report_base.get("evaluation"), dict) else {}
    if isinstance(readiness, dict) and readiness.get("warnings"):
        if language == "en":
            add("The evidence base still carries readiness warnings.")
        else:
            add("La base de evidencia todavía tiene warnings de readiness.")

    return _unique(limitations)[:4]


def _collect_evidence_refs(
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    if not isinstance(current_tldr, dict):
        current_tldr = {}
    refs: list[dict[str, str]] = []
    seen: set[str] = set()

    def _add(url: str, label: str, block: str) -> None:
        normalized = url.strip()
        if not normalized or normalized.lower() in seen:
            return
        seen.add(normalized.lower())
        refs.append({"url": normalized, "label": label, "block": block})

    for key in TLDR_KEYS:
        block = current_tldr.get(key) if isinstance(current_tldr.get(key), dict) else {}
        for source in block.get("evidence_sources") or []:
            if not isinstance(source, dict):
                continue
            url = _clean_text(source.get("url") or source.get("source_key"))
            label = _clean_text(source.get("label") or source.get("source_type") or key)
            if url:
                _add(url, label or key, key)
        for item in block.get("evidence_used") or []:
            if isinstance(item, str) and item.strip():
                _add(item, key, key)

    if isinstance(score_provenance, dict):
        for item in score_provenance.get("evidence_refs") or []:
            if isinstance(item, dict):
                url = _clean_text(item.get("url"))
                label = _clean_text(item.get("label") or item.get("block") or "evidence")
            else:
                url = _clean_text(item)
                label = "evidence"
            if url:
                _add(url, label, "score")

    return refs[:6]


def _validation_notes(
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    system_reading: dict[str, Any],
) -> list[str]:
    if not isinstance(current_tldr, dict):
        current_tldr = {}
    notes: list[str] = []
    for key in TLDR_KEYS:
        block = current_tldr.get(key) if isinstance(current_tldr.get(key), dict) else {}
        if not block.get("evidence_used") and not block.get("evidence_sources"):
            notes.append(f"{key}: answer present without evidence refs.")
        if block.get("human_review_recommended"):
            notes.append(f"{key}: marked as provisional.")
    if score_provenance.get("warnings"):
        notes.append("score_context: warnings present.")
    if (score_provenance.get("fallback_flags") or {}).get("replay_neutral_fallback_dimensions"):
        notes.append("score_context: fallback dimensions present.")
    if system_reading.get("limitations"):
        notes.append("system_reading: limitations surfaced.")
    return _unique(notes)


def _tension_from_pattern(pattern_id: str, pattern_name: str, language: str) -> str:
    mapping = {
        "pattern_category_surface_translation": {
            "en": "Category language only convinces when the surface makes it visible.",
            "es": "El lenguaje de categoría solo convence cuando la superficie lo vuelve visible.",
        },
        "pattern_evidence_bound_behavior": {
            "en": "The reading stays useful by staying anchored to what the evidence can support.",
            "es": "La lectura se vuelve útil cuando permanece anclada en lo que la evidencia sí puede sostener.",
        },
        "pattern_claim_signal_gap": {
            "en": "The visible promise still asks for more proof.",
            "es": "La promesa visible sigue pidiendo más prueba.",
        },
        "pattern_guided_movement": {
            "en": "Navigation and sequence can shape how attention moves through the story.",
            "es": "La navegación y la secuencia pueden guiar cómo avanza la atención por la historia.",
        },
        "pattern_system_cohesion_difference": {
            "en": "Consistency across surfaces supports a coherent reading.",
            "es": "La consistencia entre superficies apoya una lectura coherente.",
        },
        "pattern_concept_bearing_motion": {
            "en": "Motion only matters when real sequence or interaction evidence is visible.",
            "es": "El movimiento solo importa cuando hay evidencia real de secuencia o interacción.",
        },
        "pattern_threshold_pacing": {
            "en": "The rhythm of the page can change how quickly attention becomes action.",
            "es": "El ritmo de la página puede cambiar cómo la atención se convierte en acción.",
        },
    }
    if pattern_id in mapping:
        return mapping[pattern_id].get(language, mapping[pattern_id]["en"])
    if pattern_name:
        return pattern_name
    return ""


def _warning_to_tension(warning: str, language: str) -> str:
    warning = warning.lower()
    if "fallback" in warning or "neutral" in warning:
        return (
            "Some of the reading still depends on fallback signals."
            if language == "en"
            else "Parte de la lectura todavía depende de señales de respaldo."
        )
    if "low confidence" in warning or "insufficient" in warning:
        return (
            "The evidence base is still thin in a few places."
            if language == "en"
            else "La base de evidencia sigue siendo delgada en algunos puntos."
        )
    return ""


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        text = _clean_text(item)
        if text and text not in output:
            output.append(text)
    return output


def _unique(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in output:
            output.append(text)
    return output
