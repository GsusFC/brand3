"""Vision enrichment confidence scoring."""

from __future__ import annotations

from src.visual_signature.vision.types import (
    VisionCompositionEvidence,
    VisionConfidence,
    VisionPaletteEvidence,
    VisionScreenshotEvidence,
)


def calculate_vision_confidence(
    *,
    screenshot: VisionScreenshotEvidence,
    palette: VisionPaletteEvidence,
    composition: VisionCompositionEvidence,
) -> VisionConfidence:
    screenshot_factor = _screenshot_factor(screenshot)
    palette_factor = palette.confidence
    composition_factor = composition.confidence
    score = _clamp(screenshot_factor * 0.45 + palette_factor * 0.25 + composition_factor * 0.30)
    limitations = list(screenshot.limitations)
    if not screenshot.available:
        limitations.append("screenshot_not_available")
    if screenshot.quality in {"blank", "low_detail", "unreadable"}:
        limitations.append(f"screenshot_quality_{screenshot.quality}")
    if palette_factor < 0.45:
        limitations.append("palette_confidence_limited")
    if composition_factor < 0.45:
        limitations.append("composition_confidence_limited")
    return VisionConfidence(
        score=score,
        level="high" if score >= 0.75 else "medium" if score >= 0.45 else "low",
        factors={
            "screenshot": screenshot_factor,
            "palette": palette_factor,
            "composition": composition_factor,
        },
        limitations=_unique(limitations),
    )


def _screenshot_factor(screenshot: VisionScreenshotEvidence) -> float:
    if not screenshot.available:
        return 0.0
    if screenshot.quality == "usable":
        return 0.9
    if screenshot.quality == "low_detail":
        return 0.45
    if screenshot.quality == "blank":
        return 0.18
    return 0.1


def _unique(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
