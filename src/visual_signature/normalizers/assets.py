"""Normalize observable asset behavior."""

from __future__ import annotations

import re

from src.visual_signature.types import NormalizedAssetSignals, VisualAcquisitionResult, VisualAssetCandidate


def normalize_asset_signals(acquisition: VisualAcquisitionResult) -> NormalizedAssetSignals:
    html = "\n".join([acquisition.rendered_html or "", acquisition.raw_html or ""])
    images = acquisition.images
    logo_candidates = [item for item in images if item.role_hint == "logo" or "logo" in _text_for(item)]
    icon_candidates = [item for item in images if item.role_hint == "icon" or "icon" in _text_for(item)]
    svg_count = _count(r"<svg\b|\.svg\b", html)
    video_count = _count(r"<video\b|youtube\.com|vimeo\.com|\.mp4\b", html)
    background_count = _count(r"background(?:-image)?\s*:\s*url\(", html)
    mix: list[str] = []
    if logo_candidates:
        mix.append("logo")
    if icon_candidates or svg_count:
        mix.append("icon")
    if any("illustration" in _text_for(item) or "graphic" in _text_for(item) for item in images):
        mix.append("illustration")
    if any(item.role_hint == "photo" or re.search(r"\.(?:jpg|jpeg|webp|png)(?:\?|$)", item.url, re.I) for item in images):
        mix.append("photo")
    if video_count:
        mix.append("video")
    if acquisition.screenshot and acquisition.screenshot.url:
        mix.append("screenshot")
    mix = _unique(mix) or ["unknown"]
    return NormalizedAssetSignals(
        image_count=len(images),
        svg_count=svg_count,
        video_count=video_count,
        background_image_count=background_count,
        logo_image_candidates=logo_candidates[:8],
        icon_candidates=icon_candidates[:12],
        screenshot_available=bool(acquisition.screenshot and acquisition.screenshot.url),
        asset_mix=mix,
        confidence=_clamp(
            (0.25 if images else 0)
            + (0.1 if svg_count else 0)
            + (0.25 if acquisition.screenshot and acquisition.screenshot.url else 0)
            + (0.2 if html.strip() else 0)
            + min(0.15, len(mix) * 0.04)
        ),
    )


def _text_for(item: VisualAssetCandidate) -> str:
    return f"{item.url} {item.alt or ''}".lower()


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _count(pattern: str, value: str) -> int:
    return len(re.findall(pattern, value or "", flags=re.I))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
