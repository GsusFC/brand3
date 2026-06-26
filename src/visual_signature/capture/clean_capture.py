"""Shared clean-capture decision helpers for Visual Diagnosis Lab.

This module is lab-only. It evaluates whether a safe mutation attempt produced
cleaner visual evidence, without mutating screenshots or changing scoring.
"""

from __future__ import annotations

from typing import Any

from src.visual_signature.capture.clean_capture_support import clean_capture_improvement_state as _clean_capture_improvement_state_impl
from src.visual_signature.capture.clean_capture_support import clean_capture_metrics_delta as _clean_capture_metrics_delta_impl
from src.visual_signature.capture.clean_capture_support import clean_capture_obstruction_delta as _clean_capture_obstruction_delta_impl
from src.visual_signature.capture.clean_capture_support import severity_rank as _severity_rank_impl
from src.visual_signature.versions import VISUAL_DIAGNOSIS_CLEAN_CAPTURE_DECISION_SCHEMA_VERSION


def build_clean_capture_decision(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    raw_path = str(payload.get("raw_screenshot_path") or payload.get("screenshot_path") or "").strip()
    clean_path = str(payload.get("clean_attempt_screenshot_path") or "").strip()
    if not raw_path and not clean_path:
        return {}

    attempted = payload.get("dismissal_attempted") is True
    successful = payload.get("dismissal_successful") is True
    before = payload.get("before_obstruction") if isinstance(payload.get("before_obstruction"), dict) else {}
    after = payload.get("after_obstruction") if isinstance(payload.get("after_obstruction"), dict) else {}
    raw_metrics = payload.get("raw_viewport_metrics") if isinstance(payload.get("raw_viewport_metrics"), dict) else {}
    clean_metrics = payload.get("clean_attempt_metrics") if isinstance(payload.get("clean_attempt_metrics"), dict) else {}
    metrics_delta = clean_capture_metrics_delta(raw_metrics, clean_metrics)
    obstruction_delta = clean_capture_obstruction_delta(before, after)

    selected_variant = "raw_viewport"
    decision = "raw_only"
    reason = "no_clean_attempt_available"
    use_clean_for_diagnosis = False
    improvement_state = "not_evaluated"

    if clean_path and attempted:
        improvement_state = clean_capture_improvement_state(
            successful=successful,
            obstruction_delta=obstruction_delta,
            metrics_delta=metrics_delta,
        )
        if improvement_state == "clear_improvement":
            decision = "use_clean_attempt"
            reason = "dismissal_successful_or_obstruction_reduced"
            selected_variant = "clean_attempt"
            use_clean_for_diagnosis = True
        elif improvement_state == "partial_improvement":
            decision = "keep_raw_with_clean_supplement"
            reason = "clean_attempt_improved_some_metrics_but_not_enough"
        elif improvement_state == "degraded":
            decision = "keep_raw_clean_degraded"
            reason = "clean_attempt_degraded_first_impression"
        else:
            decision = "keep_raw_no_material_improvement"
            reason = "clean_attempt_did_not_materially_reduce_obstruction"
    elif attempted:
        decision = "keep_raw_no_clean_artifact"
        reason = "dismissal_attempted_without_clean_artifact"
    elif payload.get("dismissal_block_reason"):
        decision = "raw_only"
        reason = str(payload.get("dismissal_block_reason"))

    return {
        "schema_version": VISUAL_DIAGNOSIS_CLEAN_CAPTURE_DECISION_SCHEMA_VERSION,
        "selected_variant": selected_variant,
        "decision": decision,
        "reason": reason,
        "use_clean_for_diagnosis": use_clean_for_diagnosis,
        "improvement_state": improvement_state,
        "clean_attempt_quality": improvement_state,
        "raw_screenshot_path": raw_path or None,
        "clean_attempt_screenshot_path": clean_path or None,
        "dismissal_attempted": attempted,
        "dismissal_successful": successful,
        "obstruction_delta": obstruction_delta,
        "metrics_delta": metrics_delta,
    }


def clean_attempt_quality(payload: dict[str, Any] | None) -> str:
    decision = build_clean_capture_decision(payload)
    if not decision:
        return "not_available"
    if not decision.get("clean_attempt_screenshot_path"):
        return "not_available"
    return str(decision.get("clean_attempt_quality") or "not_evaluated")


def clean_capture_improvement_state(
    *,
    successful: bool,
    obstruction_delta: dict[str, Any],
    metrics_delta: dict[str, Any],
) -> str:
    return _clean_capture_improvement_state_impl(
        successful=successful,
        obstruction_delta=obstruction_delta,
        metrics_delta=metrics_delta,
    )


def clean_capture_obstruction_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return _clean_capture_obstruction_delta_impl(before, after)


def clean_capture_metrics_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return _clean_capture_metrics_delta_impl(before, after)


def _severity_rank(value: str) -> int:
    return _severity_rank_impl(value)
