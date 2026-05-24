"""Normalize rendered typography behavior."""

from __future__ import annotations

import json
import re
from collections import OrderedDict

from src.visual_signature.types import NormalizedTypographySignals, TypographySignal, VisualAcquisitionResult


FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;\"'}]+)", re.I)
FONT_SIZE = re.compile(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", re.I)
FONT_WEIGHT = re.compile(r"font-weight\s*:\s*(\d{3}|bold|normal|medium|semibold)", re.I)
HEADING_TAG = re.compile(r"<h([1-6])\b[^>]*>", re.I)


def normalize_typography(acquisition: VisualAcquisitionResult) -> NormalizedTypographySignals:
    html = "\n".join([acquisition.rendered_html or "", acquisition.raw_html or ""])
    markdown = acquisition.markdown or ""
    families: OrderedDict[str, TypographySignal] = OrderedDict()
    size_samples = _collect_number_samples(html)[:24]
    weights = _collect_weight_samples(html)
    heading_levels = _collect_heading_levels(html, markdown)

    for match in FONT_FAMILY.finditer(html):
        for family in _split_families(match.group(1)):
            _add_family(families, family, _role_from_context(html, match.start()), "rendered_html")

    for family in _infer_metadata_fonts(acquisition.metadata):
        _add_family(families, family, "unknown", "metadata")

    font_families = sorted(families.values(), key=lambda item: item.occurrences, reverse=True)[:12]
    confidence = _clamp(
        (0.35 if font_families else 0)
        + (0.2 if size_samples else 0)
        + (0.15 if weights else 0)
        + (0.2 if heading_levels else 0)
    )
    weight_range = {}
    if weights:
        weight_range = {"min": min(weights), "max": max(weights)}
    return NormalizedTypographySignals(
        font_families=font_families,
        heading_scale=_infer_heading_scale(size_samples, heading_levels),
        weight_range=weight_range,
        size_samples_px=size_samples,
        confidence=confidence,
    )


def _add_family(families: OrderedDict[str, TypographySignal], family: str, role: str, source: str) -> None:
    normalized = _normalize_family(family)
    if not normalized:
        return
    key = normalized.lower()
    existing = families.get(key)
    if existing:
        existing.occurrences += 1
        if existing.role == "unknown" and role != "unknown":
            existing.role = role  # type: ignore[assignment]
        return
    families[key] = TypographySignal(
        family=normalized,
        role=role,  # type: ignore[arg-type]
        occurrences=1,
        source=source,  # type: ignore[arg-type]
        confidence=0.25 if source == "metadata" else 0.65,
    )


def _split_families(value: str) -> list[str]:
    generic = {"inherit", "initial", "unset", "sans-serif", "serif", "monospace"}
    return [
        item
        for item in (
            part.strip().strip("'\"")
            for part in (value or "").split(",")
        )
        if item and item.lower() not in generic
    ]


def _normalize_family(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    return re.sub(r"^var\(|\)$", "", normalized)


def _collect_number_samples(text: str) -> list[float]:
    values = [float(match.group(1)) for match in FONT_SIZE.finditer(text or "")]
    return [value for value in values if 8 <= value <= 160]


def _collect_weight_samples(text: str) -> list[int]:
    values = []
    for match in FONT_WEIGHT.finditer(text or ""):
        raw = match.group(1).lower()
        if raw == "bold":
            values.append(700)
        elif raw == "semibold":
            values.append(600)
        elif raw == "medium":
            values.append(500)
        elif raw == "normal":
            values.append(400)
        else:
            values.append(int(raw))
    return [value for value in values if 100 <= value <= 900]


def _collect_heading_levels(html: str, markdown: str) -> list[int]:
    html_levels = [int(match.group(1)) for match in HEADING_TAG.finditer(html or "")]
    markdown_levels = [
        len(match.group(1))
        for line in (markdown or "").splitlines()
        if (match := re.match(r"^(#{1,6})\s+", line))
    ]
    return html_levels + markdown_levels


def _role_from_context(text: str, index: int) -> str:
    context = text[max(0, index - 160): index + 160].lower()
    if re.search(r"<h[1-6]\b", context) or "display" in context or "hero" in context:
        return "display"
    if "heading" in context or "headline" in context or "title" in context:
        return "heading"
    if "button" in context or "nav" in context or "menu" in context:
        return "ui"
    if "body" in context or "paragraph" in context:
        return "body"
    return "unknown"


def _infer_heading_scale(size_samples: list[float], heading_levels: list[int]) -> str:
    if not size_samples and not heading_levels:
        return "unknown"
    if len(size_samples) >= 2:
        ratio = max(size_samples) / max(1, min(size_samples))
        if ratio >= 3:
            return "expressive"
        if ratio >= 1.8:
            return "moderate"
        return "flat"
    return "moderate" if heading_levels and min(heading_levels) <= 1 and len(heading_levels) >= 3 else "flat"


def _infer_metadata_fonts(metadata: dict) -> list[str]:
    raw = json.dumps(metadata or {})
    matches = re.findall(r"(?:font|typeface)[^\"',:]*[\"':\s]+([A-Z][A-Za-z0-9\s-]{2,40})", raw)
    return [item.strip() for item in matches if item.strip()]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
