#!/usr/bin/env python3
"""Inspect and compare Brand3 Visual Signature payloads.

This is developer tooling for calibration and evidence-quality review. It does
not run scoring, modify rubrics, or call Firecrawl. It only reads saved JSON
payloads and prints compact summaries of signal coverage and confidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SIGNAL_SECTIONS = (
    "colors",
    "typography",
    "logo",
    "layout",
    "components",
    "assets",
    "consistency",
)

WEAK_THRESHOLD = 0.45


def load_payload(path: str | Path) -> dict[str, Any]:
    payload_path = Path(path)
    with payload_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{payload_path} must contain a JSON object")
    return payload


def inspect_payload(payload: dict[str, Any], *, label: str | None = None) -> str:
    lines: list[str] = []
    title = label or str(payload.get("brand_name") or payload.get("brandName") or "Visual Signature")
    lines.append(f"== {title} ==")
    lines.append(f"URL: {payload.get('website_url') or payload.get('websiteUrl') or '-'}")
    lines.append(f"Interpretation status: {interpretation_status(payload)}")
    lines.append(_confidence_line(payload))
    lines.append("")
    lines.extend(_coverage_lines(payload))
    lines.append("")
    lines.extend(_summary_lines(payload))
    vision_lines = _vision_summary_lines(payload)
    if vision_lines:
        lines.append("")
        lines.extend(vision_lines)
    if is_not_interpretable(payload):
        failures = acquisition_failures(payload)
        lines.append("")
        lines.append("Acquisition failure:")
        lines.extend(f"- {item}" for item in failures)
    elif weak := weak_signals(payload):
        lines.append("")
        lines.append("Weak or missing signals:")
        lines.extend(f"- {item}" for item in weak)
    return "\n".join(lines)


def compare_payloads(named_payloads: list[tuple[str, dict[str, Any]]]) -> str:
    rows = []
    for label, payload in named_payloads:
        confidence = _get(payload, "extraction_confidence", "score", default=0.0)
        consistency = _get(payload, "consistency", "overall_consistency", default=0.0)
        coverage = signal_coverage(payload)
        weak_count = len(weak_signals(payload))
        rows.append(
            {
                "label": label,
                "brand": str(payload.get("brand_name") or payload.get("brandName") or "-"),
                "confidence": _as_float(confidence),
                "level": str(_get(payload, "extraction_confidence", "level", default="-")),
                "interpretation": interpretation_status(payload),
                "coverage": coverage,
                "consistency": _as_float(consistency),
                "weak": weak_count,
            }
        )
    rows.sort(key=lambda item: (item["confidence"], item["consistency"], item["coverage"]), reverse=True)
    lines = [
        "Visual Signature Comparison",
        "label | brand | interpretation | confidence | level | coverage | consistency | weak",
        "--- | --- | --- | ---: | --- | ---: | ---: | ---:",
    ]
    for row in rows:
        lines.append(
            f"{row['label']} | {row['brand']} | {row['interpretation']} | {row['confidence']:.2f} | {row['level']} | "
            f"{row['coverage']:.0%} | {row['consistency']:.2f} | {row['weak']}"
        )
    return "\n".join(lines)


def signal_coverage(payload: dict[str, Any]) -> float:
    available = 0
    for section in SIGNAL_SECTIONS:
        if _section_has_signal(section, payload.get(section) or {}):
            available += 1
    return available / len(SIGNAL_SECTIONS)


def weak_signals(payload: dict[str, Any]) -> list[str]:
    if is_not_interpretable(payload):
        return []

    weak: list[str] = []
    for section in SIGNAL_SECTIONS:
        section_payload = payload.get(section) or {}
        confidence = _section_confidence(section, section_payload)
        if not _section_has_signal(section, section_payload):
            weak.append(f"{section}: missing primary signal")
        elif confidence < WEAK_THRESHOLD:
            weak.append(f"{section}: weak confidence ({confidence:.2f})")

    extraction = payload.get("extraction_confidence") or {}
    for limitation in extraction.get("limitations") or []:
        weak.append(f"extraction limitation: {limitation}")
    return weak


def interpretation_status(payload: dict[str, Any]) -> str:
    status = str(payload.get("interpretation_status") or "").strip()
    if status:
        return status
    acquisition = payload.get("acquisition") or {}
    if acquisition.get("errors"):
        return "not_interpretable"
    return "interpretable"


def is_not_interpretable(payload: dict[str, Any]) -> bool:
    return interpretation_status(payload) == "not_interpretable"


def acquisition_failures(payload: dict[str, Any]) -> list[str]:
    acquisition = payload.get("acquisition") or {}
    failures = [f"acquisition error: {item}" for item in acquisition.get("errors") or []]
    extraction = payload.get("extraction_confidence") or {}
    failures.extend(f"extraction limitation: {item}" for item in extraction.get("limitations") or [])
    return failures or ["payload is marked not_interpretable"]


def _confidence_line(payload: dict[str, Any]) -> str:
    extraction = payload.get("extraction_confidence") or {}
    score = _as_float(extraction.get("score"))
    level = extraction.get("level") or "unknown"
    factors = extraction.get("factors") or {}
    factor_text = ", ".join(f"{key}={_as_float(value):.2f}" for key, value in factors.items()) or "no factors"
    return f"Extraction confidence: {score:.2f} ({level}) [{factor_text}]"


def _coverage_lines(payload: dict[str, Any]) -> list[str]:
    lines = [f"Signal coverage: {signal_coverage(payload):.0%}"]
    for section in SIGNAL_SECTIONS:
        section_payload = payload.get(section) or {}
        status = "ok" if _section_has_signal(section, section_payload) else "missing"
        lines.append(f"- {section}: {status}, confidence={_section_confidence(section, section_payload):.2f}")
    return lines


def _summary_lines(payload: dict[str, Any]) -> list[str]:
    colors = payload.get("colors") or {}
    typography = payload.get("typography") or {}
    layout = payload.get("layout") or {}
    components = payload.get("components") or {}
    consistency = payload.get("consistency") or {}

    palette = colors.get("dominant_colors") or [item.get("hex") for item in colors.get("palette") or [] if isinstance(item, dict)]
    font_families = typography.get("font_families") or []
    font_names = [str(item.get("family")) for item in font_families if isinstance(item, dict) and item.get("family")]
    component_rows = components.get("components") or []
    component_summary = ", ".join(
        f"{item.get('type')}={item.get('count')}"
        for item in component_rows
        if isinstance(item, dict)
    )
    layout_bits = [
        f"header={bool(layout.get('has_header'))}",
        f"nav={bool(layout.get('has_navigation'))}",
        f"hero={bool(layout.get('has_hero'))}",
        f"sections={int(layout.get('section_count') or 0)}",
        f"density={layout.get('visual_density') or 'unknown'}",
        f"patterns={','.join(layout.get('layout_patterns') or []) or 'unknown'}",
    ]
    consistency_bits = [
        f"overall={_as_float(consistency.get('overall_consistency')):.2f}",
        f"color={_as_float(consistency.get('color_consistency')):.2f}",
        f"type={_as_float(consistency.get('typography_consistency')):.2f}",
        f"component={_as_float(consistency.get('component_consistency')):.2f}",
        f"asset={_as_float(consistency.get('asset_consistency')):.2f}",
    ]
    return [
        "Visual summaries:",
        f"- palette preview: {_palette_preview([str(item) for item in palette if item])}",
        f"- typography: {', '.join(font_names) if font_names else 'none'}",
        f"- layout: {'; '.join(layout_bits)}",
        f"- components: {component_summary or 'none'}",
        f"- consistency: {'; '.join(consistency_bits)}",
    ]


def _vision_summary_lines(payload: dict[str, Any]) -> list[str]:
    vision = payload.get("vision") or {}
    if not isinstance(vision, dict):
        return []
    screenshot = vision.get("screenshot") or {}
    palette = vision.get("screenshot_palette") or {}
    viewport_palette = vision.get("viewport_palette") or {}
    composition = vision.get("composition") or {}
    viewport_composition = vision.get("viewport_composition") or {}
    agreement = vision.get("agreement") or {}
    confidence = vision.get("vision_confidence") or {}
    viewport_confidence = vision.get("viewport_confidence") or {}
    colors = [
        item.get("hex")
        for item in palette.get("dominant_colors") or []
        if isinstance(item, dict) and item.get("hex")
    ]
    viewport_colors = [
        item.get("hex")
        for item in viewport_palette.get("dominant_colors") or []
        if isinstance(item, dict) and item.get("hex")
    ]
    dimensions = "-"
    if screenshot.get("width") and screenshot.get("height"):
        dimensions = f"{screenshot.get('width')}x{screenshot.get('height')}"
    viewport_dimensions = "-"
    if screenshot.get("viewport_width") and screenshot.get("viewport_height"):
        viewport_dimensions = f"{screenshot.get('viewport_width')}x{screenshot.get('viewport_height')}"
    return [
        "Vision summaries:",
        (
            "- screenshot: "
            f"available={bool(screenshot.get('available'))}; "
            f"quality={screenshot.get('quality') or 'unknown'}; "
            f"capture_type={screenshot.get('capture_type') or 'unknown'}; "
            f"dimensions={dimensions}; viewport={viewport_dimensions}"
        ),
        f"- screenshot palette: {_palette_preview([str(item) for item in colors])}",
        f"- viewport palette: {_palette_preview([str(item) for item in viewport_colors])}",
        (
            "- composition: "
            f"density={composition.get('visual_density') or 'unknown'}; "
            f"whitespace={_format_optional_ratio(composition.get('whitespace_ratio'))}; "
            f"classification={composition.get('composition_classification') or 'unknown'}"
        ),
        (
            "- viewport composition: "
            f"density={viewport_composition.get('visual_density') or 'unknown'}; "
            f"whitespace={_format_optional_ratio(viewport_composition.get('whitespace_ratio'))}; "
            f"classification={viewport_composition.get('composition_classification') or 'unknown'}"
        ),
        (
            "- vision confidence: "
            f"{_as_float(confidence.get('score')):.2f} "
            f"({confidence.get('level') or 'unknown'})"
        ),
        (
            "- viewport confidence: "
            f"{_as_float(viewport_confidence.get('score')):.2f} "
            f"({viewport_confidence.get('level') or 'unknown'})"
        ),
        (
            "- agreement: "
            f"{agreement.get('agreement_level') or 'unknown'}; "
            f"flags={','.join(agreement.get('disagreement_flags') or []) or 'none'}"
        ),
        f"- agreement notes: {'; '.join(agreement.get('summary_notes') or []) or 'none'}",
    ]


def _palette_preview(colors: list[str]) -> str:
    if not colors:
        return "none"
    return " ".join(f"{color}[###]" for color in colors[:10])


def _section_has_signal(section: str, value: dict[str, Any]) -> bool:
    if section == "colors":
        return bool(value.get("palette") or value.get("dominant_colors"))
    if section == "typography":
        return bool(value.get("font_families"))
    if section == "logo":
        return bool(value.get("logo_detected") or value.get("candidates"))
    if section == "layout":
        return bool(value.get("has_header") or value.get("has_navigation") or value.get("has_main_content") or value.get("section_count"))
    if section == "components":
        return bool(value.get("components") or value.get("primary_ctas"))
    if section == "assets":
        return bool(value.get("image_count") or value.get("svg_count") or value.get("screenshot_available") or value.get("asset_mix"))
    if section == "consistency":
        return bool(value.get("overall_consistency") is not None)
    return bool(value)


def _section_confidence(section: str, value: dict[str, Any]) -> float:
    if section == "consistency" and "confidence" not in value:
        return _as_float(value.get("overall_consistency"))
    return _as_float(value.get("confidence"))


def _get(payload: dict[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_optional_ratio(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "-"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect saved Visual Signature JSON payloads.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one Visual Signature payload.")
    inspect_parser.add_argument("payload", help="Path to a Visual Signature JSON file.")

    compare_parser = subparsers.add_parser("compare", help="Compare two or more Visual Signature payloads.")
    compare_parser.add_argument("payloads", nargs="+", help="Paths to Visual Signature JSON files.")

    args = parser.parse_args(argv)
    if args.command == "inspect":
        payload = load_payload(args.payload)
        print(inspect_payload(payload, label=Path(args.payload).stem))
        return 0
    if args.command == "compare":
        named_payloads = [(Path(path).stem, load_payload(path)) for path in args.payloads]
        print(compare_payloads(named_payloads))
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
