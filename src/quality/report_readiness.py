"""Report readiness evaluator.

This module is intentionally read-only with respect to Brand3 scoring. It does
not change scores, weights, collectors, prompts, storage, or rendering. It only
classifies whether existing analysis material is fit for an editorial report.
"""

from __future__ import annotations

import ast
import copy
import json
from typing import Any

from src.dimensions import DIMENSIONS

REPORT_MODE_PUBLISHABLE = "publishable_brand_report"
REPORT_MODE_TECHNICAL = "technical_diagnostic"
REPORT_MODE_INSUFFICIENT = "insufficient_evidence"

DIMENSION_READY = "ready"
DIMENSION_OBSERVATION_ONLY = "observation_only"
DIMENSION_TECHNICAL_ONLY = "technical_only"
DIMENSION_NOT_EVALUABLE = "not_evaluable"

CORE_DIMENSIONS = ("coherencia", "diferenciacion", "presencia")
HIGH_WEIGHT_FEATURE_THRESHOLD = 0.25


def evaluate_report_readiness(
    *,
    scores: dict[str, Any] | None = None,
    evidence_summary: dict[str, Any] | None = None,
    confidence_summary: dict[str, dict[str, Any]] | None = None,
    features_by_dimension: dict[str, Any] | None = None,
    narrative_summary: dict[str, Any] | None = None,
    core_dimensions: tuple[str, ...] = CORE_DIMENSIONS,
) -> dict[str, Any]:
    """Classify whether a run is ready for an editorial brand report.

    Inputs are deliberately plain dictionaries so the evaluator can run over a
    report context, a database snapshot, or test fixtures without importing the
    service layer.
    """

    scores_input = copy.deepcopy(scores or {})
    evidence_input = copy.deepcopy(evidence_summary or {})
    confidence_input = copy.deepcopy(confidence_summary or {})
    features_input = copy.deepcopy(features_by_dimension or {})
    narrative_input = copy.deepcopy(narrative_summary or {})

    warnings: list[str] = []
    if not _has_entity_relevance_signal(evidence_input):
        warnings.append(
            "entity_relevance_not_available: direct evidence may only mean URL presence"
        )

    fallback_by_dim = _fallback_detected_by_dimension(
        scores_input,
        confidence_input,
        features_input,
        evidence_input,
    )
    missing_high_weight = _missing_high_weight_features(
        confidence_input,
        features_input,
    )

    dimension_states: dict[str, str] = {}
    reasons: dict[str, list[str]] = {}
    blockers: list[str] = []

    for dimension_name in DIMENSIONS:
        state, dimension_reasons = _dimension_state(
            dimension_name,
            scores=scores_input,
            evidence_summary=evidence_input,
            confidence_summary=confidence_input,
            missing_high_weight_features=missing_high_weight,
            fallback_detected=fallback_by_dim,
            narrative_summary=narrative_input,
        )
        dimension_states[dimension_name] = state
        reasons[dimension_name] = dimension_reasons

    core_not_evaluable = [
        dim
        for dim in core_dimensions
        if dimension_states.get(dim) == DIMENSION_NOT_EVALUABLE
    ]
    core_technical_only = [
        dim
        for dim in core_dimensions
        if dimension_states.get(dim) == DIMENSION_TECHNICAL_ONLY
    ]
    core_ready = [
        dim
        for dim in core_dimensions
        if dimension_states.get(dim) == DIMENSION_READY
    ]
    core_below_observation = [
        dim
        for dim in core_dimensions
        if dimension_states.get(dim) not in (DIMENSION_READY, DIMENSION_OBSERVATION_ONLY)
    ]
    unsupported_editorial = _unsupported_editorial_synthesis(narrative_input)

    if len(core_not_evaluable) >= 2:
        report_mode = REPORT_MODE_INSUFFICIENT
        blockers.append("multiple_core_dimensions_not_evaluable")
    elif unsupported_editorial:
        report_mode = REPORT_MODE_TECHNICAL
        blockers.append("unsupported_editorial_synthesis")
    elif core_technical_only:
        report_mode = REPORT_MODE_TECHNICAL
        blockers.append("core_dimensions_technical_only")
    elif core_not_evaluable:
        report_mode = REPORT_MODE_TECHNICAL
        blockers.append("core_dimensions_not_evaluable")
    elif core_below_observation:
        report_mode = REPORT_MODE_TECHNICAL
        blockers.append("core_dimensions_below_observation_only")
    elif len(core_ready) < 2:
        report_mode = REPORT_MODE_TECHNICAL
        blockers.append("insufficient_ready_core_dimensions")
    else:
        report_mode = REPORT_MODE_PUBLISHABLE

    return {
        "report_mode": report_mode,
        "dimension_states": dimension_states,
        "reasons": reasons,
        "blockers": blockers,
        "warnings": warnings,
        "fallback_detected": {
            dim: detected for dim, detected in fallback_by_dim.items() if detected
        },
        "missing_high_weight_features": {
            dim: features for dim, features in missing_high_weight.items() if features
        },
        "evidence_summary_used": evidence_input,
        "confidence_summary_used": confidence_input,
    }


def _dimension_state(
    dimension_name: str,
    *,
    scores: dict[str, Any],
    evidence_summary: dict[str, Any],
    confidence_summary: dict[str, dict[str, Any]],
    missing_high_weight_features: dict[str, list[str]],
    fallback_detected: dict[str, bool],
    narrative_summary: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    score = _dimension_score(scores, dimension_name)
    evidence_count = _dimension_evidence_count(evidence_summary, dimension_name)
    confidence = confidence_summary.get(dimension_name) or {}
    confidence_status = confidence.get("status")
    confidence_value = _as_float(confidence.get("confidence"))
    narrative_state = _dimension_narrative_state(narrative_summary, dimension_name)

    if score is None:
        reasons.append("score_missing")
    if evidence_count <= 0:
        reasons.append("no_dimension_evidence")
    if confidence_status == "insufficient_data":
        reasons.append("confidence_insufficient_data")
    if fallback_detected.get(dimension_name):
        reasons.append("fallback_value_detected")
    if missing_high_weight_features.get(dimension_name):
        reasons.append("missing_high_weight_features")
    if narrative_state in ("fallback", "unsupported"):
        reasons.append(f"narrative_{narrative_state}")

    if score is None or evidence_count <= 0 or confidence_status == "insufficient_data":
        return DIMENSION_NOT_EVALUABLE, reasons

    if fallback_detected.get(dimension_name) or missing_high_weight_features.get(dimension_name):
        return DIMENSION_TECHNICAL_ONLY, reasons

    if narrative_state in ("fallback", "unsupported"):
        return DIMENSION_TECHNICAL_ONLY, reasons

    if confidence_status == "degraded" or 0 < confidence_value < 0.6:
        reasons.append("confidence_below_editorial_threshold")
        return DIMENSION_OBSERVATION_ONLY, reasons

    return DIMENSION_READY, reasons


def _dimension_score(scores: dict[str, Any], dimension_name: str) -> float | None:
    if dimension_name not in scores:
        return None
    value = scores.get(dimension_name)
    if isinstance(value, dict):
        value = value.get("score")
    return _optional_float(value)


def _dimension_evidence_count(evidence_summary: dict[str, Any], dimension_name: str) -> int:
    by_dimension = evidence_summary.get("by_dimension") or {}
    try:
        return int(by_dimension.get(dimension_name) or 0)
    except (TypeError, ValueError):
        return 0


def _fallback_detected_by_dimension(
    scores: dict[str, Any],
    confidence_summary: dict[str, dict[str, Any]],
    features_by_dimension: dict[str, Any],
    evidence_summary: dict[str, Any],
) -> dict[str, bool]:
    detected: dict[str, bool] = {}
    for dimension_name in DIMENSIONS:
        feature_records = _feature_records(features_by_dimension, dimension_name)
        feature_fallback = any(_feature_record_looks_fallback(record) for record in feature_records)
        score = _dimension_score(scores, dimension_name)
        no_evidence = _dimension_evidence_count(evidence_summary, dimension_name) <= 0
        confidence = confidence_summary.get(dimension_name) or {}
        confidence_reasons = confidence.get("confidence_reason") or []
        neutral_without_support = (
            score == 50.0
            and (
                no_evidence
                or confidence.get("status") == "insufficient_data"
                or "no_evidence" in confidence_reasons
                or "low_coverage" in confidence_reasons
            )
        )
        detected[dimension_name] = feature_fallback or neutral_without_support
    return detected


def _feature_record_looks_fallback(record: dict[str, Any]) -> bool:
    value = _optional_float(record.get("value"))
    source = str(record.get("source") or "").lower()
    raw = _parse_raw(record.get("raw_value"))

    if source in {"fallback", "none", "unknown"} and value == 50.0:
        return True
    if isinstance(raw, dict):
        raw_flags = {
            str(key).lower(): value
            for key, value in raw.items()
            if key is not None
        }
        if any(
            bool(raw_flags.get(key))
            for key in (
                "fallback",
                "fallback_used",
                "default_score",
                "no_data",
                "insufficient_data",
                "unavailable",
            )
        ):
            return True
        reason_text = " ".join(
            str(raw_flags.get(key) or "")
            for key in ("reason", "status", "note")
        ).lower()
        if value == 50.0 and any(marker in reason_text for marker in ("fallback", "no data", "insufficient")):
            return True
    return False


def _missing_high_weight_features(
    confidence_summary: dict[str, dict[str, Any]],
    features_by_dimension: dict[str, Any],
) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for dimension_name, config in DIMENSIONS.items():
        high_weight_features = {
            name
            for name, feature in (config.get("features") or {}).items()
            if _as_float(feature.get("weight")) >= HIGH_WEIGHT_FEATURE_THRESHOLD
        }
        missing_names = set()

        confidence_missing = (
            (confidence_summary.get(dimension_name) or {}).get("missing_signals")
            or []
        )
        missing_names.update(name for name in confidence_missing if name in high_weight_features)

        if dimension_name in features_by_dimension:
            present = {
                record.get("feature_name")
                for record in _feature_records(features_by_dimension, dimension_name)
            }
            missing_names.update(high_weight_features - present)

        missing[dimension_name] = sorted(missing_names)
    return missing


def _feature_records(features_by_dimension: dict[str, Any], dimension_name: str) -> list[dict[str, Any]]:
    raw = features_by_dimension.get(dimension_name)
    if raw is None:
        return []
    if isinstance(raw, dict):
        records = []
        for feature_name, value in raw.items():
            if isinstance(value, dict):
                record = dict(value)
                record.setdefault("feature_name", feature_name)
            else:
                record = {"feature_name": feature_name, "value": value}
            records.append(record)
        return records
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    return []


def _dimension_narrative_state(narrative_summary: dict[str, Any], dimension_name: str) -> str | None:
    by_dimension = narrative_summary.get("dimension_states") or {}
    if dimension_name in by_dimension:
        state = by_dimension.get(dimension_name)
        if isinstance(state, dict):
            return state.get("state")
        if isinstance(state, str):
            return state
    fallback_dimensions = set(narrative_summary.get("fallback_dimensions") or [])
    unsupported_dimensions = set(narrative_summary.get("unsupported_dimensions") or [])
    if dimension_name in unsupported_dimensions:
        return "unsupported"
    if dimension_name in fallback_dimensions:
        return "fallback"
    return None


def _unsupported_editorial_synthesis(narrative_summary: dict[str, Any]) -> bool:
    if bool(narrative_summary.get("unsupported_editorial_synthesis")):
        return True
    if str(narrative_summary.get("synthesis_state") or "").lower() == "unsupported":
        return True
    return False


def _has_entity_relevance_signal(evidence_summary: dict[str, Any]) -> bool:
    if "entity_relevance_available" in evidence_summary:
        return bool(evidence_summary.get("entity_relevance_available"))
    if "by_relevance" in evidence_summary:
        return True
    if "off_entity" in (evidence_summary.get("by_quality") or {}):
        return True
    return False


def _parse_raw(raw_value: Any) -> Any:
    if isinstance(raw_value, (dict, list)):
        return raw_value
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    try:
        return json.loads(raw_value)
    except Exception:
        pass
    try:
        return ast.literal_eval(raw_value)
    except Exception:
        return raw_value


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float:
    parsed = _optional_float(value)
    return parsed if parsed is not None else 0.0
