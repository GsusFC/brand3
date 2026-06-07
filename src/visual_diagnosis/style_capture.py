"""Playwright-backed computed-style snapshot capture for Visual Diagnosis lab."""

from __future__ import annotations

from typing import Any


DEFAULT_SELECTORS = [
    "body",
    "header",
    "nav",
    "main",
    "section",
    "article",
    "h1",
    "h2",
    "h3",
    "p",
    "a",
    "button",
    "[role='button']",
    "[class*='hero' i]",
    "[class*='card' i]",
    "[class*='tile' i]",
    "[class*='cta' i]",
    "[class*='button' i]",
]


COMPUTED_STYLE_EVALUATE_JS = """
({ selectors, maxElements }) => {
  const wantedStyles = [
    'display',
    'position',
    'fontFamily',
    'fontSize',
    'fontWeight',
    'lineHeight',
    'letterSpacing',
    'color',
    'backgroundColor',
    'borderColor',
    'borderRadius',
    'boxShadow',
    'textTransform',
    'gap',
    'padding',
    'margin',
  ];
  const seen = new Set();
  const elements = [];

  const pushNode = (node, selector) => {
    if (!node || seen.has(node) || elements.length >= maxElements) return;
    seen.add(node);
    const style = window.getComputedStyle(node);
    const rect = node.getBoundingClientRect ? node.getBoundingClientRect() : null;
    const styles = {};
    for (const key of wantedStyles) {
      styles[key] = style ? (style[key] || '') : '';
    }
    const className = typeof node.className === 'string' ? node.className : '';
    elements.push({
      tag: node.tagName ? node.tagName.toLowerCase() : '',
      selector,
      role: node.getAttribute ? (node.getAttribute('role') || '') : '',
      className,
      id: node.id || '',
      text: (node.innerText || node.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 120),
      styles,
      box: rect ? {
        x: Math.round(rect.x || rect.left || 0),
        y: Math.round(rect.y || rect.top || 0),
        width: Math.round(rect.width || 0),
        height: Math.round(rect.height || 0),
      } : null,
    });
  };

  for (const selector of selectors) {
    let nodes = [];
    try {
      nodes = Array.from(document.querySelectorAll(selector));
    } catch (_) {
      nodes = [];
    }
    for (const node of nodes) {
      pushNode(node, selector);
    }
  }

  const colors = [];
  for (const element of elements) {
    for (const key of ['color', 'backgroundColor', 'borderColor']) {
      const value = element.styles[key];
      if (value && value !== 'rgba(0, 0, 0, 0)' && value !== 'transparent') {
        colors.push(value);
      }
    }
  }

  return {
    schema_version: 'computed-style-snapshot-v1',
    url: window.location.href,
    title: document.title || '',
    viewport: {
      width: window.innerWidth || 0,
      height: window.innerHeight || 0,
    },
    body: elements.find((item) => item.tag === 'body') || null,
    colors: Array.from(new Set(colors)).slice(0, 16),
    image_count: document.images ? document.images.length : 0,
    link_count: document.links ? document.links.length : 0,
    element_count: elements.length,
    elements,
  };
}
"""


def extract_computed_style_snapshot_from_page(
    page: Any,
    *,
    selectors: list[str] | None = None,
    max_elements: int = 80,
) -> dict[str, Any]:
    """Extract a stable computed-style snapshot from an already-loaded page."""
    selected = selectors or DEFAULT_SELECTORS
    payload = page.evaluate(
        COMPUTED_STYLE_EVALUATE_JS,
        {"selectors": selected, "maxElements": max(1, int(max_elements))},
    )
    return _normalize_snapshot(payload)


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
    if not isinstance(payload, dict):
        return {
            "schema_version": "computed-style-snapshot-v1",
            "interpretation_status": "not_interpretable",
            "elements": [],
            "colors": [],
            "limitations": ["computed_style_snapshot_invalid"],
        }
    payload = dict(payload)
    payload["schema_version"] = str(payload.get("schema_version") or "computed-style-snapshot-v1")
    elements = payload.get("elements")
    payload["elements"] = [item for item in elements if isinstance(item, dict)] if isinstance(elements, list) else []
    colors = payload.get("colors")
    payload["colors"] = [str(item) for item in colors if item] if isinstance(colors, list) else []
    payload["element_count"] = len(payload["elements"])
    return payload
