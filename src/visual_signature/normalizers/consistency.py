"""Derive consistency signals from normalized visual behavior."""

from __future__ import annotations

from src.visual_signature.types import (
    NormalizedAssetSignals,
    NormalizedColorSignals,
    NormalizedComponentSignals,
    NormalizedConsistencySignals,
    NormalizedTypographySignals,
)


def normalize_consistency_signals(
    *,
    colors: NormalizedColorSignals,
    typography: NormalizedTypographySignals,
    components: NormalizedComponentSignals,
    assets: NormalizedAssetSignals,
) -> NormalizedConsistencySignals:
    color_consistency = _score_color_consistency(colors)
    typography_consistency = _score_typography_consistency(typography)
    component_consistency = _score_component_consistency(components)
    asset_consistency = _score_asset_consistency(assets)
    notes: list[str] = []
    if colors.palette_complexity == "high":
        notes.append("High color variety detected; verify whether this is systemized or incidental.")
    if len(typography.font_families) > 5:
        notes.append("Many font families detected in rendered CSS.")
    if not assets.screenshot_available:
        notes.append("No screenshot was available from the acquisition adapter.")
    return NormalizedConsistencySignals(
        color_consistency=color_consistency,
        typography_consistency=typography_consistency,
        component_consistency=component_consistency,
        asset_consistency=asset_consistency,
        overall_consistency=_round(
            color_consistency * 0.3
            + typography_consistency * 0.25
            + component_consistency * 0.25
            + asset_consistency * 0.2
        ),
        notes=notes,
        confidence=_round(
            (colors.confidence + typography.confidence + components.confidence + assets.confidence) / 4
        ),
    )


def _score_color_consistency(colors: NormalizedColorSignals) -> float:
    if not colors.palette:
        return 0.15
    if colors.palette_complexity == "low":
        return 0.78
    if colors.palette_complexity == "medium":
        return 0.68
    return 0.48


def _score_typography_consistency(typography: NormalizedTypographySignals) -> float:
    count = len(typography.font_families)
    if not count:
        return 0.2
    if count <= 2:
        return 0.82
    if count <= 5:
        return 0.65
    return 0.42


def _score_component_consistency(components: NormalizedComponentSignals) -> float:
    if not components.components:
        return 0.25
    has_navigation = any(item.type == "navigation" for item in components.components)
    has_cta = any(item.type in {"cta", "button"} for item in components.components)
    return _round(
        0.42
        + (0.2 if has_navigation else 0)
        + (0.18 if has_cta else 0)
        + min(0.15, len(components.components) * 0.02)
    )


def _score_asset_consistency(assets: NormalizedAssetSignals) -> float:
    if not assets.image_count and not assets.svg_count:
        return 0.2
    return _round(
        0.45
        + (0.18 if assets.logo_image_candidates else 0)
        + (0.12 if assets.icon_candidates else 0)
        + (0.12 if assets.screenshot_available else 0)
    )


def _round(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
