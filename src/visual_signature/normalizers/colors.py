"""Normalize rendered color behavior into Brand3 color signals."""

from __future__ import annotations

import re
from collections import OrderedDict

from src.visual_signature.types import ColorSignal, NormalizedColorSignals, VisualAcquisitionResult


HEX_COLOR = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
RGB_COLOR = re.compile(r"rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})(?:[\s,/]+[\d.]+)?\s*\)", re.I)


def normalize_colors(acquisition: VisualAcquisitionResult) -> NormalizedColorSignals:
    counts: OrderedDict[str, ColorSignal] = OrderedDict()
    sources = [
        (acquisition.rendered_html or "", "rendered_html"),
        (acquisition.raw_html or "", "raw_html"),
        (acquisition.markdown or "", "markdown"),
    ]
    for text, source in sources:
        _collect_hex_colors(text, source, counts)
        _collect_rgb_colors(text, source, counts)

    palette = sorted(counts.values(), key=lambda item: item.occurrences, reverse=True)[:24]
    for item in palette:
        item.confidence = _clamp(item.confidence + min(0.25, item.occurrences * 0.02))

    dominant = [item.hex for item in palette[:8]]
    accent = [
        item.hex
        for item in palette
        if item.role == "accent" or _saturation(item.hex) > 0.35
    ][:6]
    background = [
        item.hex
        for item in palette
        if item.role == "background" or _luminance(item.hex) > 0.82 or _luminance(item.hex) < 0.12
    ][:6]
    text = [
        item.hex
        for item in palette
        if item.role == "text" or _luminance(item.hex) < 0.2
    ][:6]
    return NormalizedColorSignals(
        palette=palette,
        dominant_colors=dominant,
        accent_candidates=accent,
        background_candidates=background,
        text_color_candidates=text,
        palette_complexity=_complexity(len(palette)),
        confidence=_clamp(0.35 + min(0.55, len(palette) / 18)) if palette else 0.05,
    )


def _collect_hex_colors(text: str, source: str, counts: OrderedDict[str, ColorSignal]) -> None:
    for match in HEX_COLOR.finditer(text or ""):
        color = _normalize_hex(match.group(0))
        if color:
            _add_color(counts, color, _role_from_context(text, match.start()), source)


def _collect_rgb_colors(text: str, source: str, counts: OrderedDict[str, ColorSignal]) -> None:
    for match in RGB_COLOR.finditer(text or ""):
        color = _rgb_to_hex(
            _clamp_channel(int(match.group(1))),
            _clamp_channel(int(match.group(2))),
            _clamp_channel(int(match.group(3))),
        )
        _add_color(counts, color, _role_from_context(text, match.start()), source)


def _add_color(counts: OrderedDict[str, ColorSignal], color: str, role: str, source: str) -> None:
    existing = counts.get(color)
    if existing:
        existing.occurrences += 1
        if existing.role == "unknown" and role != "unknown":
            existing.role = role  # type: ignore[assignment]
        return
    counts[color] = ColorSignal(
        hex=color,
        role=role,  # type: ignore[arg-type]
        occurrences=1,
        source=source,  # type: ignore[arg-type]
        confidence=0.6 if source in {"rendered_html", "raw_html"} else 0.35,
    )


def _role_from_context(text: str, index: int) -> str:
    context = text[max(0, index - 80): index + 80].lower()
    if "background" in context or "bg-" in context:
        return "background"
    if "color:" in context or "text-" in context or "foreground" in context:
        return "text"
    if "border" in context or "outline" in context:
        return "border"
    if "accent" in context or "primary" in context or "cta" in context:
        return "accent"
    if "surface" in context or "card" in context:
        return "surface"
    return "unknown"


def _normalize_hex(value: str) -> str | None:
    raw = value.replace("#", "").lower()
    if len(raw) in {3, 4}:
        return f"#{raw[0]}{raw[0]}{raw[1]}{raw[1]}{raw[2]}{raw[2]}"
    if len(raw) in {6, 8}:
        return f"#{raw[:6]}"
    return None


def _rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"


def _clamp_channel(value: int) -> int:
    return max(0, min(255, int(value)))


def _complexity(count: int) -> str:
    if count <= 0:
        return "unknown"
    if count <= 5:
        return "low"
    if count <= 14:
        return "medium"
    return "high"


def _rgb(hex_value: str) -> tuple[int, int, int]:
    raw = hex_value.replace("#", "")
    return int(raw[:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def _luminance(hex_value: str) -> float:
    channels = []
    for channel in _rgb(hex_value):
        normalized = channel / 255
        channels.append(normalized / 12.92 if normalized <= 0.03928 else ((normalized + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _saturation(hex_value: str) -> float:
    red, green, blue = [channel / 255 for channel in _rgb(hex_value)]
    max_value = max(red, green, blue)
    min_value = min(red, green, blue)
    return 0 if max_value == 0 else (max_value - min_value) / max_value


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
