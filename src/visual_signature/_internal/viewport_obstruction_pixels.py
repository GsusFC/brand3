"""Viewport pixel helpers for obstruction heuristics."""

from __future__ import annotations

from src.visual_signature.vision.types import RasterImage


def centered_modal_score(image: RasterImage) -> float:
    center = region_stats(image, 0.28, 0.22, 0.72, 0.78)
    outer = outer_region_stats(image, 0.12)
    if not center or not outer:
        return 0.0
    brightness_gap = center["brightness"] - outer["brightness"]
    outer_dark = outer["dark_ratio"]
    center_light = center["light_ratio"]
    if outer_dark >= 0.45 and brightness_gap >= 35 and center_light >= 0.25:
        return round(min(0.72, 0.45 + outer_dark * 0.25 + min(0.2, brightness_gap / 255)), 3)
    return 0.0


def fullscreen_overlay_score(image: RasterImage) -> float:
    sample = image.sample_pixels(8000)
    if not sample:
        return 0.0
    dark_ratio = sum(1 for pixel in sample if brightness(pixel) <= 38) / len(sample)
    mid_dark_ratio = sum(1 for pixel in sample if brightness(pixel) <= 75) / len(sample)
    unique_ratio = len(set(sample)) / len(sample)
    if dark_ratio >= 0.88 and unique_ratio <= 0.08:
        return round(dark_ratio, 3)
    if mid_dark_ratio >= 0.92 and unique_ratio <= 0.04:
        return round(min(0.95, mid_dark_ratio), 3)
    return 0.0


def bottom_bar_ratio(image: RasterImage) -> float:
    if image.height < 10:
        return 0.0
    reference_y = max(0, int(image.height * 0.55))
    reference = row_average(image, reference_y)
    bottom = row_average(image, image.height - 1)
    if distance(reference, bottom) < 20:
        return 0.0

    bar_rows = 0
    for y in range(image.height - 1, -1, -1):
        row = row_average(image, y)
        if distance(row, bottom) <= 24:
            bar_rows += 1
            continue
        break
    ratio = bar_rows / image.height
    if 0.05 <= ratio <= 0.4:
        return round(ratio, 3)
    return 0.0


def region_stats(image: RasterImage, x0: float, y0: float, x1: float, y1: float) -> dict[str, float]:
    left = max(0, min(image.width - 1, int(image.width * x0)))
    right = max(left + 1, min(image.width, int(image.width * x1)))
    top = max(0, min(image.height - 1, int(image.height * y0)))
    bottom = max(top + 1, min(image.height, int(image.height * y1)))
    return pixel_stats(image.sample_grid(max_width=80, max_height=60, left=left, top=top, right=right, bottom=bottom))


def outer_region_stats(image: RasterImage, border_ratio: float) -> dict[str, float]:
    border_x = max(1, int(image.width * border_ratio))
    border_y = max(1, int(image.height * border_ratio))
    pixels = []
    pixels.extend(image.sample_grid(max_width=100, max_height=20, left=0, top=0, right=image.width, bottom=border_y))
    pixels.extend(
        image.sample_grid(
            max_width=100,
            max_height=20,
            left=0,
            top=max(0, image.height - border_y),
            right=image.width,
            bottom=image.height,
        )
    )
    middle_top = border_y
    middle_bottom = max(border_y, image.height - border_y)
    if middle_top < middle_bottom:
        pixels.extend(image.sample_grid(max_width=20, max_height=60, left=0, top=middle_top, right=border_x, bottom=middle_bottom))
        pixels.extend(
            image.sample_grid(
                max_width=20,
                max_height=60,
                left=max(0, image.width - border_x),
                top=middle_top,
                right=image.width,
                bottom=middle_bottom,
            )
        )
    return pixel_stats(pixels)


def pixel_stats(pixels: list[tuple[int, int, int]]) -> dict[str, float]:
    if not pixels:
        return {}
    brightness_values = [brightness(pixel) for pixel in pixels]
    return {
        "brightness": sum(brightness_values) / len(brightness_values),
        "dark_ratio": sum(1 for value in brightness_values if value <= 70) / len(brightness_values),
        "light_ratio": sum(1 for value in brightness_values if value >= 210) / len(brightness_values),
    }


def row_average(image: RasterImage, y: int) -> tuple[int, int, int]:
    row = image.row_pixels(y)
    if not row:
        return (0, 0, 0)
    return tuple(int(sum(pixel[channel] for pixel in row) / len(row)) for channel in range(3))  # type: ignore[return-value]


def brightness(pixel: tuple[int, int, int]) -> float:
    return pixel[0] * 0.2126 + pixel[1] * 0.7152 + pixel[2] * 0.0722


def distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return sum(abs(left[idx] - right[idx]) for idx in range(3)) / 3
