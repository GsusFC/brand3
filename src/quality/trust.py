"""Shared trust status helpers for API and reports."""

from __future__ import annotations


def quality_label(value: float) -> str:
    if value >= 0.75:
        return "alta"
    if value >= 0.45:
        return "media"
    return "baja"


def dimension_status_counts_from_confidence(dimension_confidence: dict) -> dict[str, int]:
    counts = _empty_counts()
    for item in (dimension_confidence or {}).values():
        status = item.get("status") if isinstance(item, dict) else None
        if status in counts:
            counts[status] += 1
    return counts


def dimension_status_counts_from_report_dimensions(dimensions: list[dict]) -> dict[str, int]:
    counts = _empty_counts()
    for item in dimensions:
        status = item.get("confidence_status")
        if status in counts:
            counts[status] += 1
    return counts


def limited_dimensions_from_confidence(dimension_confidence: dict) -> list[dict[str, object]]:
    limited: list[dict[str, object]] = []
    for name, item in (dimension_confidence or {}).items():
        if not isinstance(item, dict):
            continue
        status = item.get("status") or "insufficient_data"
        missing_signals = item.get("missing_signals") or []
        if status == "good" and not missing_signals:
            continue
        limited.append({
            "name": name,
            "status": status,
            "coverage": item.get("coverage", 0.0),
            "confidence": item.get("confidence", 0.0),
            "confidence_reason": item.get("confidence_reason") or [],
            "missing_signals": missing_signals,
            "recommended_next_steps": item.get("recommended_next_steps") or [],
        })
    return limited


def limited_dimensions_from_report_dimensions(dimensions: list[dict]) -> list[dict[str, object]]:
    limited: list[dict[str, object]] = []
    for item in dimensions or []:
        status = item.get("confidence_status") or "insufficient_data"
        missing_signals = item.get("missing_signals") or []
        if status == "good" and not missing_signals:
            continue
        limited.append({
            "name": item.get("name"),
            "display_name": item.get("display_name") or item.get("name"),
            "status": status,
            "coverage": item.get("coverage", 0.0),
            "coverage_label": item.get("coverage_label"),
            "confidence": item.get("confidence", 0.0),
            "confidence_label": item.get("confidence_label"),
            "confidence_reason": item.get("confidence_reason") or [],
            "confidence_reason_labels": item.get("confidence_reason_labels") or [],
            "missing_signals": missing_signals,
            "recommended_next_steps": item.get("recommended_next_steps") or [],
        })
    return limited


def build_trust_summary(
    *,
    data_quality: str,
    context_summary: dict[str, object],
    evidence_summary: dict[str, object],
    dimension_status_counts: dict[str, int],
    limited_dimensions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    context_status = context_summary.get("status") if isinstance(context_summary, dict) else None
    overall_status = trust_overall_status(
        data_quality=data_quality,
        context_status=context_status,
        dimension_status_counts=dimension_status_counts,
    )
    return {
        "data_quality": data_quality,
        "overall_status": overall_status,
        "overall_status_label": trust_status_label(overall_status),
        "overall_reason": trust_overall_reason(
            data_quality=data_quality,
            context_status=context_status,
            dimension_status_counts=dimension_status_counts,
        ),
        "overall_reason_label": trust_overall_reason(
            data_quality=data_quality,
            context_status=context_status,
            dimension_status_counts=dimension_status_counts,
            locale="es",
        ),
        "context": context_summary,
        "evidence": evidence_summary,
        "dimension_status_counts": dimension_status_counts,
        "limited_dimensions": limited_dimensions or [],
    }


def build_trust_interpretation(
    *,
    trust_summary: dict[str, object],
    raw_context_summary: dict[str, object] | None = None,
    effective_context_summary: dict[str, object] | None = None,
    evidence_summary: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Build deterministic user-facing wording for compensated trust states."""
    evidence_summary = evidence_summary or {}
    effective_context_summary = effective_context_summary or {}
    raw_context_summary = raw_context_summary or {}
    evidence_total = int(evidence_summary.get("total") or 0)
    dimensions_without_evidence = list(evidence_summary.get("dimensions_without_evidence") or [])

    compensated_context = (
        trust_summary.get("overall_status") == "degraded"
        and bool(effective_context_summary.get("applied"))
        and effective_context_summary.get("status") == "degraded"
        and evidence_total > 0
    )
    if not compensated_context:
        return None

    if dimensions_without_evidence:
        dimensions_text = "Algunas dimensiones aún tienen evidencia limitada: " + ", ".join(
            str(item) for item in dimensions_without_evidence
        ) + "."
        evidence_base = "partial_with_context_limitation"
    else:
        dimensions_text = "Todas las dimensiones cuentan con alguna evidencia."
        evidence_base = "sufficient_with_context_limitation"

    primary_limitation = "homepage_pre_scan_unavailable"
    raw_reasons = raw_context_summary.get("confidence_reason") or []
    if isinstance(raw_reasons, list) and "homepage_unavailable" not in raw_reasons:
        primary_limitation = "raw_context_pre_scan_limited"

    user_message = (
        "El análisis es utilizable, pero el pre-scan técnico de contexto está degradado: "
        "la homepage no pudo analizarse directamente. La lectura se ha compensado con "
        "inventario público, menciones externas, contenido recuperado por fallback y "
        "evidencias visuales/LLM. "
        f"{dimensions_text} "
        "Mantén esta limitación visible al interpretar conclusiones de contexto."
    )

    return {
        "audit_usable": True,
        "primary_limitation": primary_limitation,
        "compensated_by_public_inventory": True,
        "evidence_base": evidence_base,
        "limitations_visible": True,
        "raw_context_status": raw_context_summary.get("status"),
        "effective_context_status": effective_context_summary.get("status"),
        "user_message": user_message,
    }


def trust_overall_status(
    *,
    data_quality: str,
    context_status: str | None,
    dimension_status_counts: dict[str, int],
) -> str:
    if data_quality == "insufficient" or context_status == "insufficient_data":
        return "insufficient_data"
    if dimension_status_counts.get("insufficient_data", 0) >= 3:
        return "insufficient_data"
    if (
        data_quality == "degraded"
        or context_status == "degraded"
        or dimension_status_counts.get("degraded", 0) > 0
        or dimension_status_counts.get("insufficient_data", 0) > 0
    ):
        return "degraded"
    return "good"


def trust_overall_reason(
    *,
    data_quality: str,
    context_status: str | None,
    dimension_status_counts: dict[str, int],
    locale: str = "code",
) -> str:
    code = _trust_overall_reason_code(
        data_quality=data_quality,
        context_status=context_status,
        dimension_status_counts=dimension_status_counts,
    )
    if locale == "es":
        return _REASON_LABELS_ES.get(code, code)
    return code


def trust_status_label(status: str, locale: str = "es") -> str:
    if locale == "es":
        return _STATUS_LABELS_ES.get(status, status)
    return status


def _trust_overall_reason_code(
    *,
    data_quality: str,
    context_status: str | None,
    dimension_status_counts: dict[str, int],
) -> str:
    if data_quality == "insufficient":
        return "data_quality_insufficient"
    if context_status == "insufficient_data":
        return "context_insufficient"
    if dimension_status_counts.get("insufficient_data", 0) >= 3:
        return "multiple_dimensions_insufficient"
    if data_quality == "degraded":
        return "data_quality_degraded"
    if context_status == "degraded":
        return "context_degraded"
    if dimension_status_counts.get("degraded", 0) > 0:
        return "dimension_degraded"
    if dimension_status_counts.get("insufficient_data", 0) > 0:
        return "some_dimensions_insufficient"
    return "all_trust_checks_passed"


def _empty_counts() -> dict[str, int]:
    return {"good": 0, "degraded": 0, "insufficient_data": 0}


_REASON_LABELS_ES = {
    "data_quality_insufficient": "calidad de datos insuficiente",
    "context_insufficient": "pre-scan contextual insuficiente",
    "multiple_dimensions_insufficient": "multiples dimensiones con datos insuficientes",
    "data_quality_degraded": "calidad de datos degradada",
    "context_degraded": "pre-scan contextual degradado",
    "dimension_degraded": "alguna dimension degradada",
    "some_dimensions_insufficient": "alguna dimension con datos insuficientes",
    "all_trust_checks_passed": "todas las comprobaciones de confianza pasaron",
}

_STATUS_LABELS_ES = {
    "good": "bueno",
    "degraded": "degradado",
    "insufficient_data": "datos insuficientes",
}
