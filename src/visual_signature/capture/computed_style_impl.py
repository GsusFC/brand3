"""Lab-only computed-style visual evidence adapter.

This adapter turns a local browser style snapshot into the Visual Signature
shape consumed by Visual Diagnosis. It does not navigate, crawl, call providers,
or use an LLM.
"""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import unique_text as _unique_text


def computed_style_snapshot_to_visual_signature(
    snapshot: dict[str, Any],
    *,
    brand_name: str,
    website_url: str,
) -> dict[str, Any]:
    elements = _elements(snapshot)
    colors = _colors(snapshot, elements)
    typography = _typography(snapshot, elements)
    components = _components(elements)
    layout = _layout(snapshot, elements)
    confidence_score = _confidence_score(
        has_colors=bool(colors["dominant_colors"] or colors["accent_candidates"]),
        has_typography=bool(typography),
        has_components=bool(components["components"] or components["primary_ctas"]),
        has_layout=bool(layout),
        element_count=len(elements),
    )

    return {
        "brand_name": brand_name,
        "website_url": website_url,
        "interpretation_status": "interpretable" if confidence_score > 0 else "not_interpretable",
        "source": "computed_style_visual_lab",
        "assets": {
            "screenshot_available": False,
            "image_count": _image_count(snapshot, elements),
        },
        "layout": layout,
        "logo": {},
        "components": components,
        "colors": colors,
        "typography": typography,
        "consistency": {"overall_consistency": confidence_score},
        "extraction_confidence": {
            "score": confidence_score,
            "level": "medium" if confidence_score >= 0.6 else "low",
            "limitations": ["computed_style_snapshot_only"],
        },
        "semantics": {
            "status": "detected" if confidence_score >= 0.5 else "limited",
            "data": {
                "visual_polish_score": 7 if confidence_score >= 0.65 else 5 if confidence_score > 0 else 0,
                "visual_coherence": "detected" if confidence_score >= 0.5 else "not_detected",
            },
        },
        "vision": {},
        "computed_style": {
            "schema_version": str(snapshot.get("schema_version") or snapshot.get("version") or "unknown"),
            "element_count": len(elements),
            "source_url": str(snapshot.get("url") or snapshot.get("page_url") or website_url),
        },
    }


def _elements(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    raw = snapshot.get("elements")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]

    sampled = snapshot.get("sampled_elements")
    if isinstance(sampled, list):
        return [item for item in sampled if isinstance(item, dict)]

    styles = snapshot.get("styles")
    if isinstance(styles, dict):
        result = []
        for selector, style in styles.items():
            if not isinstance(style, dict):
                continue
            result.append({"selector": selector, "tag": _selector_tag(str(selector)), "styles": style})
        return result
    return []


def _colors(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> dict[str, list[str]]:
    dominant: list[str] = []
    accents: list[str] = []
    for value in snapshot.get("colors") or snapshot.get("palette") or []:
        if isinstance(value, str) and _is_color(value):
            dominant.append(value)
        elif isinstance(value, dict):
            color = value.get("hex") or value.get("value") or value.get("color")
            if color and _is_color(str(color)):
                dominant.append(str(color))

    for element in elements:
        style = _style(element)
        for key in ("backgroundColor", "background-color", "color", "borderColor", "border-color"):
            value = str(style.get(key) or "").strip()
            if value and _is_color(value):
                dominant.append(value)
        if _is_interactive(element):
            for key in ("backgroundColor", "background-color", "color"):
                value = str(style.get(key) or "").strip()
                if value and _is_color(value):
                    accents.append(value)

    return {
        "dominant_colors": _unique_text(dominant)[:8],
        "accent_candidates": _unique_text(accents)[:4],
    }


def _typography(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> dict[str, Any]:
    headings = [
        element
        for element in elements
        if str(element.get("tag") or element.get("selector") or "").lower().startswith(("h1", "h2", "h3"))
    ]
    h1_size = _first_font_size(headings, "h1")
    h2_size = _first_font_size(headings, "h2")
    heading_scale = "moderate"
    if h1_size and h2_size:
        heading_scale = "flat" if h1_size / h2_size < 1.25 else "strong" if h1_size / h2_size >= 1.65 else "moderate"

    heading_font = _first_font_family(headings)
    body_font = _body_font(snapshot, elements)
    result: dict[str, Any] = {"heading_scale": heading_scale}
    if heading_font:
        result["heading_font"] = heading_font
    if body_font:
        result["body_font"] = body_font
    return result


def _components(elements: list[dict[str, Any]]) -> dict[str, Any]:
    cta_count = 0
    card_count = 0
    nav_count = 0
    primary_ctas: list[str] = []
    for element in elements:
        text = str(element.get("text") or element.get("label") or "").strip()
        class_name = str(element.get("className") or element.get("class_name") or "").lower()
        role = str(element.get("role") or "").lower()
        tag = str(element.get("tag") or "").lower()
        selector = str(element.get("selector") or "").lower()
        combined = " ".join([class_name, role, tag, selector, text.lower()])
        if _is_interactive(element):
            cta_count += 1
            if text:
                primary_ctas.append(text[:80])
        if "card" in combined or "tile" in combined:
            card_count += 1
        if tag == "nav" or role == "navigation" or " nav" in f" {combined}":
            nav_count += 1

    components = []
    if cta_count:
        components.append({"type": "cta", "count": cta_count})
    if card_count:
        components.append({"type": "card", "count": card_count})
    if nav_count:
        components.append({"type": "navigation", "count": nav_count})
    return {
        "primary_ctas": _unique_text(primary_ctas)[:5],
        "components": components,
    }


def _layout(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> dict[str, Any]:
    patterns: list[str] = []
    has_navigation = False
    has_hero = False
    for element in elements:
        tag = str(element.get("tag") or "").lower()
        role = str(element.get("role") or "").lower()
        class_name = str(element.get("className") or element.get("class_name") or "").lower()
        selector = str(element.get("selector") or "").lower()
        combined = " ".join([tag, role, class_name, selector])
        style = _style(element)
        display = str(style.get("display") or "").lower()
        if tag == "nav" or role == "navigation" or "nav" in combined:
            has_navigation = True
        if "hero" in combined or tag == "h1":
            has_hero = True
        if display in {"grid", "flex"}:
            patterns.append(display)
        if "card" in combined:
            patterns.append("cards")

    explicit_patterns = snapshot.get("layout_patterns")
    if isinstance(explicit_patterns, list):
        patterns.extend(str(item) for item in explicit_patterns if item)

    density = str(snapshot.get("visual_density") or "").strip().lower()
    if density not in {"sparse", "balanced", "dense"}:
        density = "dense" if len(elements) >= 40 else "balanced" if len(elements) >= 8 else "sparse"
    return {
        "has_navigation": has_navigation,
        "has_hero": has_hero,
        "visual_density": density,
        "layout_patterns": _unique_text(patterns)[:8],
    }


def _confidence_score(
    *,
    has_colors: bool,
    has_typography: bool,
    has_components: bool,
    has_layout: bool,
    element_count: int,
) -> float:
    score = 0.2 if element_count else 0.0
    score += 0.16 if has_colors else 0
    score += 0.16 if has_typography else 0
    score += 0.16 if has_components else 0
    score += 0.16 if has_layout else 0
    score += min(element_count, 12) * 0.01
    return round(min(score, 0.82), 2)


def _style(element: dict[str, Any]) -> dict[str, Any]:
    style = element.get("styles") or element.get("computed_style") or element.get("style") or {}
    return style if isinstance(style, dict) else {}


def _is_interactive(element: dict[str, Any]) -> bool:
    tag = str(element.get("tag") or "").lower()
    role = str(element.get("role") or "").lower()
    class_name = str(element.get("className") or element.get("class_name") or "").lower()
    selector = str(element.get("selector") or "").lower()
    text = str(element.get("text") or "").lower()
    return (
        tag in {"a", "button"}
        or role == "button"
        or "button" in class_name
        or "btn" in class_name
        or "cta" in class_name
        or "button" in selector
        or text in {"get started", "start", "try it", "contact sales", "buy now", "shop now"}
    )


def _first_font_size(elements: list[dict[str, Any]], tag: str) -> float:
    for element in elements:
        if str(element.get("tag") or element.get("selector") or "").lower().startswith(tag):
            value = _css_px(_style(element).get("fontSize") or _style(element).get("font-size"))
            if value:
                return value
    return 0.0


def _first_font_family(elements: list[dict[str, Any]]) -> str | None:
    for element in elements:
        value = _style(element).get("fontFamily") or _style(element).get("font-family")
        if value:
            return str(value)
    return None


def _body_font(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> str | None:
    body = snapshot.get("body")
    if isinstance(body, dict):
        style = body.get("styles") if isinstance(body.get("styles"), dict) else body
        value = style.get("fontFamily") or style.get("font-family")
        if value:
            return str(value)
    for element in elements:
        selector = str(element.get("selector") or "").lower()
        tag = str(element.get("tag") or "").lower()
        if selector == "body" or tag == "body" or tag == "p":
            value = _style(element).get("fontFamily") or _style(element).get("font-family")
            if value:
                return str(value)
    return None


def _image_count(snapshot: dict[str, Any], elements: list[dict[str, Any]]) -> int:
    explicit = snapshot.get("image_count")
    try:
        if explicit is not None:
            return max(0, int(explicit))
    except (TypeError, ValueError):
        pass
    return sum(1 for element in elements if str(element.get("tag") or "").lower() in {"img", "picture"})


def _selector_tag(selector: str) -> str:
    normalized = selector.strip().lower()
    for tag in ("body", "header", "nav", "main", "section", "h1", "h2", "h3", "p", "a", "button", "img"):
        if normalized == tag or normalized.startswith(f"{tag}.") or normalized.startswith(f"{tag}#"):
            return tag
    return ""


def _css_px(value: Any) -> float:
    text = str(value or "").strip().lower().removesuffix("px")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _is_color(value: str) -> bool:
    text = value.strip().lower()
    return text.startswith("#") or text.startswith("rgb(") or text.startswith("rgba(")


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
