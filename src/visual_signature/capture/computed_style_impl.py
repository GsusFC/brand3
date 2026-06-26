"""Lab-only computed-style visual evidence adapter.

This adapter turns a local browser style snapshot into the Visual Signature
shape consumed by Visual Diagnosis. It does not navigate, crawl, call providers,
or use an LLM.
"""

from __future__ import annotations

from typing import Any

from src.visual_signature.capture.computed_style_mapping_support import body_font_from_snapshot as _body_font_impl
from src.visual_signature.capture.computed_style_mapping_support import colors_from_snapshot as _colors_impl
from src.visual_signature.capture.computed_style_mapping_support import components_from_elements as _components_impl
from src.visual_signature.capture.computed_style_mapping_support import confidence_score_for_snapshot as _confidence_score_impl
from src.visual_signature.capture.computed_style_mapping_support import css_px as _css_px_impl
from src.visual_signature.capture.computed_style_mapping_support import element_style as _style_impl
from src.visual_signature.capture.computed_style_mapping_support import elements_from_snapshot as _elements_impl
from src.visual_signature.capture.computed_style_mapping_support import first_font_family as _first_font_family_impl
from src.visual_signature.capture.computed_style_mapping_support import first_font_size as _first_font_size_impl
from src.visual_signature.capture.computed_style_mapping_support import image_count_from_snapshot as _image_count_impl
from src.visual_signature.capture.computed_style_mapping_support import is_color as _is_color_impl
from src.visual_signature.capture.computed_style_mapping_support import is_interactive_element as _is_interactive_impl
from src.visual_signature.capture.computed_style_mapping_support import layout_from_snapshot as _layout_impl
from src.visual_signature.capture.computed_style_mapping_support import selector_tag as _selector_tag_impl
from src.visual_signature.capture.computed_style_mapping_support import snapshot_to_visual_signature as _snapshot_to_visual_signature_impl
from src.visual_signature.capture.computed_style_mapping_support import typography_from_snapshot as _typography_impl
from src.visual_signature.capture.computed_style_snapshot_support import COMPUTED_STYLE_EVALUATE_JS
from src.visual_signature.capture.computed_style_snapshot_support import DEFAULT_SELECTORS
from src.visual_signature.capture.computed_style_snapshot_support import extract_snapshot_from_page as _extract_snapshot_from_page_impl
from src.visual_signature.capture.computed_style_snapshot_support import normalize_snapshot as _normalize_snapshot_impl


def computed_style_snapshot_to_visual_signature(
    snapshot: dict[str, Any],
    *,
    brand_name: str,
    website_url: str,
) -> dict[str, Any]:
    return _snapshot_to_visual_signature_impl(
        snapshot,
        brand_name=brand_name,
        website_url=website_url,
    )


def _elements(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return _elements_impl(snapshot)


def _colors(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> dict[str, list[str]]:
    return _colors_impl(snapshot, elements)


def _typography(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> dict[str, Any]:
    return _typography_impl(snapshot, elements)


def _components(elements: list[dict[str, Any]]) -> dict[str, Any]:
    return _components_impl(elements)


def _layout(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> dict[str, Any]:
    return _layout_impl(snapshot, elements)


def _confidence_score(
    *,
    has_colors: bool,
    has_typography: bool,
    has_components: bool,
    has_layout: bool,
    element_count: int,
) -> float:
    return _confidence_score_impl(
        has_colors=has_colors,
        has_typography=has_typography,
        has_components=has_components,
        has_layout=has_layout,
        element_count=element_count,
    )


def _style(element: dict[str, Any]) -> dict[str, Any]:
    return _style_impl(element)


def _is_interactive(element: dict[str, Any]) -> bool:
    return _is_interactive_impl(element)


def _first_font_size(elements: list[dict[str, Any]], tag: str) -> float:
    return _first_font_size_impl(elements, tag)


def _first_font_family(elements: list[dict[str, Any]]) -> str | None:
    return _first_font_family_impl(elements)


def _body_font(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> str | None:
    return _body_font_impl(snapshot, elements)


def _image_count(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> int:
    return _image_count_impl(snapshot, elements)


def _selector_tag(selector: str) -> str:
    return _selector_tag_impl(selector)


def _css_px(value: Any) -> float:
    return _css_px_impl(value)


def _is_color(value: str) -> bool:
    return _is_color_impl(value)


def extract_computed_style_snapshot_from_page(
    page: Any,
    *,
    selectors: list[str] | None = None,
    max_elements: int = 80,
) -> dict[str, Any]:
    """Extract a stable computed-style snapshot from an already-loaded page."""
    return _extract_snapshot_from_page_impl(
        page,
        selectors=selectors,
        max_elements=max_elements,
    )


def capture_computed_style_snapshot(
    website_url: str,
    *,
    viewport_width: int = 1440,
    viewport_height: int = 900,
    timeout_ms: int = 45000,
    networkidle_timeout_ms: int = 12000,
    selectors: list[str] | None = None,
    max_elements: int = 80,
) -> dict[str, Any]:
    """Capture a computed-style snapshot with Playwright.

    This is lab tooling. It performs a live browser navigation and returns local
    evidence only; callers decide whether to persist or compare it.
    """
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError(
            "playwright is not installed. Run: ./.venv/bin/python -m pip install playwright && ./.venv/bin/python -m playwright install chromium"
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": viewport_width, "height": viewport_height})
        page = context.new_page()
        try:
            page.goto(website_url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=networkidle_timeout_ms)
            except PlaywrightTimeoutError:
                pass
            snapshot = extract_computed_style_snapshot_from_page(
                page,
                selectors=selectors,
                max_elements=max_elements,
            )
        finally:
            context.close()
            browser.close()
    return snapshot


def _normalize_snapshot(payload: Any) -> dict[str, Any]:
    return _normalize_snapshot_impl(payload)
