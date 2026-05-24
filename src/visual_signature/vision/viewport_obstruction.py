"""Viewport obstruction heuristics for Visual Signature evidence quality.

This module detects likely cookie banners, modals, login walls, and overlays
that can compromise first-impression visual analysis. It is evidence-only: it
does not click, dismiss, mutate DOM, bypass protections, or affect scoring.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from src.visual_signature.vision.types import RasterImage


ObstructionType = Literal[
    "cookie_banner",
    "cookie_modal",
    "newsletter_modal",
    "login_wall",
    "promo_modal",
    "unknown_overlay",
    "none",
]
ObstructionSeverity = Literal["minor", "moderate", "major", "blocking", "none"]

COOKIE_TERMS = (
    "cookie",
    "cookies",
    "consent",
    "privacy",
    "gdpr",
    "ccpa",
    "onetrust",
    "trustarc",
    "usercentrics",
    "cookiebot",
    "didomi",
    "quantcast",
    "cmp",
)
NEWSLETTER_TERMS = ("newsletter", "subscribe", "subscription", "email signup")
LOGIN_TERMS = ("login", "log in", "sign in", "signin", "create account", "members only", "paywall")
PROMO_TERMS = ("promo", "promotion", "discount", "offer", "sale", "coupon")
OVERLAY_TERMS = (
    "modal",
    "dialog",
    "overlay",
    "backdrop",
    "popup",
    "pop-up",
    "popover",
    "aria-modal",
    "role=\"dialog",
    "role='dialog",
)


@dataclass
class ViewportObstructionEvidence:
    present: bool
    type: ObstructionType = "none"
    severity: ObstructionSeverity = "none"
    coverage_ratio: float = 0.0
    first_impression_valid: bool = True
    confidence: float = 0.0
    page_level_signals: list[str] = field(default_factory=list)
    overlay_level_signals: list[str] = field(default_factory=list)
    visual_signals: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if payload["type"] == "none":
            payload["type"] = "unknown_overlay" if payload["present"] else "none"
        return payload


def analyze_viewport_obstruction(
    *,
    dom_html: str | None = None,
    viewport_image: RasterImage | None = None,
    existing_obstruction: dict[str, Any] | None = None,
) -> ViewportObstructionEvidence:
    """Combine DOM and viewport heuristics into an obstruction evidence record."""
    dom = _dom_obstruction(dom_html or "")
    viewport = _viewport_obstruction(viewport_image)
    existing = _coerce_existing(existing_obstruction)

    page_level_signals = _unique(existing.page_level_signals + dom.page_level_signals + viewport.page_level_signals)
    overlay_level_signals = _unique(existing.overlay_level_signals + dom.overlay_level_signals + viewport.overlay_level_signals)
    visual_signals = _unique(existing.visual_signals + dom.visual_signals + viewport.visual_signals)
    signals = _unique(existing.signals + dom.signals + viewport.signals + page_level_signals + overlay_level_signals + visual_signals)
    limitations = _unique(existing.limitations + dom.limitations + viewport.limitations)
    present = existing.present or dom.present or viewport.present
    obstruction_type = _choose_type(existing.type, dom.type, viewport.type)
    coverage_ratio = max(existing.coverage_ratio, dom.coverage_ratio, viewport.coverage_ratio)

    if not present and signals:
        limitations.append("weak_obstruction_signals_below_presence_threshold")
    severity = _severity(coverage_ratio, obstruction_type, present)
    first_impression_valid = not (
        severity in {"major", "blocking"}
        or obstruction_type == "login_wall"
        or coverage_ratio >= 0.45
        or existing.first_impression_valid is False
    )
    confidence = _confidence(
        present=present,
        dom_present=dom.present or existing.present,
        viewport_present=viewport.present,
        obstruction_type=obstruction_type,
        coverage_ratio=coverage_ratio,
        signal_count=len(signals),
    )
    if viewport_image is None:
        limitations.append("viewport_pixels_unavailable_for_obstruction_analysis")
    if not dom_html and not existing.signals:
        limitations.append("dom_obstruction_signals_unavailable")

    return ViewportObstructionEvidence(
        present=present,
        type=obstruction_type if present else "none",
        severity=severity,
        coverage_ratio=round(min(1.0, max(0.0, coverage_ratio)), 3),
        first_impression_valid=first_impression_valid,
        confidence=confidence,
        page_level_signals=page_level_signals,
        overlay_level_signals=overlay_level_signals,
        visual_signals=visual_signals,
        signals=signals,
        limitations=_unique(limitations),
    )


def _dom_obstruction(html: str) -> ViewportObstructionEvidence:
    text = (html or "").lower()
    if not text.strip():
        return ViewportObstructionEvidence(
            present=False,
            confidence=0.0,
            limitations=["dom_html_unavailable"],
        )

    page_level_signals: list[str] = []
    overlay_level_signals: list[str] = []
    visual_signals: list[str] = []
    cookie_page_hits, cookie_overlay_hits = _split_term_signals(text, COOKIE_TERMS, signal_prefix="dom_keyword")
    newsletter_page_hits, newsletter_overlay_hits = _split_term_signals(text, NEWSLETTER_TERMS, signal_prefix="dom_keyword")
    login_page_hits, login_overlay_hits = _split_term_signals(text, LOGIN_TERMS, signal_prefix="dom_keyword")
    promo_page_hits, promo_overlay_hits = _split_term_signals(text, PROMO_TERMS, signal_prefix="dom_keyword")
    overlay_page_hits, overlay_overlay_hits = _split_term_signals(text, OVERLAY_TERMS, signal_prefix="dom_overlay_term")
    fixed_like = bool(re.search(r"position\s*:\s*fixed|\bfixed\b|inset-0|fixed-bottom|bottom-0|sticky", text))
    bottom_like = bool(re.search(r"bottom\s*:\s*0|bottom-0|fixed-bottom|cookie[-_\s]?bar|consent[-_\s]?bar", text))
    full_like = bool(re.search(r"inset\s*:\s*0|inset-0|height\s*:\s*100(?:vh|%)|min-height\s*:\s*100vh|w-screen|h-screen", text))
    high_z = bool(re.search(r"z-index\s*:\s*(?:[9]\d{2,}|\d{4,})|z-\[?\d{3,}\]?|z-50", text))

    page_level_signals.extend(cookie_page_hits[:4])
    page_level_signals.extend(newsletter_page_hits[:3])
    page_level_signals.extend(login_page_hits[:3])
    page_level_signals.extend(promo_page_hits[:3])
    page_level_signals.extend(overlay_page_hits[:4])
    overlay_level_signals.extend(cookie_overlay_hits[:4])
    overlay_level_signals.extend(newsletter_overlay_hits[:3])
    overlay_level_signals.extend(login_overlay_hits[:3])
    overlay_level_signals.extend(promo_overlay_hits[:3])
    overlay_level_signals.extend(overlay_overlay_hits[:4])
    if fixed_like:
        visual_signals.append("dom_fixed_or_sticky_position_pattern")
    if bottom_like:
        visual_signals.append("dom_bottom_aligned_container_pattern")
    if full_like:
        visual_signals.append("dom_full_viewport_container_pattern")
    if high_z:
        visual_signals.append("dom_high_z_index_pattern")

    obstruction_type: ObstructionType = "none"
    cookie_terms_present = bool(cookie_page_hits or cookie_overlay_hits)
    newsletter_terms_present = bool(newsletter_page_hits or newsletter_overlay_hits)
    overlay_local_login = bool(login_overlay_hits)
    promo_terms_present = bool(promo_page_hits or promo_overlay_hits)
    strong_overlay = _context_has_overlay_cues(text) or fixed_like or bottom_like or full_like or high_z
    if overlay_local_login and strong_overlay:
        obstruction_type = "login_wall"
    elif newsletter_terms_present and strong_overlay:
        obstruction_type = "newsletter_modal"
    elif promo_terms_present and strong_overlay:
        obstruction_type = "promo_modal"
    elif cookie_terms_present and strong_overlay:
        obstruction_type = "cookie_modal" if not bottom_like else "cookie_banner"
    elif (overlay_level_signals or visual_signals) and (fixed_like or high_z or full_like or bottom_like):
        obstruction_type = "unknown_overlay"
    elif fixed_like and bottom_like:
        obstruction_type = "unknown_overlay"

    present = obstruction_type != "none"
    coverage = 0.0
    if present:
        coverage = _dom_coverage(
            text,
            obstruction_type,
            bottom_like=bottom_like,
            full_like=full_like,
            overlay=bool(overlay_level_signals),
        )

    limitations: list[str] = []
    if (cookie_page_hits or login_page_hits or newsletter_page_hits or promo_page_hits) and not present:
        limitations.append("cookie_terms_without_overlay_or_fixed_position_pattern")
    return ViewportObstructionEvidence(
        present=present,
        type=obstruction_type if present else "none",
        coverage_ratio=coverage,
        confidence=0.0,
        page_level_signals=_unique(page_level_signals),
        overlay_level_signals=_unique(overlay_level_signals),
        visual_signals=_unique(visual_signals),
        signals=_unique(page_level_signals + overlay_level_signals + visual_signals),
        limitations=limitations,
    )


def _viewport_obstruction(image: RasterImage | None) -> ViewportObstructionEvidence:
    if image is None or not image.pixels or image.width <= 0 or image.height <= 0:
        return ViewportObstructionEvidence(
            present=False,
            confidence=0.0,
            limitations=["viewport_pixels_unavailable"],
        )

    visual_signals: list[str] = []
    coverage = 0.0
    obstruction_type: ObstructionType = "none"

    centered_modal = _centered_modal_score(image)
    if centered_modal >= 0.65:
        visual_signals.append("viewport_centered_modal_with_backdrop")
        coverage = max(coverage, min(0.72, centered_modal))
        obstruction_type = "unknown_overlay"

    full_overlay_score = _fullscreen_overlay_score(image)
    if full_overlay_score >= 0.86:
        visual_signals.append("viewport_fullscreen_overlay_pattern")
        # A dark or single-color viewport can be a legitimate visual system.
        # Treat fullscreen darkness as supporting evidence; DOM/existing
        # obstruction signals decide whether it is actually an overlay.

    bottom_ratio = _bottom_bar_ratio(image)
    if bottom_ratio >= 0.07:
        visual_signals.append("viewport_bottom_bar_pattern")
        coverage = max(coverage, bottom_ratio)
        if obstruction_type == "none":
            obstruction_type = "unknown_overlay"

    present = coverage >= 0.12 or centered_modal >= 0.65 or full_overlay_score >= 0.86
    if bottom_ratio and bottom_ratio < 0.12:
        visual_signals.append("viewport_minor_sticky_footer_pattern")
        present = present or bottom_ratio >= 0.05
        coverage = max(coverage, bottom_ratio)
        if obstruction_type == "none":
            obstruction_type = "unknown_overlay"

    return ViewportObstructionEvidence(
        present=present,
        type=obstruction_type if present else "none",
        coverage_ratio=coverage if present else 0.0,
        confidence=0.0,
        visual_signals=_unique(visual_signals),
        signals=_unique(visual_signals),
        limitations=[],
    )


def _coerce_existing(value: dict[str, Any] | None) -> ViewportObstructionEvidence:
    if not isinstance(value, dict):
        return ViewportObstructionEvidence(present=False)
    return ViewportObstructionEvidence(
        present=bool(value.get("present")),
        type=_valid_type(value.get("type")),
        severity=_valid_severity(value.get("severity")),
        coverage_ratio=_float_or_none(value.get("coverage_ratio")) or 0.0,
        first_impression_valid=bool(value.get("first_impression_valid", True)),
        confidence=_float_or_none(value.get("confidence")) or 0.0,
        page_level_signals=[str(item) for item in value.get("page_level_signals") or []],
        overlay_level_signals=[str(item) for item in value.get("overlay_level_signals") or []],
        visual_signals=[str(item) for item in value.get("visual_signals") or []],
        signals=[str(item) for item in value.get("signals") or []],
        limitations=[str(item) for item in value.get("limitations") or []],
    )


def _dom_coverage(text: str, obstruction_type: str, *, bottom_like: bool, full_like: bool, overlay: bool) -> float:
    if obstruction_type == "login_wall" or full_like:
        return 0.92
    if overlay:
        return 0.55
    if bottom_like:
        height_match = re.search(r"height\s*:\s*(\d+(?:\.\d+)?)(vh|%)", text)
        if height_match:
            value = float(height_match.group(1))
            return min(0.45, max(0.06, value / 100))
        px_match = re.search(r"height\s*:\s*(\d+(?:\.\d+)?)px", text)
        if px_match:
            return min(0.35, max(0.04, float(px_match.group(1)) / 900))
        return 0.18 if obstruction_type == "cookie_banner" else 0.07
    return 0.22


def _centered_modal_score(image: RasterImage) -> float:
    center = _region_stats(image, 0.28, 0.22, 0.72, 0.78)
    outer = _outer_region_stats(image, 0.12)
    if not center or not outer:
        return 0.0
    brightness_gap = center["brightness"] - outer["brightness"]
    outer_dark = outer["dark_ratio"]
    center_light = center["light_ratio"]
    if outer_dark >= 0.45 and brightness_gap >= 35 and center_light >= 0.25:
        return round(min(0.72, 0.45 + outer_dark * 0.25 + min(0.2, brightness_gap / 255)), 3)
    return 0.0


def _fullscreen_overlay_score(image: RasterImage) -> float:
    sample = _sample_pixels(image, limit=8000)
    if not sample:
        return 0.0
    dark_ratio = sum(1 for pixel in sample if _brightness(pixel) <= 38) / len(sample)
    mid_dark_ratio = sum(1 for pixel in sample if _brightness(pixel) <= 75) / len(sample)
    unique_ratio = len(set(sample)) / len(sample)
    if dark_ratio >= 0.88 and unique_ratio <= 0.08:
        return round(dark_ratio, 3)
    if mid_dark_ratio >= 0.92 and unique_ratio <= 0.04:
        return round(min(0.95, mid_dark_ratio), 3)
    return 0.0


def _bottom_bar_ratio(image: RasterImage) -> float:
    if image.height < 10:
        return 0.0
    reference_y = max(0, int(image.height * 0.55))
    reference = _row_average(image, reference_y)
    bottom = _row_average(image, image.height - 1)
    if _distance(reference, bottom) < 20:
        return 0.0

    bar_rows = 0
    for y in range(image.height - 1, -1, -1):
        row = _row_average(image, y)
        if _distance(row, bottom) <= 24:
            bar_rows += 1
            continue
        break
    ratio = bar_rows / image.height
    if 0.05 <= ratio <= 0.4:
        return round(ratio, 3)
    return 0.0


def _region_stats(image: RasterImage, x0: float, y0: float, x1: float, y1: float) -> dict[str, float]:
    left = max(0, min(image.width - 1, int(image.width * x0)))
    right = max(left + 1, min(image.width, int(image.width * x1)))
    top = max(0, min(image.height - 1, int(image.height * y0)))
    bottom = max(top + 1, min(image.height, int(image.height * y1)))
    pixels = []
    x_step = max(1, (right - left) // 80)
    y_step = max(1, (bottom - top) // 60)
    for y in range(top, bottom, y_step):
        offset = y * image.width
        for x in range(left, right, x_step):
            pixels.append(image.pixels[offset + x])
    return _pixel_stats(pixels)


def _outer_region_stats(image: RasterImage, border_ratio: float) -> dict[str, float]:
    border_x = max(1, int(image.width * border_ratio))
    border_y = max(1, int(image.height * border_ratio))
    pixels = []
    x_step = max(1, image.width // 100)
    y_step = max(1, image.height // 80)
    for y in range(0, image.height, y_step):
        offset = y * image.width
        for x in range(0, image.width, x_step):
            if x < border_x or x >= image.width - border_x or y < border_y or y >= image.height - border_y:
                pixels.append(image.pixels[offset + x])
    return _pixel_stats(pixels)


def _pixel_stats(pixels: list[tuple[int, int, int]]) -> dict[str, float]:
    if not pixels:
        return {}
    brightness_values = [_brightness(pixel) for pixel in pixels]
    return {
        "brightness": sum(brightness_values) / len(brightness_values),
        "dark_ratio": sum(1 for value in brightness_values if value <= 70) / len(brightness_values),
        "light_ratio": sum(1 for value in brightness_values if value >= 210) / len(brightness_values),
    }


def _sample_pixels(image: RasterImage, *, limit: int) -> list[tuple[int, int, int]]:
    step = max(1, len(image.pixels) // limit)
    return image.pixels[::step][:limit]


def _row_average(image: RasterImage, y: int) -> tuple[int, int, int]:
    y = max(0, min(image.height - 1, y))
    row = image.pixels[y * image.width:(y + 1) * image.width]
    if not row:
        return (0, 0, 0)
    return tuple(int(sum(pixel[channel] for pixel in row) / len(row)) for channel in range(3))  # type: ignore[return-value]


def _term_hits(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term in text]


def _split_term_signals(text: str, terms: tuple[str, ...], *, signal_prefix: str) -> tuple[list[str], list[str]]:
    page_level_signals: list[str] = []
    overlay_level_signals: list[str] = []
    for term in terms:
        for context in _term_contexts(text, term):
            signal = f"{signal_prefix}:{term}"
            if _context_has_page_level_cues(context):
                page_level_signals.append(signal)
            elif _context_has_overlay_cues(context):
                overlay_level_signals.append(signal)
            else:
                page_level_signals.append(signal)
    return page_level_signals, overlay_level_signals


def _term_contexts(text: str, term: str, *, window: int = 220, limit: int = 3) -> list[str]:
    contexts: list[str] = []
    for match in re.finditer(re.escape(term), text):
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        contexts.append(text[start:end])
        if len(contexts) >= limit:
            break
    return contexts


def _context_has_overlay_cues(context: str) -> bool:
    overlay_pattern = (
        r"modal|dialog|overlay|backdrop|popup|pop-up|popover|aria-modal|role=['\"]?dialog|"
        r"position\s*:\s*fixed|fixed-bottom|bottom-0|inset-0|z-\[?\d{3,}\]?|z-50|sticky"
    )
    return bool(re.search(overlay_pattern, context))


def _context_has_page_level_cues(context: str) -> bool:
    page_pattern = (
        r"<(header|nav|footer)\b|site-header|site-nav|navbar|topbar|masthead|breadcrumb|menu|"
        r"utility-nav|primary-nav|secondary-nav|header__|nav__"
    )
    return bool(re.search(page_pattern, context))


def _choose_type(*values: str) -> ObstructionType:
    priority = {
        "login_wall": 6,
        "cookie_modal": 5,
        "newsletter_modal": 4,
        "promo_modal": 3,
        "cookie_banner": 2,
        "unknown_overlay": 1,
        "none": 0,
    }
    chosen = max((_valid_type(value) for value in values), key=lambda item: priority[item])
    return chosen


def _severity(coverage_ratio: float, obstruction_type: str, present: bool) -> ObstructionSeverity:
    if not present:
        return "none"
    if obstruction_type == "login_wall" or coverage_ratio >= 0.85:
        return "blocking"
    if coverage_ratio >= 0.45:
        return "major"
    if coverage_ratio >= 0.16:
        return "moderate"
    return "minor"


def _confidence(
    *,
    present: bool,
    dom_present: bool,
    viewport_present: bool,
    obstruction_type: str,
    coverage_ratio: float,
    signal_count: int,
) -> float:
    if not present:
        return 0.25 if signal_count else 0.0
    score = 0.35
    if dom_present:
        score += 0.22
    if viewport_present:
        score += 0.22
    if obstruction_type != "unknown_overlay":
        score += 0.12
    if coverage_ratio >= 0.45:
        score += 0.08
    score += min(0.12, signal_count * 0.025)
    return round(max(0.0, min(1.0, score)), 3)


def _brightness(pixel: tuple[int, int, int]) -> float:
    return pixel[0] * 0.2126 + pixel[1] * 0.7152 + pixel[2] * 0.0722


def _distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return sum(abs(left[idx] - right[idx]) for idx in range(3)) / 3


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _valid_type(value: Any) -> ObstructionType:
    text = str(value or "none")
    allowed = {
        "cookie_banner",
        "cookie_modal",
        "newsletter_modal",
        "login_wall",
        "promo_modal",
        "unknown_overlay",
        "none",
    }
    return text if text in allowed else "unknown_overlay"  # type: ignore[return-value]


def _valid_severity(value: Any) -> ObstructionSeverity:
    text = str(value or "none")
    allowed = {"minor", "moderate", "major", "blocking", "none"}
    return text if text in allowed else "none"  # type: ignore[return-value]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
