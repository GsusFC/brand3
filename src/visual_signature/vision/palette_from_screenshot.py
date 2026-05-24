"""Screenshot-derived palette heuristics."""

from __future__ import annotations

from collections import Counter

from src.visual_signature.vision.types import RasterImage, VisionColor, VisionPaletteEvidence


def extract_palette_from_screenshot(image: RasterImage | None, *, max_colors: int = 8) -> VisionPaletteEvidence:
    if image is None or not image.pixels:
        return VisionPaletteEvidence(confidence=0.0)

    sampled = _sample_pixels(image.pixels, limit=20_000)
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


def _sample_pixels(pixels: list[tuple[int, int, int]], *, limit: int) -> list[tuple[int, int, int]]:
    if len(pixels) <= limit:
        return pixels
    step = max(1, len(pixels) // limit)
    return pixels[::step][:limit]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
