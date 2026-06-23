"""Client-facing TLDR v2 normalization helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.features.magnetism.analyst_tldr import TLDR_KEYS
from src.reports.experimental_perceptual_narrative import build_perceptual_narrative_hints
from src.features.magnetism.client_tldr_v2_support_runtime import _normalize_choice
from src.features.magnetism.client_tldr_v2_support_contract import CLIENT_TLDR_V2_PROMPT_VERSION

def normalize_client_tldr_v2_response(
    raw: dict[str, Any],
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    perceptual_guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if "blocks" in raw or "executive_reading" in raw or "score_note" in raw or "caveats" in raw:
        return _normalize_client_tldr_v2_editorial_response(
            raw,
            brand_name=brand_name,
            url=url,
            current_tldr=current_tldr,
            score_provenance=score_provenance,
            report_base=report_base,
            lang=lang,
            perceptual_guidance=perceptual_guidance or {},
        )
    return _normalize_client_tldr_v2_legacy_response(
        raw,
        brand_name=brand_name,
        url=url,
        current_tldr=current_tldr,
        score_provenance=score_provenance,
        report_base=report_base,
        lang=lang,
        perceptual_guidance=perceptual_guidance or {},
    )


def _normalize_client_tldr_v2_editorial_response(
    raw: dict[str, Any],
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    perceptual_guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score_note = _clean_text(raw.get("score_note"))
    executive_reading = _clean_text(raw.get("executive_reading"))
    score_reading = _normalize_score_reading(
        raw.get("score_reading"),
        score_provenance,
        lang,
        score_note=score_note or executive_reading,
    )
    normalized_blocks: dict[str, str] = {}
    legacy_blocks: dict[str, Any] = {}
    validation_notes: list[str] = []
    for key in TLDR_KEYS:
        raw_block = _resolve_client_tldr_v2_block(raw, key)
        legacy_block, notes = _normalize_client_block(
            key,
            raw_block,
            current_tldr.get(key) if isinstance(current_tldr, dict) else {},
            lang=lang,
        )
        legacy_blocks[key] = legacy_block
        block_text = _client_tldr_v2_block_text(raw_block)
        if not block_text:
            block_text = _clean_text(legacy_block.get("answer") or legacy_block.get("content"))
        normalized_blocks[key] = block_text
        validation_notes.extend(notes)

    caveats = _clean_list(raw.get("caveats"))
    system_reading = _normalize_system_reading(
        raw.get("system_reading"),
        score_provenance,
        report_base,
        lang,
        executive_reading=executive_reading,
        caveats=caveats,
    )
    system_reading = _client_system_reading(system_reading)
    if executive_reading and not system_reading.get("diagnosis"):
        system_reading["diagnosis"] = executive_reading
    if score_note:
        score_reading["note"] = score_note
    evidence_refs = _collect_evidence_refs(legacy_blocks, score_provenance)
    validation_notes.extend(_validation_notes(legacy_blocks, score_provenance, _legacy_system_reading(system_reading)))
    validation_notes.extend(caveats)
    return {
        "prompt_version": CLIENT_TLDR_V2_PROMPT_VERSION,
        "generation_mode": "llm_client_v2",
        "brand_name": brand_name,
        "url": url,
        "score_reading": score_reading,
        "executive_reading": executive_reading,
        "score_note": score_note,
        "blocks": normalized_blocks,
        "legacy_tldr_brand3_v2": legacy_blocks,
        "system_reading": system_reading,
        "caveats": caveats,
        "evidence_refs": evidence_refs,
        "validation_notes": _unique(validation_notes),
        "display_score_source": score_reading.get("display_source"),
        "recommended_display_score": score_reading.get("value"),
    }


_SCORE_LABELS = {
    "en": {
        "computed": "Calculated score",
        "reviewed": "Reviewed score",
        "blocked": "Score withheld",
        "limited_confidence": "Limited-confidence score",
        "unavailable": "Score unavailable",
    },
    "es": {
        "computed": "Score calculado",
        "reviewed": "Score revisado",
        "blocked": "Score retenido",
        "limited_confidence": "Score con confianza limitada",
        "unavailable": "Score no disponible",
    },
}


_SCORE_NOTES = {
    "en": {
        "computed": "Based on the current evidence set.",
        "reviewed": "A human-reviewed score is available for display.",
        "blocked": "The score is being held back until the technical review settles.",
        "limited_confidence": "The score is usable, but the underlying check is limited.",
        "unavailable": "No displayable score is available for this run.",
    },
    "es": {
        "computed": "Basado en el conjunto de evidencia actual.",
        "reviewed": "Hay un score revisado por una persona disponible para mostrar.",
        "blocked": "El score se retiene hasta que se resuelva la revisión técnica.",
        "limited_confidence": "El score es utilizable, pero la base de verificación sigue siendo limitada.",
        "unavailable": "No hay un score mostrable para esta ejecución.",
    },
}


_SYSTEM_READING_LABELS = {
    "en": {
        "credibility_support": "Credibility support",
        "strategic_tensions": "Strategic tensions",
        "validation_questions": "Validation questions",
        "diagnosis": "Diagnosis",
        "limitations": "Limitations",
    },
    "es": {
        "credibility_support": "Soporte de credibilidad",
        "strategic_tensions": "Tensiones estratégicas",
        "validation_questions": "Preguntas de validación",
        "diagnosis": "Diagnóstico",
        "limitations": "Limitaciones",
    },
}


def _normalize_client_tldr_v2_legacy_response(
    raw: dict[str, Any],
    *,
    brand_name: str,
    url: str,
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    report_base: dict[str, Any],
    lang: str,
    perceptual_guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score_reading = _normalize_score_reading(raw.get("score_reading"), score_provenance, lang)
    raw_blocks = raw.get("tldr_brand3_v2") if isinstance(raw.get("tldr_brand3_v2"), dict) else {}
    normalized_blocks: dict[str, str] = {}
    legacy_blocks: dict[str, Any] = {}
    validation_notes: list[str] = []
    for key in TLDR_KEYS:
        raw_block = _resolve_client_tldr_v2_block(raw, key)
        legacy_block, notes = _normalize_client_block(
            key,
            raw_block,
            current_tldr.get(key) if isinstance(current_tldr, dict) else {},
            lang=lang,
        )
        legacy_blocks[key] = legacy_block
        block_text = _client_tldr_v2_block_text(raw_block) or _clean_text(legacy_block.get("answer") or legacy_block.get("content"))
        normalized_blocks[key] = block_text
        validation_notes.extend(notes)

    system_reading = _normalize_system_reading(raw.get("system_reading"), score_provenance, report_base, lang)
    system_reading = _client_system_reading(system_reading)
    evidence_refs = _collect_evidence_refs(legacy_blocks, score_provenance)
    validation_notes.extend(_validation_notes(legacy_blocks, score_provenance, _legacy_system_reading(system_reading)))
    return {
        "prompt_version": CLIENT_TLDR_V2_PROMPT_VERSION,
        "generation_mode": "llm_client_v2",
        "brand_name": brand_name,
        "url": url,
        "score_reading": score_reading,
        "blocks": normalized_blocks,
        "legacy_tldr_brand3_v2": legacy_blocks,
        "system_reading": system_reading,
        "evidence_refs": evidence_refs,
        "validation_notes": _unique(validation_notes),
        "display_score_source": score_reading.get("display_source"),
        "recommended_display_score": score_reading.get("value"),
    }


def _normalize_client_block(
    key: str,
    raw_block: Any,
    source_block: dict[str, Any],
    *,
    lang: str,
) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    raw = raw_block if isinstance(raw_block, dict) else {}
    raw_text = _clean_text(raw_block) if isinstance(raw_block, str) else ""
    source_answer = _clean_text(source_block.get("answer") or source_block.get("content"))
    answer = _clean_text(raw.get("answer") or raw.get("content") or raw_text) or source_answer
    question = _clean_text(raw.get("question")) or _question_for_block(key, lang)
    claim_type = _normalize_choice(
        raw.get("claim_type"),
        {"declared", "performed", "inferred", "absent"},
        fallback="inferred" if answer else "absent",
    )
    mode = _normalize_choice(
        raw.get("mode"),
        {"literal", "interpreted_from_discourse", "needs_human_review", "not_detected"},
        fallback="interpreted_from_discourse" if answer else "not_detected",
    )
    confidence = _normalize_choice(raw.get("confidence"), {"high", "medium", "low"}, fallback="medium" if answer else "low")
    evidence_refs = _clean_list(raw.get("evidence_refs")) or [source.get("url") for source in source_block.get("evidence_sources", []) if source.get("url")]
    caveat = _clean_text(raw.get("caveat"))
    validation_question = _clean_text(raw.get("validation_question"))
    reasoning = _clean_text(raw.get("reasoning") or raw.get("rationale") or source_block.get("reasoning"))
    if not evidence_refs and answer:
        notes.append(f"{key}: answer present without evidence refs.")
        caveat = caveat or (
            "This block is still lightly evidenced." if lang == "en" else "Este bloque todavía está poco evidenciado."
        )
        validation_question = validation_question or _question_for_block(key, lang)
        mode = "needs_human_review"
        confidence = "low"
    if not answer:
        claim_type = "absent"
        mode = "not_detected"
        confidence = "low"
    if not reasoning and answer:
        reasoning = (
            "This reading is grounded in the available evidence and the current score context."
            if lang == "en"
            else "Esta lectura se apoya en la evidencia disponible y en el contexto del score."
        )
    if not validation_question and confidence in {"low", "medium"}:
        validation_question = _question_for_block(key, lang)
    if not caveat and confidence == "low":
        caveat = (
            "Treat this as a working reading, not a conclusion."
            if lang == "en"
            else "Trátalo como una lectura de trabajo, no como una conclusión."
        )
    if not evidence_refs and source_block.get("evidence_sources"):
        evidence_refs = [source.get("url") for source in source_block.get("evidence_sources", []) if source.get("url")]
    block = {
        "block": key,
        "question": question,
        "answer": answer or None,
        "content": answer or None,
        "claim_type": claim_type,
        "mode": mode,
        "confidence": confidence,
        "reasoning": reasoning,
        "rationale": reasoning,
        "evidence_used": _clean_list(source_block.get("evidence_used")),
        "evidence_sources": _normalize_evidence_sources(source_block.get("evidence_sources")),
        "evidence_refs": [ref for ref in evidence_refs if isinstance(ref, str) and ref.strip()],
        "counter_evidence": _clean_list(source_block.get("counter_evidence")),
        "human_review_recommended": bool(raw.get("human_review_recommended")) or mode == "needs_human_review" or confidence == "low",
        "validation_question": validation_question,
        "caveat": caveat,
        "detected": bool(answer) and mode != "not_detected",
    }
    return block, notes


def _client_tldr_v2_block_aliases(key: str) -> list[str]:
    spaced = key.replace("_", " ")
    title = spaced.title()
    kebab = key.replace("_", "-")
    compact = key.replace("_", "")
    return [
        key,
        key.upper(),
        spaced,
        spaced.upper(),
        title,
        title.upper(),
        kebab,
        kebab.upper(),
        compact,
        compact.upper(),
    ]


def _client_tldr_v2_block_text(raw_block: Any) -> str:
    if isinstance(raw_block, str):
        return _clean_text(raw_block)
    if isinstance(raw_block, dict):
        for field in ("answer", "content", "text", "reading"):
            text = _clean_text(raw_block.get(field))
            if text:
                return text
        return _clean_text(str(raw_block))
    return ""


def _resolve_client_tldr_v2_block(raw: dict[str, Any], key: str) -> Any:
    if not isinstance(raw, dict):
        return None
    candidate_maps: list[dict[str, Any]] = []
    for candidate in (raw.get("blocks"), raw.get("tldr_brand3_v2"), raw):
        if isinstance(candidate, dict):
            candidate_maps.append(candidate)
    aliases = _client_tldr_v2_block_aliases(key)
    for candidate_map in candidate_maps:
        for alias in aliases:
            if alias in candidate_map:
                return candidate_map.get(alias)
    return None


def _normalize_score_reading(
    raw: Any,
    provenance: dict[str, Any],
    lang: str,
    *,
    score_note: str | None = None,
) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    fallback = _build_score_reading(provenance, lang)
    status = fallback["status"]
    value = fallback.get("value")
    label = fallback["label"]
    note = fallback["note"] if value is None else (_clean_text(source.get("note")) or _clean_text(score_note) or fallback["note"])
    confidence = fallback["confidence"]
    return {
        "status": status,
        "display_source": fallback.get("display_source"),
        "label": label,
        "note": note,
        "value": value,
        "confidence": confidence,
        "limited_confidence": fallback.get("limited_confidence", False) or status == "limited_confidence",
    }


def _client_score_provenance(
    score_provenance: dict[str, Any],
    *,
    scanner_display_score: Any | None,
) -> dict[str, Any]:
    """Prefer the persisted Magnetism scan score for client TLDR display.

    The internal audit score may be blocked by replay drift. That decision should
    remain intact for internal audit pages, but TLDR v2 is attached to a persisted
    Magnetism scan that already has its own client-facing score.
    """

    provenance = deepcopy(score_provenance or {})
    score = _display_score_number(scanner_display_score)
    if score is None:
        return provenance
    if (
        provenance.get("display_score_source") != "blocked"
        and provenance.get("recommended_display_score") is not None
    ):
        return provenance

    provenance["display_score_source"] = "computed"
    provenance["recommended_display_score"] = score
    provenance["client_display_score_source"] = "magnetism_scan"
    provenance["client_score_fallback"] = {
        "source": "magnetism_scan",
        "reason": "audit_display_blocked",
    }
    return provenance


def _display_score_number(value: Any) -> float | None:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0 or score > 100:
        return None
    return score


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


def _normalize_tldr_blocks(current_tldr: dict[str, Any] | None) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    source = current_tldr if isinstance(current_tldr, dict) else {}
    for key in TLDR_KEYS:
        block = source.get(key) if isinstance(source.get(key), dict) else {}
        answer = _clean_text(block.get("answer") or block.get("content"))
        compact[key] = {
            "block": key,
            "question": _clean_text(block.get("question")),
            "answer": answer or None,
            "content": answer or None,
            "claim_type": _clean_text(block.get("claim_type")) or ("inferred" if answer else "absent"),
            "mode": _clean_text(block.get("mode")) or ("interpreted_from_discourse" if answer else "not_detected"),
            "confidence": _clean_text(block.get("confidence")) or ("medium" if answer else "low"),
            "reasoning": _clean_text(block.get("reasoning") or block.get("rationale")),
            "rationale": _clean_text(block.get("reasoning") or block.get("rationale")),
            "evidence_used": _clean_list(block.get("evidence_used") or block.get("evidence")),
            "evidence_sources": _normalize_evidence_sources(block.get("evidence_sources")),
            "counter_evidence": _clean_list(block.get("counter_evidence")),
            "human_review_recommended": bool(block.get("human_review_recommended")),
            "detected": bool(answer) or bool(block.get("detected")),
        }
    return compact


def _build_score_reading(provenance: dict[str, Any], lang: str) -> dict[str, Any]:
    replay = provenance.get("replay_integrity") or {}
    status = str(replay.get("status") or "unavailable")
    display_source = str(provenance.get("display_score_source") or "blocked")
    limited_confidence = status == "unverifiable"

    if display_source == "reviewed":
        status_key = "reviewed"
    elif display_source == "computed":
        status_key = "limited_confidence" if limited_confidence else "computed"
    elif display_source == "blocked":
        status_key = "blocked"
    else:
        status_key = "unavailable"

    value = provenance.get("recommended_display_score")
    if status_key == "blocked":
        value = None

    note_key = status_key if status_key in _SCORE_NOTES[lang] else "unavailable"
    return {
        "status": status_key,
        "display_source": display_source,
        "label": _SCORE_LABELS[lang][note_key],
        "note": _SCORE_NOTES[lang][note_key],
        "value": value,
        "confidence": "low" if status_key in {"blocked", "limited_confidence", "unavailable"} else "high",
        "limited_confidence": limited_confidence,
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


def _normalize_evidence_sources(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    out: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            url = _clean_text(item.get("url") or item.get("source_url"))
            label = _clean_text(item.get("label") or item.get("source_label") or item.get("source_type"))
            source_key = _clean_text(item.get("source_key") or item.get("source_url") or item.get("url"))
        else:
            url = _clean_text(item)
            label = ""
            source_key = _clean_text(item)
        if not url and not source_key:
            continue
        out.append(
            {
                "url": url or source_key,
                "label": label or source_key or url,
                "source_key": source_key or url,
            }
        )
    return out


def _validation_notes(
    current_tldr: dict[str, Any],
    score_provenance: dict[str, Any],
    system_reading: dict[str, Any],
) -> list[str]:
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


def _question_for_block(key: str, language: str) -> str:
    questions = {
        "core_purpose": {
            "en": "What is the clearest visible purpose behind the brand?",
            "es": "¿Cuál es el propósito visible más claro detrás de la marca?",
        },
        "magnetism": {
            "en": "What phrase or tension is most memorable here?",
            "es": "¿Qué frase o tensión resulta más memorable aquí?",
        },
        "value_proposition": {
            "en": "What changes for the audience when they choose this brand?",
            "es": "¿Qué cambia para la audiencia cuando elige esta marca?",
        },
        "personality": {
            "en": "What personality is actually visible in the brand's voice and behavior?",
            "es": "¿Qué personalidad es realmente visible en la voz y el comportamiento de la marca?",
        },
        "brand_idea": {
            "en": "What concept connects the offer, the expression, and the metaphor?",
            "es": "¿Qué concepto conecta la oferta, la expresión y la metáfora?",
        },
        "attributes": {
            "en": "Which attributes are truly repeated across the evidence?",
            "es": "¿Qué atributos se repiten de verdad en la evidencia?",
        },
        "values": {
            "en": "Which values are defended through behavior rather than declared only in words?",
            "es": "¿Qué valores se defienden con comportamiento y no solo con palabras?",
        },
        "mission": {
            "en": "What does the brand concretely do today?",
            "es": "¿Qué hace concretamente la marca hoy?",
        },
        "vision": {
            "en": "What future shift is the brand trying to make visible?",
            "es": "¿Qué cambio futuro intenta hacer visible la marca?",
        },
    }
    return questions.get(key, {}).get(language, questions.get(key, {}).get("en", ""))


def _block_label(key: str, language: str) -> str:
    labels = {
        "core_purpose": {"en": "Core purpose", "es": "Propósito central"},
        "magnetism": {"en": "Magnetism", "es": "Magnetismo"},
        "value_proposition": {"en": "Value proposition", "es": "Propuesta de valor"},
        "personality": {"en": "Personality", "es": "Personalidad"},
        "brand_idea": {"en": "Brand idea", "es": "Idea de marca"},
        "attributes": {"en": "Attributes", "es": "Atributos"},
        "values": {"en": "Values", "es": "Valores"},
        "mission": {"en": "Mission", "es": "Misión"},
        "vision": {"en": "Vision", "es": "Visión"},
    }
    return labels.get(key, {}).get(language, labels.get(key, {}).get("en", key))


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


def _normalize_list_text_values(value: Any) -> list[str]:
    return _unique(_clean_list(value))


def _normalize_list_dict_values(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            output.append(item)
    return output


def _unique(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        text = _clean_text(value)
        if text and text not in output:
            output.append(text)
    return output
