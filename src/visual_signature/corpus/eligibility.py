"""Evidence-only eligibility gates for the Visual Signature calibration corpus."""

from __future__ import annotations

from typing import Any


def baseline_eligibility(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return baseline eligibility for a Visual Signature evidence payload.

    This utility is diagnostic only. It does not affect Brand3 scoring,
    rubric dimensions, reports, or UI.
    """
    if not isinstance(payload, dict):
        return _result(False, ["payload_missing"])

    failures: list[str] = []
    warnings: list[str] = []
    if payload.get("interpretation_status") != "interpretable":
        failures.append("interpretation_status_not_interpretable")

    acquisition = payload.get("acquisition") if isinstance(payload.get("acquisition"), dict) else {}
    if acquisition.get("errors"):
        failures.append("acquisition_errors_present")

    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision.get("screenshot"), dict) else {}
    if not screenshot.get("available"):
        failures.append("viewport_screenshot_missing")
    if screenshot.get("quality") in {"missing", "unreadable", "blank"}:
        failures.append("viewport_screenshot_quality_unusable")
    if screenshot.get("capture_type") not in {"viewport", "full_page"}:
        warnings.append("capture_type_unknown")

    viewport_composition = (
        vision.get("viewport_composition")
        if isinstance(vision.get("viewport_composition"), dict)
        else {}
    )
    if not viewport_composition:
        failures.append("viewport_composition_missing")

    viewport_palette = (
        vision.get("viewport_palette")
        if isinstance(vision.get("viewport_palette"), dict)
        else {}
    )
    if not viewport_palette:
        failures.append("viewport_palette_missing")

    viewport_confidence = (
        vision.get("viewport_confidence")
        if isinstance(vision.get("viewport_confidence"), dict)
        else {}
    )
    if _float_or_none(viewport_confidence.get("score")) is None:
        failures.append("viewport_confidence_missing")

    agreement = vision.get("agreement") if isinstance(vision.get("agreement"), dict) else {}
    if not agreement.get("agreement_level"):
        failures.append("agreement_layer_missing")

    obstruction = vision.get("viewport_obstruction") if isinstance(vision.get("viewport_obstruction"), dict) else {}
    if obstruction.get("first_impression_valid") is False:
        failures.append("viewport_first_impression_obstructed")
    elif obstruction.get("present"):
        warnings.append("viewport_obstruction_present_but_first_impression_valid")

    coverage = _signal_coverage(payload)
    if coverage < 0.7:
        failures.append("signal_coverage_below_threshold")

    dimensions = _dimensions(screenshot)
    if dimensions["viewport_width"] is not None and dimensions["viewport_width"] < 1200:
        failures.append("viewport_width_below_minimum")
    if dimensions["viewport_height"] is not None and dimensions["viewport_height"] < 750:
        failures.append("viewport_height_below_minimum")

    return _result(not failures, failures, warnings=warnings, signal_coverage=coverage, **dimensions)


def _result(
    eligible: bool,
    failures: list[str],
    *,
    warnings: list[str] | None = None,
    signal_coverage: float | None = None,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
) -> dict[str, Any]:
    return {
        "baseline_eligible": eligible,
        "failures": failures,
        "warnings": warnings or [],
        "signal_coverage": signal_coverage,
        "minimums": {
            "signal_coverage": 0.7,
            "viewport_width": 1200,
            "viewport_height": 750,
        },
        "observed": {
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
        },
    }


def _dimensions(screenshot: dict[str, Any]) -> dict[str, int | None]:
    width = _int_or_none(screenshot.get("viewport_width") or screenshot.get("width"))
    height = _int_or_none(screenshot.get("viewport_height") or screenshot.get("height"))
    return {"viewport_width": width, "viewport_height": height}


def _signal_coverage(payload: dict[str, Any]) -> float:
    keys = ("colors", "typography", "logo", "layout", "components", "assets", "consistency")
    covered = 0
    for key in keys:
        value = payload.get(key)
        if not isinstance(value, dict):
            continue
        confidence = _float_or_none(value.get("confidence"))
        if confidence is not None and confidence > 0:
            covered += 1
            continue
        if any(item not in (None, "", [], {}, "unknown", ["unknown"]) for item in value.values()):
            covered += 1
    return round(covered / len(keys), 3)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
