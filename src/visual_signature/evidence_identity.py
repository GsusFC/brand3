"""Identity observations for Visual Signature evidence packets."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import dict_or_empty as _dict
from src.visual_signature.evidence_utils import optional_str, score01


def identity_contract(payload: dict[str, Any]) -> dict[str, Any]:
    logo = _dict(payload.get("logo"))
    candidates = logo.get("candidates") if isinstance(logo.get("candidates"), list) else []
    ordered = [logo_candidate(item) for item in candidates if isinstance(item, dict)]
    ordered = sorted(ordered, key=lambda item: item["confidence"], reverse=True)
    return {
        "logo_detected": bool(logo.get("logo_detected")),
        "favicon_detected": bool(logo.get("favicon_detected")),
        "textual_brand_mark_detected": bool(logo.get("textual_brand_mark_detected")),
        "primary_location": str(logo.get("primary_location") or "unknown"),
        "candidates": ordered[:8],
        "confidence": score01(logo.get("confidence")),
    }


def logo_candidate(item: dict[str, Any]) -> dict[str, Any]:
    location = str(item.get("location") or "unknown")
    source = str(item.get("source") or "unknown")
    url = item.get("url")
    role = "real_logo" if location in {"header", "nav"} and url else "favicon" if location == "metadata" else "text_or_unknown"
    return {
        "url": str(url) if url else None,
        "text": optional_str(item.get("text")),
        "alt": optional_str(item.get("alt")),
        "location": location,
        "source": source,
        "role": role,
        "confidence": score01(item.get("confidence")),
        "reason": logo_reason(location, source, role),
    }


def logo_reason(location: str, source: str, role: str) -> str:
    if role == "real_logo":
        return f"logo candidate appears in {location}"
    if role == "favicon":
        return "candidate comes from metadata favicon"
    return f"candidate comes from {source}"
