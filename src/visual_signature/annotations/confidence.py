"""Confidence normalization for Visual Signature annotations."""

from __future__ import annotations

from typing import Any

from src.visual_signature.annotations.types import (
    ANNOTATION_TARGETS,
    AnnotationConfidence,
    AnnotationStatus,
    AnnotationTarget,
)


def normalize_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, min(1.0, number)), 3)


def confidence_level(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def calculate_annotation_confidence(
    *,
    status: AnnotationStatus,
    targets: dict[str, AnnotationTarget],
    visual_signature_payload: dict[str, Any],
) -> AnnotationConfidence:
    limitations: list[str] = []
    screenshot_factor = _screenshot_factor(visual_signature_payload)
    completeness = len(targets) / len(ANNOTATION_TARGETS)
    target_scores = [target.confidence for target in targets.values()]
    model_certainty = sum(target_scores) / len(target_scores) if target_scores else 0.0
    evidence_specificity = _evidence_specificity(targets)
    if status == "not_interpretable":
        limitations.append("annotation_not_interpretable")
    if completeness < 1:
        limitations.append("annotation_targets_incomplete")
    score = (
        screenshot_factor * 0.25
        + completeness * 0.25
        + model_certainty * 0.35
        + evidence_specificity * 0.15
    )
    if status == "failed":
        score = 0.0
        limitations.append("annotation_provider_failed")
    elif status == "not_interpretable":
        score = min(score, 0.2)
    return AnnotationConfidence(
        score=round(score, 3),
        level=confidence_level(score),  # type: ignore[arg-type]
        factors={
            "screenshot_quality": round(screenshot_factor, 3),
            "target_completeness": round(completeness, 3),
            "model_certainty": round(model_certainty, 3),
            "evidence_specificity": round(evidence_specificity, 3),
        },
        limitations=limitations,
    )


def _screenshot_factor(payload: dict[str, Any]) -> float:
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision.get("screenshot"), dict) else {}
    if not screenshot.get("available"):
        return 0.0
    quality = str(screenshot.get("quality") or "unknown")
    return {
        "usable": 1.0,
        "low_detail": 0.55,
        "blank": 0.1,
        "unreadable": 0.0,
        "missing": 0.0,
    }.get(quality, 0.5)


def _evidence_specificity(targets: dict[str, AnnotationTarget]) -> float:
    if not targets:
        return 0.0
    usable = 0
    for target in targets.values():
        if target.evidence and target.source not in {"unknown", ""}:
            usable += 1
    return usable / len(targets)
