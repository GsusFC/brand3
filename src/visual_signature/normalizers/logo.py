"""Normalize logo and brand mark signals from rendered behavior."""

from __future__ import annotations

import re

from src.visual_signature.types import LogoCandidate, NormalizedLogoSignals, VisualAcquisitionResult, VisualAssetCandidate


def normalize_logo_signals(acquisition: VisualAcquisitionResult, brand_name: str) -> NormalizedLogoSignals:
    html = "\n".join([acquisition.rendered_html or "", acquisition.raw_html or ""])
    candidates: list[LogoCandidate] = []
    brand_token = _normalize_token(brand_name)

    for image in acquisition.images:
        searchable = f"{image.url} {image.alt or ''}".lower()
        if image.role_hint == "logo" or "logo" in searchable or (brand_token and brand_token in _normalize_token(searchable)):
            candidates.append(_candidate_from_asset(image, _location_from_context(html, image.url)))

    for match in re.finditer(r"<img\b[^>]*(?:logo|brandmark|wordmark)[^>]*>", html, re.I):
        tag = match.group(0)
        candidates.append(
            LogoCandidate(
                url=_attr(tag, "src"),
                alt=_attr(tag, "alt"),
                location=_location_from_context(html, tag, match.start()),
                source="rendered_html",
                confidence=0.72,
            )
        )

    metadata_icon = _metadata_icon_url(acquisition.metadata)
    if metadata_icon:
        candidates.append(
            LogoCandidate(
                url=metadata_icon,
                location="metadata",
                source="metadata",
                confidence=0.45,
            )
        )

    textual_brand_mark = bool(
        brand_name
        and re.search(
            rf"<(?:a|span|div|strong)[^>]*>\s*{re.escape(brand_name)}\s*<",
            html,
            re.I,
        )
    )
    if textual_brand_mark:
        candidates.append(
            LogoCandidate(
                text=brand_name,
                location=_location_from_context(html, brand_name),
                source="rendered_html",
                confidence=0.55,
            )
        )

    unique = _dedupe(candidates)
    unique.sort(key=lambda item: item.confidence, reverse=True)
    favicon_detected = bool(metadata_icon or re.search(r"rel=[\"'](?:shortcut )?icon[\"']", html, re.I))
    confidence = _clamp(
        (0.35 if unique else 0)
        + (0.25 if any(item.location in {"header", "nav"} for item in unique) else 0)
        + (0.15 if favicon_detected else 0)
        + (0.15 if textual_brand_mark else 0)
    )
    return NormalizedLogoSignals(
        logo_detected=any(item.confidence >= 0.55 for item in unique),
        candidates=unique[:8],
        favicon_detected=favicon_detected,
        textual_brand_mark_detected=textual_brand_mark,
        primary_location=unique[0].location if unique else "unknown",
        confidence=confidence,
    )


def _candidate_from_asset(asset: VisualAssetCandidate, location: str) -> LogoCandidate:
    return LogoCandidate(
        url=asset.url,
        alt=asset.alt,
        location=location,  # type: ignore[arg-type]
        source=asset.source,
        confidence=0.78 if asset.role_hint == "logo" else 0.55,
    )


def _location_from_context(html: str, needle: str, index: int | None = None) -> str:
    position = index if index is not None else html.find(needle)
    if position < 0:
        return "unknown"
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


def _attr(tag: str, name: str) -> str | None:
    match = re.search(rf"{name}\s*=\s*[\"']([^\"']+)[\"']", tag, re.I)
    return match.group(1).strip() if match else None


def _metadata_icon_url(metadata: dict) -> str | None:
    for key in ("favicon", "faviconUrl", "icon", "ogImage", "image"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _dedupe(candidates: list[LogoCandidate]) -> list[LogoCandidate]:
    seen: set[str] = set()
    result: list[LogoCandidate] = []
    for candidate in candidates:
        key = candidate.url or candidate.text or candidate.alt or ""
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))
