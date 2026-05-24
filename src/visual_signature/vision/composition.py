"""Local screenshot composition heuristics."""

from __future__ import annotations

from src.visual_signature.vision.types import RasterImage, VisionCompositionEvidence


def analyze_composition(image: RasterImage | None) -> VisionCompositionEvidence:
    if image is None or not image.pixels:
        return VisionCompositionEvidence(confidence=0.0)

    sampled = _sample_grid(image, max_width=180, max_height=120)
    whitespace_ratio = _whitespace_ratio(sampled)
    edge_density = _edge_density(sampled)
    color_variance = _color_variance(sampled)
    visual_density = _classify_density(whitespace_ratio, edge_density, color_variance)
    composition = _classify_composition(whitespace_ratio, edge_density, visual_density)
    confidence = _clamp(0.35 + min(0.25, len(sampled) / 12_000 * 0.25) + min(0.25, color_variance * 0.6))
    return VisionCompositionEvidence(
        whitespace_ratio=round(whitespace_ratio, 3),
        visual_density=visual_density,
        composition_classification=composition,
        edge_density=round(edge_density, 3),
        color_variance=round(color_variance, 3),
        confidence=confidence,
    )


def _sample_grid(image: RasterImage, *, max_width: int, max_height: int) -> list[tuple[int, int, int]]:
    x_step = max(1, image.width // max_width)
    y_step = max(1, image.height // max_height)
    sampled = []
    for y in range(0, image.height, y_step):
        row_offset = y * image.width
        for x in range(0, image.width, x_step):
            sampled.append(image.pixels[row_offset + x])
    return sampled


def _whitespace_ratio(pixels: list[tuple[int, int, int]]) -> float:
    if not pixels:
        return 0.0
    whitespace = sum(1 for pixel in pixels if _is_whitespace(pixel))
    return whitespace / len(pixels)


def _edge_density(pixels: list[tuple[int, int, int]]) -> float:
    if len(pixels) < 2:
        return 0.0
    changes = 0
    comparisons = 0
    previous = pixels[0]
    for pixel in pixels[1:]:
        comparisons += 1
        if _distance(previous, pixel) > 55:
            changes += 1
        previous = pixel
    return changes / comparisons if comparisons else 0.0


def _color_variance(pixels: list[tuple[int, int, int]]) -> float:
    if not pixels:
        return 0.0
    means = [sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3)]
    variance = 0.0
    for pixel in pixels:
        variance += sum((pixel[channel] - means[channel]) ** 2 for channel in range(3)) / 3
    variance /= len(pixels)
    return min(1.0, variance / (255 ** 2 / 4))


def _classify_density(whitespace_ratio: float, edge_density: float, color_variance: float) -> str:
    if whitespace_ratio >= 0.78 and edge_density < 0.08:
        return "sparse"
    if edge_density >= 0.28 or color_variance >= 0.35 or whitespace_ratio < 0.35:
        return "dense"
    return "balanced"


def _classify_composition(whitespace_ratio: float, edge_density: float, visual_density: str) -> str:
    if whitespace_ratio >= 0.98 and edge_density < 0.01:
        return "blank"
    if visual_density == "sparse":
        return "sparse_single_focus"
    if visual_density == "dense":
        return "dense_grid"
    return "balanced_blocks"


def _is_whitespace(pixel: tuple[int, int, int]) -> bool:
    return min(pixel) >= 238 and max(pixel) - min(pixel) <= 12


def _distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return sum(abs(left[idx] - right[idx]) for idx in range(3)) / 3


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
