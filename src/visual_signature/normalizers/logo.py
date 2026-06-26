"""Normalize logo and brand mark signals from rendered behavior."""

from __future__ import annotations

import re

from src.visual_signature._internal.utils import unique_by_key as _unique_by_key
from src.visual_signature.normalizers.logo_candidates import (
    collect_asset_logo_candidates,
    collect_html_logo_candidates,
)
from src.visual_signature.normalizers.logo_context import (
    attr as _attr,
    has_textual_brand_mark as _has_textual_brand_mark,
    location_from_context as _location_from_context,
    metadata_icon_url as _metadata_icon_url,
)
from src.visual_signature.types import LogoCandidate, NormalizedLogoSignals, VisualAcquisitionResult
from src.visual_signature._internal.utils import clamp_01 as _clamp


def normalize_logo_signals(acquisition: VisualAcquisitionResult, brand_name: str) -> NormalizedLogoSignals:
    html = "\n".join([acquisition.rendered_html or "", acquisition.raw_html or ""])
    brand_token = _normalize_token(brand_name)
    candidates: list[LogoCandidate] = []
    candidates.extend(
        collect_asset_logo_candidates(
            acquisition,
            html=html,
            brand_token=brand_token,
            location_from_context=_location_from_context,
            is_brand_logo_candidate=_is_brand_logo_candidate,
        )
    )
    candidates.extend(
        collect_html_logo_candidates(
            html=html,
            brand_token=brand_token,
            location_from_context=_location_from_context,
            attr=_attr,
            is_brand_logo_candidate=_is_brand_logo_candidate,
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

    textual_brand_mark = _has_textual_brand_mark(
        html=html,
        metadata=acquisition.metadata,
        brand_name=brand_name,
        normalize_token=_normalize_token,
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

    unique = _unique_by_key(candidates, lambda candidate: candidate.url or candidate.text or candidate.alt or "")
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
def _is_brand_logo_candidate(
    *,
    searchable: str,
    brand_token: str,
    location: str,
    role_hint: str,
) -> bool:
    normalized = _normalize_token(searchable)
    brand_match = bool(brand_token and brand_token in normalized)
    primary_region = location in {"header", "nav", "footer", "metadata"}
    if brand_match:
        return True
    if role_hint == "logo" and primary_region:
        return True
    if "logo" in searchable and primary_region:
        return True
    return False
def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())
