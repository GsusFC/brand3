"""Identity observations for Visual Signature evidence packets."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import dict_or_empty as _dict
from src.visual_signature.evidence_utils import optional_str, score01


def identity_contract(payload: dict[str, Any]) -> dict[str, Any]:
    logo = _dict(payload.get("logo"))
    candidates = logo.get("candidates") if isinstance(logo.get("candidates"), list) else []
    ordered = [logo_candidate(item) for item in candidates if isinstance(item, dict)]
    ordered = sorted(
        ordered,
        key=lambda item: (_role_priority(item["role"]), _location_priority(item["location"]), item["confidence"]),
        reverse=True,
    )
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
    url = optional_str(item.get("url"))
    text = optional_str(item.get("text"))
    alt = optional_str(item.get("alt"))
    role = _candidate_role(location=location, source=source, url=url, text=text, alt=alt)
    return {
        "url": url,
        "text": text,
        "alt": alt,
        "location": location,
        "source": source,
        "role": role,
        "confidence": score01(item.get("confidence")),
        "reason": logo_reason(location=location, source=source, role=role, url=url, text=text, alt=alt),
    }


def logo_reason(*, location: str, source: str, role: str, url: str | None, text: str | None, alt: str | None) -> str:
    if role == "real_logo":
        return f"candidate appears in {location} with visual logo evidence"
    if role == "favicon":
        return "candidate comes from metadata favicon"
    if role == "text_brand_mark":
        return f"brand text appears in {location}"
    if role == "generic_icon":
        return f"candidate looks like a generic icon from {source}"
    detail = []
    if alt:
        detail.append(f"alt:{alt}")
    if text:
        detail.append(f"text:{text}")
    if url:
        detail.append("url_present")
    suffix = f" ({', '.join(detail[:2])})" if detail else ""
    return f"candidate comes from {source}{suffix}"


def _candidate_role(*, location: str, source: str, url: str | None, text: str | None, alt: str | None) -> str:
    searchable = f"{url or ''} {alt or ''} {text or ''}".lower()
    if location == "metadata":
        return "favicon"
    if text and not url:
        return "text_brand_mark"
    if location in {"header", "nav"} and url:
        if any(token in searchable for token in ("favicon", "apple-touch-icon", "icon-")):
            return "generic_icon"
        return "real_logo"
    if url and any(token in searchable for token in ("favicon", "apple-touch-icon", "icon-")):
        return "generic_icon"
    return "text_or_unknown"


def _role_priority(role: str) -> int:
    return {
        "real_logo": 4,
        "text_brand_mark": 3,
        "favicon": 2,
        "generic_icon": 1,
        "text_or_unknown": 0,
    }.get(role, 0)


def _location_priority(location: str) -> int:
    return {
        "header": 5,
        "nav": 4,
        "body": 3,
        "footer": 2,
        "metadata": 1,
        "unknown": 0,
    }.get(location, 0)
