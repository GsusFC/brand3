"""Screenshot-derived palette heuristics."""

from __future__ import annotations

from collections import Counter

from src.visual_signature.vision.types import RasterImage, VisionColor, VisionPaletteEvidence
from src.visual_signature._internal.utils import clamp_01 as _clamp


def extract_palette_from_screenshot(image: RasterImage | None, *, max_colors: int = 8) -> VisionPaletteEvidence:
    if image is None:
        return VisionPaletteEvidence(confidence=0.0)

    sampled = image.sample_pixels(20_000)
    if not sampled:
        return VisionPaletteEvidence(confidence=0.0)

    buckets = Counter(_bucket_color(pixel) for pixel in sampled)
    total = sum(buckets.values()) or 1
    dominant = [
        VisionColor(
            hex=_hex_color(color),
            occurrences=count,
            ratio=round(count / total, 4),
        )
        for color, count in buckets.most_common(max_colors)
    ]
    unique_ratio = min(1.0, len(buckets) / 64)
    confidence = _clamp(0.35 + unique_ratio * 0.35 + min(0.2, len(sampled) / 20_000 * 0.2))
    return VisionPaletteEvidence(
        dominant_colors=dominant,
        color_count=len(buckets),
        confidence=confidence,
    )


def _bucket_color(pixel: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(min(255, round(channel / 32) * 32) for channel in pixel)


def _hex_color(pixel: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*pixel)
