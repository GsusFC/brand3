"""Extraction confidence scoring for Visual Signature."""

from __future__ import annotations

from src.visual_signature.types import (
    ExtractionConfidence,
    NormalizedAssetSignals,
    NormalizedColorSignals,
    NormalizedComponentSignals,
    NormalizedConsistencySignals,
    NormalizedLayoutSignals,
    NormalizedLogoSignals,
    NormalizedTypographySignals,
    VisualAcquisitionResult,
)


def calculate_extraction_confidence(
    *,
    acquisition: VisualAcquisitionResult,
    colors: NormalizedColorSignals,
    typography: NormalizedTypographySignals,
    logo: NormalizedLogoSignals,
    layout: NormalizedLayoutSignals,
    components: NormalizedComponentSignals,
    assets: NormalizedAssetSignals,
    consistency: NormalizedConsistencySignals,
) -> ExtractionConfidence:
    acquisition_score = _score_acquisition(acquisition)
    html_coverage = _score_html_coverage(acquisition)
    signal_coverage = _average([
        colors.confidence,
        typography.confidence,
        logo.confidence,
        layout.confidence,
        components.confidence,
        assets.confidence,
    ])
    consistency_coverage = consistency.confidence
    score = _round(
        acquisition_score * 0.25
        + html_coverage * 0.25
        + signal_coverage * 0.35
        + consistency_coverage * 0.15
    )
    return ExtractionConfidence(
        score=score,
        level="high" if score >= 0.75 else "medium" if score >= 0.45 else "low",
        factors={
            "acquisition": acquisition_score,
            "html_coverage": html_coverage,
            "signal_coverage": signal_coverage,
            "consistency_coverage": consistency_coverage,
        },
        limitations=_limitations_for(
            acquisition,
            html_coverage=html_coverage,
            signal_coverage=signal_coverage,
            consistency_coverage=consistency_coverage,
        ),
    )


def _score_acquisition(acquisition: VisualAcquisitionResult) -> float:
    if acquisition.errors:
        return 0.1
    status = acquisition.status_code or 0
    if 200 <= status < 300:
        return 0.9
    if 300 <= status < 400:
        return 0.75
    if acquisition.rendered_html or acquisition.raw_html or acquisition.markdown:
        return 0.65
    return 0.45


def _score_html_coverage(acquisition: VisualAcquisitionResult) -> float:
    total = (
        len(acquisition.rendered_html or "")
        + len(acquisition.raw_html or "") * 0.7
        + len(acquisition.markdown or "") * 0.35
    )
    if total > 20_000:
        return 0.9
    if total > 5_000:
        return 0.72
    if total > 1_000:
        return 0.5
    if total > 0:
        return 0.25
    return 0.0


def _limitations_for(
    acquisition: VisualAcquisitionResult,
    *,
    html_coverage: float,
    signal_coverage: float,
    consistency_coverage: float,
) -> list[str]:
    limitations = []
    if acquisition.errors:
        limitations.append("acquisition_errors_present")
    if not acquisition.screenshot or not acquisition.screenshot.url:
        limitations.append("screenshot_not_available")
    if html_coverage < 0.5:
        limitations.append("html_coverage_limited")
    if signal_coverage < 0.45:
        limitations.append("visual_signal_coverage_limited")
    if consistency_coverage < 0.45:
        limitations.append("consistency_inference_limited")
    return limitations


def _average(values: list[float]) -> float:
    return _round(sum(values) / len(values)) if values else 0.0


def _round(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
