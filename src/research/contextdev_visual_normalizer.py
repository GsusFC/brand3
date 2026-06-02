"""Semantic normalization for Context.dev visual identity candidates."""

from __future__ import annotations

import json
import re
from typing import Any


def normalize_contextdev_visual_signal(candidate_type: str, text: str) -> str:
    """Convert raw Context.dev visual payloads into Analyst-friendly signals."""

    candidate_type = str(candidate_type or "")
    if candidate_type == "visual_colors":
        return _normalize_colors(text)
    if candidate_type == "visual_typography":
        return _normalize_typography(text)
    if candidate_type == "visual_components":
        return _normalize_components(text)
    if candidate_type == "visual_fonts":
        return _normalize_fonts(text)
    return _clean_text(text)


def _normalize_colors(text: str) -> str:
    payload = _json_obj(text)
    values = [_hex(value) for value in payload.values()]
    colors = [value for value in values if value]
    if not colors:
        return _clean_text(text)

    background = _hex(payload.get("background"))
    accent = _hex(payload.get("accent"))
    foreground = _hex(payload.get("text"))
    descriptors = []
    if background:
        descriptors.append(f"{_tone(background)} background")
    if foreground:
        descriptors.append(f"{_tone(foreground)} text contrast")
    if accent:
        descriptors.append(f"{_tone(accent)} accent")
    palette = ", ".join(part for part in descriptors if part)
    if not palette:
        palette = ", ".join(_tone(color) for color in colors[:3])
    return f"Visual identity signal: {palette}, suggesting {_palette_intent(colors)}."


def _normalize_typography(text: str) -> str:
    payload = _json_obj(text)
    font_families = _collect_values(payload, "fontFamily")
    weights = _collect_values(payload, "fontWeight")
    sizes = _collect_values(payload, "fontSize")
    fonts = _unique([str(item) for item in font_families if item])[:3]
    weight_label = _weight_label(weights)
    scale_label = _scale_label(sizes)
    parts = []
    if fonts:
        parts.append(f"{', '.join(fonts)} typography")
    if weight_label:
        parts.append(weight_label)
    if scale_label:
        parts.append(scale_label)
    if not parts:
        return _clean_text(text)
    return f"Typography signal: {', '.join(parts)}, supporting a {_typography_intent(fonts, weight_label)} personality."


def _normalize_components(text: str) -> str:
    payload = _json_obj(text)
    radii = _collect_values(payload, "borderRadius")
    min_heights = _collect_values(payload, "minHeight")
    border_colors = [_hex(item) for item in _collect_values(payload, "borderColor")]
    component_names = ", ".join(sorted(str(key) for key in payload.keys())[:4]) if payload else ""
    traits = []
    if _has_large_radius(radii):
        traits.append("rounded card surfaces")
    if _has_substantial_height(min_heights):
        traits.append("substantial call-to-action controls")
    if any(color and _brightness(color) < 90 for color in border_colors):
        traits.append("subtle low-contrast borders")
    if not traits:
        return _clean_text(text)
    prefix = f"{component_names} components" if component_names else "Component system"
    return f"Component signal: {prefix} use {', '.join(traits)}, suggesting controlled, product-led polish."


def _normalize_fonts(text: str) -> str:
    fonts = _unique([part.strip() for part in str(text or "").split(",") if part.strip()])
    if not fonts:
        return _clean_text(text)
    font_text = ", ".join(fonts[:4])
    return f"Font signal: {font_text}, suggesting {_font_intent(fonts)}."


def _json_obj(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _collect_values(value: Any, key: str) -> list[Any]:
    results = []
    if isinstance(value, dict):
        for item_key, item_value in value.items():
            if item_key == key:
                results.append(item_value)
            results.extend(_collect_values(item_value, key))
    elif isinstance(value, list):
        for item in value:
            results.extend(_collect_values(item, key))
    return results


def _tone(hex_color: str) -> str:
    brightness = _brightness(hex_color)
    r, g, b = _rgb(hex_color)
    if brightness < 45:
        return "near-black"
    if brightness < 95:
        return "dark"
    if brightness > 235:
        return "bright white"
    if b > r + 25 and b > g:
        return "electric blue"
    if g > r + 20 and g > b:
        return "green"
    if r > g + 20 and r > b:
        return "warm"
    return "muted"


def _palette_intent(colors: list[str]) -> str:
    has_dark = any(_brightness(color) < 70 for color in colors)
    has_bright = any(_brightness(color) > 220 for color in colors)
    has_blue = any(_rgb(color)[2] > _rgb(color)[0] + 25 and _rgb(color)[2] > _rgb(color)[1] for color in colors)
    if has_dark and has_blue:
        return "a technical, high-control interface stance"
    if has_dark and has_bright:
        return "premium contrast and focused product seriousness"
    return "a deliberate visual system rather than generic decoration"


def _typography_intent(fonts: list[str], weight_label: str) -> str:
    joined = " ".join(fonts).lower()
    if "aeonik" in joined or "lausanne" in joined:
        return "modern, engineered"
    if "mono" in joined:
        return "technical"
    if "lightweight" in weight_label:
        return "precise, editorial"
    return "structured"


def _font_intent(fonts: list[str]) -> str:
    joined = " ".join(fonts).lower()
    if "aeonik" in joined or "lausanne" in joined:
        return "a contemporary technical/editorial brand voice"
    if "mono" in joined:
        return "a technical and code-adjacent brand voice"
    return "a defined visual voice"


def _weight_label(weights: list[Any]) -> str:
    ints = [_int(value) for value in weights]
    ints = [value for value in ints if value is not None]
    if not ints:
        return ""
    average = sum(ints) / len(ints)
    if average <= 350:
        return "lightweight type"
    if average >= 650:
        return "bold type"
    return "regular-weight type"


def _scale_label(sizes: list[Any]) -> str:
    ints = [_int(value) for value in sizes]
    ints = [value for value in ints if value is not None]
    if not ints:
        return ""
    if max(ints) >= 48:
        return "large editorial headings"
    if max(ints) >= 32:
        return "clear heading hierarchy"
    return "compact typography"


def _has_large_radius(values: list[Any]) -> bool:
    return any((_int(value) or 0) >= 24 for value in values)


def _has_substantial_height(values: list[Any]) -> bool:
    return any((_int(value) or 0) >= 44 for value in values)


def _hex(value: Any) -> str:
    match = re.search(r"#[0-9a-fA-F]{6}", str(value or ""))
    return match.group(0).lower() if match else ""


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _brightness(hex_color: str) -> float:
    r, g, b = _rgb(hex_color)
    return (0.299 * r) + (0.587 * g) + (0.114 * b)


def _int(value: Any) -> int | None:
    match = re.search(r"-?\d+", str(value or ""))
    return int(match.group(0)) if match else None


def _unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        normalized = _clean_text(value)
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        result.append(normalized)
    return result


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())
