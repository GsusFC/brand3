"""Shared clean-capture decision helpers for Visual Diagnosis Lab.

This module is lab-only. It evaluates whether a safe mutation attempt produced
cleaner visual evidence, without mutating screenshots or changing scoring.
"""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none


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
        "schema_version": "visual-diagnosis-clean-capture-decision-1",
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
    if successful and obstruction_delta.get("after_present") is False:
        return "clear_improvement"
    if obstruction_delta.get("severity_delta", 0) < 0 or obstruction_delta.get("coverage_delta", 0.0) < -0.05:
        return "degraded"
    if metrics_delta.get("visual_density_changed") and (metrics_delta.get("whitespace_delta") or 0.0) < -0.08:
        return "degraded"
    if obstruction_delta.get("severity_delta", 0) > 0 or obstruction_delta.get("coverage_delta", 0.0) >= 0.12:
        return "clear_improvement"
    if obstruction_delta.get("coverage_delta", 0.0) >= 0.05 or (metrics_delta.get("whitespace_delta") or 0.0) >= 0.08:
        return "partial_improvement"
    return "no_material_improvement"


def clean_capture_obstruction_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_present = before.get("present") is True if before else None
    after_present = after.get("present") is True if after else None
    before_severity = str(before.get("severity") or "none") if before else "none"
    after_severity = str(after.get("severity") or "none") if after else "none"
    before_coverage = _float_or_none(before.get("coverage_ratio")) or 0.0
    after_coverage = _float_or_none(after.get("coverage_ratio")) or 0.0
    return {
        "before_present": before_present,
        "after_present": after_present,
        "before_type": before.get("type") if before else None,
        "after_type": after.get("type") if after else None,
        "before_severity": before_severity,
        "after_severity": after_severity,
        "severity_delta": _severity_rank(before_severity) - _severity_rank(after_severity),
        "before_coverage_ratio": before_coverage,
        "after_coverage_ratio": after_coverage,
        "coverage_delta": round(before_coverage - after_coverage, 3),
    }


def clean_capture_metrics_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_whitespace = _float_or_none(before.get("viewport_whitespace_ratio"))
    after_whitespace = _float_or_none(after.get("viewport_whitespace_ratio"))
    before_palette = _float_or_none(before.get("palette_color_count"))
    after_palette = _float_or_none(after.get("palette_color_count"))
    whitespace_delta = None
    palette_delta = None
    if before_whitespace is not None and after_whitespace is not None:
        whitespace_delta = round(after_whitespace - before_whitespace, 3)
    if before_palette is not None and after_palette is not None:
        palette_delta = round(after_palette - before_palette, 3)
    return {
        "before_visual_density": before.get("viewport_visual_density"),
        "after_visual_density": after.get("viewport_visual_density"),
        "visual_density_changed": bool(before and after and before.get("viewport_visual_density") != after.get("viewport_visual_density")),
        "before_composition": before.get("viewport_composition"),
        "after_composition": after.get("viewport_composition"),
        "composition_changed": bool(before and after and before.get("viewport_composition") != after.get("viewport_composition")),
        "whitespace_delta": whitespace_delta,
        "palette_color_count_delta": palette_delta,
    }


def _severity_rank(value: str) -> int:
    order = {"none": 0, "minor": 1, "moderate": 2, "major": 3, "blocking": 4}
    return order.get(str(value or "none").lower(), 0)
