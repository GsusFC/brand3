"""Candidate extraction helpers for logo normalization."""

from __future__ import annotations

import re

from src.visual_signature.types import LogoCandidate, VisualAcquisitionResult, VisualAssetCandidate


def collect_asset_logo_candidates(
    acquisition: VisualAcquisitionResult,
    *,
    html: str,
    brand_token: str,
    location_from_context,
    is_brand_logo_candidate,
) -> list[LogoCandidate]:
    candidates: list[LogoCandidate] = []
    for image in acquisition.images:
        searchable = f"{image.url} {image.alt or ''}".lower()
        location = location_from_context(html, image.url)
        if is_brand_logo_candidate(
            searchable=searchable,
            brand_token=brand_token,
            location=location,
            role_hint=image.role_hint,
        ):
            candidates.append(candidate_from_asset(image, location))
    return candidates


def collect_html_logo_candidates(
    *,
    html: str,
    brand_token: str,
    location_from_context,
    attr,
    is_brand_logo_candidate,
) -> list[LogoCandidate]:
    candidates: list[LogoCandidate] = []
    for match in re.finditer(r"<img\b[^>]*(?:logo|brandmark|wordmark)[^>]*>", html, re.I):
        tag = match.group(0)
        location = location_from_context(html, tag, match.start())
        searchable = f"{attr(tag, 'src') or ''} {attr(tag, 'alt') or ''}".lower()
        if not is_brand_logo_candidate(
            searchable=searchable,
            brand_token=brand_token,
            location=location,
            role_hint="logo",
        ):
            continue
        candidates.append(
            LogoCandidate(
                url=attr(tag, "src"),
                alt=attr(tag, "alt"),
                location=location,
                source="rendered_html",
                confidence=0.72,
            )
        )
    return candidates


def candidate_from_asset(asset: VisualAssetCandidate, location: str) -> LogoCandidate:
    return LogoCandidate(
        url=asset.url,
        alt=asset.alt,
        location=location,  # type: ignore[arg-type]
        source=asset.source,
        confidence=0.78 if asset.role_hint == "logo" else 0.55,
    )
