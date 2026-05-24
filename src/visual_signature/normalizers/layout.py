"""Normalize rendered layout behavior."""

from __future__ import annotations

import re

from src.visual_signature.types import NormalizedLayoutSignals, VisualAcquisitionResult


def normalize_layout_signals(acquisition: VisualAcquisitionResult) -> NormalizedLayoutSignals:
    html = "\n".join([acquisition.rendered_html or "", acquisition.raw_html or ""])
    lower = html.lower()
    section_count = _count(r"<section\b", lower) + _count(r"class=[\"'][^\"']*\bsection\b", lower)
    patterns: list[str] = []
    if re.search(r"\bgrid\b|display\s*:\s*grid|grid-template", html, re.I):
        patterns.append("grid")
    if re.search(r"\bflex\b|display\s*:\s*flex", html, re.I):
        patterns.append("flex")
    if re.search(r"\bcol-|columns?|two-column|three-column|split\b", html, re.I):
        patterns.append("multi_column")
    if not patterns and html.strip():
        patterns.append("single_column")
    if re.search(r"position\s*:\s*sticky|sticky|fixed top|navbar-fixed", html, re.I):
        patterns.append("sticky_nav")

    return NormalizedLayoutSignals(
        has_header="<header" in lower or bool(re.search(r"\bheader\b", lower)),
        has_navigation="<nav" in lower or bool(re.search(r"\bnavbar\b|\bmenu\b", lower)),
        has_hero=bool(re.search(r"\bhero\b|above[-_\s]?the[-_\s]?fold|<h1\b", html, re.I)),
        has_main_content="<main" in lower or len(lower) > 1000,
        has_footer="<footer" in lower or bool(re.search(r"\bfooter\b", lower)),
        section_count=section_count,
        layout_patterns=patterns or ["unknown"],
        visual_density=_infer_density(html, section_count),
        confidence=_clamp(
            (0.3 if html.strip() else 0)
            + (0.15 if "<main" in lower else 0)
            + (0.2 if "<header" in lower or "<nav" in lower else 0)
            + (0.15 if section_count else 0)
            + (0.15 if patterns else 0)
        ),
    )


def _infer_density(html: str, section_count: int) -> str:
    if not html.strip():
        return "unknown"
    text_length = len(re.sub(r"\s+", " ", _strip_tags(html)).strip())
    interactive_count = _count(r"<(?:a|button|input|select|textarea)\b", html)
    denominator = max(1.0, float(section_count or _count(r"<div\b", html) / 8))
    density = (text_length / 500 + interactive_count / 8) / denominator
    if density < 1.1:
        return "sparse"
    if density > 3.2:
        return "dense"
    return "balanced"


def _strip_tags(value: str) -> str:
    without_scripts = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    without_styles = re.sub(r"<style[\s\S]*?</style>", " ", without_scripts, flags=re.I)
    return re.sub(r"<[^>]+>", " ", without_styles)


def _count(pattern: str, value: str) -> int:
    return len(re.findall(pattern, value or "", flags=re.I))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
