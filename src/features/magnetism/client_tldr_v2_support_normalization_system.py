"""System-reading normalization helpers for client TLDR v2."""

from __future__ import annotations

from typing import Any

from src.features.magnetism.client_tldr_v2_support_contract import CLIENT_TLDR_V2_PROMPT_VERSION
from src.features.magnetism.client_tldr_v2_support_normalization_score import (
    _SYSTEM_READING_LABELS,
    _build_score_reading,
)
from src.features.magnetism.client_tldr_v2_support_runtime import _normalize_choice
from src.features.magnetism.client_tldr_v2_support_normalization_system_support import (
    _collect_evidence_refs,
    _collect_limitations,
    _collect_strategic_tensions,
    _collect_validation_questions,
    _credibility_reading,
    _diagnosis_text,
    _clean_list,
    _clean_text,
    _validation_notes,
)


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
