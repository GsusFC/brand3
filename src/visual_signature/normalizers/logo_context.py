"""Context helpers for logo normalization."""

from __future__ import annotations

import re


def location_from_context(html: str, needle: str, index: int | None = None) -> str:
    position = index if index is not None else html.find(needle)
    if position < 0:
        return "unknown"
    structural_location = open_structural_region(html, position)
    if structural_location != "unknown":
        return structural_location
    context = html[max(0, position - 1000): position + 1000].lower()
    if "<header" in context:
        return "header"
    if "<nav" in context or "navbar" in context:
        return "nav"
    if "<footer" in context:
        return "footer"
    if "<main" in context:
        return "body"
    return "unknown"


def open_structural_region(html: str, position: int) -> str:
    before = html[:position].lower()
    candidates: list[tuple[int, str]] = []
    for tag, location in (("header", "header"), ("nav", "nav"), ("main", "body"), ("footer", "footer")):
        opened = before.rfind(f"<{tag}")
        closed = before.rfind(f"</{tag}>")
        if opened > closed:
            candidates.append((opened, location))
    if not candidates:
        return "unknown"
    return max(candidates, key=lambda item: item[0])[1]


def attr(tag: str, name: str) -> str | None:
    match = re.search(rf"{name}\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
    return match.group(1).strip() if match else None


def metadata_icon_url(metadata: dict) -> str | None:
    for key in ("favicon", "faviconUrl", "icon", "ogImage", "image"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def has_textual_brand_mark(html: str, metadata: dict, brand_name: str, *, normalize_token) -> bool:
    if not brand_name:
        return False
    if re.search(
        rf"<(?:a|span|div|strong)[^>]*>\s*{re.escape(brand_name)}\s*<",
        html,
        re.I,
    ):
        return True
    brand_token = normalize_token(brand_name)
    for key in ("site_name", "og_site_name", "og:site_name", "title"):
        if brand_token and brand_token in normalize_token(str(metadata.get(key) or "")):
            return True
    meta_match = re.search(
        r"<meta\b[^>]*(?:property|name)=['\"]og:site_name['\"][^>]*content=['\"]([^'\"]+)['\"]",
        html,
        re.I,
    )
    return bool(meta_match and brand_token and brand_token in normalize_token(meta_match.group(1)))
