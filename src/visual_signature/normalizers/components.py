"""Normalize observable component and interaction signals."""

from __future__ import annotations

import re

from src.visual_signature.types import ComponentSignal, NormalizedComponentSignals, VisualAcquisitionResult


def normalize_component_signals(acquisition: VisualAcquisitionResult) -> NormalizedComponentSignals:
    html = "\n".join([acquisition.rendered_html or "", acquisition.raw_html or ""])
    markdown = acquisition.markdown or ""
    ctas = _cta_labels(html, markdown)
    components = [
        _signal("navigation", _count(r"<nav\b", html), _nav_labels(html), 0.7),
        _signal("button", _count(r"<button\b", html), _button_labels(html), 0.72),
        _signal("cta", len(ctas), ctas, 0.62),
        _signal("form", _count(r"<form\b|<input\b|<textarea\b|<select\b", html), [], 0.68),
        _signal("card", _count(r"\bcard\b|<article\b", html), [], 0.48),
        _signal("accordion", _count(r"\baccordion\b|aria-expanded=", html), [], 0.45),
        _signal("tabs", _count(r"\btablist\b|\btabs?\b|role=[\"']tab", html), [], 0.45),
        _signal("modal", _count(r"\bmodal\b|role=[\"']dialog", html), [], 0.45),
        _signal("pricing", _count(r"\bpricing\b|\bprice-card\b|\bplan\b", html), [], 0.42),
    ]
    components = [item for item in components if item.count > 0]
    patterns: list[str] = []
    for item in components:
        if item.type == "form":
            patterns.append("form")
        elif item.type == "navigation":
            patterns.append("navigation")
        elif item.type == "accordion":
            patterns.append("accordion")
        elif item.type == "tabs":
            patterns.append("tabs")
        elif item.type == "modal":
            patterns.append("modal")
    patterns = _unique(patterns) or ["unknown"]
    return NormalizedComponentSignals(
        components=components,
        primary_ctas=ctas[:8],
        interaction_patterns=patterns,
        confidence=_clamp(
            (0.25 if html.strip() else 0)
            + min(0.35, len(components) * 0.06)
            + (0.15 if ctas else 0)
            + (0.15 if patterns != ["unknown"] else 0)
        ),
    )


def _signal(type_name: str, count: int, labels: list[str], confidence: float) -> ComponentSignal:
    return ComponentSignal(
        type=type_name,  # type: ignore[arg-type]
        count=count,
        labels=_unique(labels)[:10],
        source="rendered_html",
        confidence=confidence,
    )


def _button_labels(html: str) -> list[str]:
    return [
        cleaned
        for match in re.finditer(r"<button\b[^>]*>([\s\S]*?)</button>", html or "", re.I)
        if (cleaned := _clean_text(match.group(1)))
    ]


def _nav_labels(html: str) -> list[str]:
    labels: list[str] = []
    for nav in re.finditer(r"<nav\b[^>]*>([\s\S]*?)</nav>", html or "", re.I):
        labels.extend(
            cleaned
            for link in re.finditer(r"<a\b[^>]*>([\s\S]*?)</a>", nav.group(1), re.I)
            if (cleaned := _clean_text(link.group(1)))
        )
    return labels


def _cta_labels(html: str, markdown: str) -> list[str]:
    html_labels = [
        cleaned
        for match in re.finditer(
            r"<(?:a|button)\b[^>]*(?:btn|button|cta|primary|signup|demo|get-started)[^>]*>([\s\S]*?)</(?:a|button)>",
            html or "",
            re.I,
        )
        if (cleaned := _clean_text(match.group(1)))
    ]
    markdown_labels = [
        match.group(1).strip()
        for match in re.finditer(r"\[([^\]]{2,80})\]\([^)]+\)", markdown or "")
        if re.search(r"get|start|try|book|demo|contact|sign|join|buy|pricing|learn", match.group(1), re.I)
    ]
    return _unique(html_labels + markdown_labels)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()[:80]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _count(pattern: str, value: str) -> int:
    return len(re.findall(pattern, value or "", flags=re.I))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
