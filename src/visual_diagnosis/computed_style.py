"""Lab-only computed-style visual evidence adapter.

This adapter turns a local browser style snapshot into the Visual Signature
shape consumed by Visual Diagnosis. It does not navigate, crawl, call providers,
or use an LLM.
"""

from __future__ import annotations

from typing import Any


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
        "dominant_colors": _dedupe(dominant)[:8],
        "accent_candidates": _dedupe(accents)[:4],
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
        "primary_ctas": _dedupe(primary_ctas)[:5],
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
        "layout_patterns": _dedupe(patterns)[:8],
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


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
