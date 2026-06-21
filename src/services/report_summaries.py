"""Confidence, trust, and report-readiness summary helpers."""

from __future__ import annotations

from typing import Any

from src.collectors.context_collector import ContextData
from src.config import AUDIT_ANALYST_MODEL, LLM_CHEAP_MODEL, LLM_MODEL, LLM_PREMIUM_MODEL, VISION_MODEL
from src.features.llm_analyzer import LLMAnalyzer
from src.learning.calibration import CalibrationAnalyzer
from src.quality.dimension_confidence import dimension_confidence_from_features
from src.quality.publication_readiness import attach_report_publication_decision
from src.quality.trust import (
    build_trust_interpretation,
    build_trust_summary,
    dimension_status_counts_from_confidence,
    limited_dimensions_from_confidence,
)
from src.reports.derivation import build_report_readiness_from_snapshot
from src.services.llm_policy import _audit_analyst_llm as _build_audit_analyst_llm
from src.services.llm_policy import _llm_model_roles_payload as _build_llm_model_roles_payload


def _confidence_status(context_data: ContextData | None) -> str:
    if not context_data or context_data.coverage < 0.3:
        return "insufficient_data"
    if context_data.confidence < 0.6:
        return "degraded"
    return "good"


def _context_confidence_summary(context_data: ContextData | None) -> dict[str, object]:
    if not context_data:
        return {
            "coverage": 0.0,
            "confidence": 0.0,
            "confidence_reason": ["context_scan_unavailable"],
            "status": "insufficient_data",
        }
    return {
        "coverage": context_data.coverage,
        "confidence": context_data.confidence,
        "confidence_reason": list(context_data.confidence_reason or []),
        "status": _confidence_status(context_data),
    }


def _dimension_confidence_summary(
    features_by_dim: dict[str, dict],
    *,
    evidence_items: list[dict[str, object]] | None = None,
    data_quality: str | None = None,
    context_data: ContextData | None = None,
) -> dict[str, dict[str, object]]:
    return dimension_confidence_from_features(
        features_by_dim,
        evidence_items=evidence_items,
        data_quality=data_quality,
        context_summary=_context_confidence_summary(context_data),
    )


def _trust_summary_payload(
    *,
    data_quality: str,
    context_summary: dict[str, object],
    evidence_summary: dict[str, object],
    dimension_confidence: dict[str, dict[str, object]],
    context_enrichment_summary: dict[str, object] | None = None,
    context_effective_readiness: dict[str, object] | None = None,
) -> dict[str, object]:
    dimension_status_counts = dimension_status_counts_from_confidence(dimension_confidence)
    effective_applied = bool(context_effective_readiness and context_effective_readiness.get("applied"))
    summary = build_trust_summary(
        data_quality=data_quality,
        context_summary=context_effective_readiness if effective_applied else context_summary,
        evidence_summary=evidence_summary,
        dimension_status_counts=dimension_status_counts,
        limited_dimensions=limited_dimensions_from_confidence(dimension_confidence),
    )
    if effective_applied:
        summary["context"] = context_summary
        summary["effective_context"] = context_effective_readiness
    if context_enrichment_summary and context_enrichment_summary.get("applied"):
        summary["context_enrichment"] = context_enrichment_summary
    interpretation = build_trust_interpretation(
        trust_summary=summary,
        raw_context_summary=context_summary,
        effective_context_summary=context_effective_readiness,
        evidence_summary=evidence_summary,
    )
    if interpretation:
        summary["interpretation"] = interpretation
        summary["user_facing_summary"] = interpretation["user_message"]
    return summary


def _llm_model_roles_payload() -> dict[str, str]:
    return _build_llm_model_roles_payload(
        default_model=LLM_MODEL,
        cheap_model=LLM_CHEAP_MODEL,
        premium_model=LLM_PREMIUM_MODEL,
        audit_analyst_model=AUDIT_ANALYST_MODEL,
        vision_model=VISION_MODEL,
    )


def _audit_analyst_llm(feature_llm: LLMAnalyzer | None) -> LLMAnalyzer | None:
    return _build_audit_analyst_llm(
        feature_llm,
        analyzer_cls=LLMAnalyzer,
        audit_analyst_model=AUDIT_ANALYST_MODEL,
    )


def _persist_report_readiness(
    store,
    run_id: int,
    audit: dict[str, Any],
) -> dict[str, Any] | None:
    snapshot = store.get_run_snapshot(run_id)
    if not snapshot:
        return None
    readiness = build_report_readiness_from_snapshot(snapshot)
    if not readiness:
        return None
    attach_report_publication_decision(audit, readiness)
    store.save_run_audit(run_id, audit)
    return readiness
