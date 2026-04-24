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
