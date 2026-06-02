"""Map Context.dev benchmark payloads into Brand3 candidate evidence.

This module is a lab-only bridge. It does not mutate EvidenceGraph or
BrandResearchPack; it produces explicit candidates that can be reviewed before
promotion into production contracts.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any

CONTEXTDEV_CANDIDATE_VERSION = "contextdev_candidate_evidence_v0_1"


@dataclass(frozen=True)
class ContextDevEvidenceCandidate:
    candidate_id: str
    candidate_type: str
    supports_channel: str
    text: str
    source_url: str
    provider: str = "contextdev"
    confidence: str = "candidate"
    raw_ref: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"version": CONTEXTDEV_CANDIDATE_VERSION, **asdict(self)}


def build_contextdev_candidates(payload: dict[str, Any]) -> list[ContextDevEvidenceCandidate]:
    """Build reviewable Brand3 candidates from a Context.dev case payload."""

    case = _dict(payload.get("case"))
    outputs = _dict(payload.get("outputs"))
    domain = str(case.get("domain") or "")
    source_url = _source_url(case)
    candidates: list[ContextDevEvidenceCandidate] = []

    candidates.extend(_brand_candidates(_dict(outputs.get("retrieve_brand")), source_url=source_url, domain=domain))
    candidates.extend(_styleguide_candidates(_dict(outputs.get("styleguide")), source_url=source_url, domain=domain))
    candidates.extend(_font_candidates(_dict(outputs.get("fonts")), source_url=source_url, domain=domain))
    candidates.extend(_image_candidates(_dict(outputs.get("images")), source_url=source_url, domain=domain))
    candidates.extend(_screenshot_candidates(_dict(outputs.get("screenshot")), source_url=source_url, domain=domain))
    candidates.extend(_product_candidates(_dict(outputs.get("products")), source_url=source_url, domain=domain))
    return _dedupe_candidates(candidates)


def summarize_contextdev_candidates(candidates: list[ContextDevEvidenceCandidate]) -> dict[str, Any]:
    by_channel: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for candidate in candidates:
        by_channel[candidate.supports_channel] = by_channel.get(candidate.supports_channel, 0) + 1
        by_type[candidate.candidate_type] = by_type.get(candidate.candidate_type, 0) + 1
    return {
        "version": CONTEXTDEV_CANDIDATE_VERSION,
        "candidate_count": len(candidates),
        "by_channel": dict(sorted(by_channel.items())),
        "by_type": dict(sorted(by_type.items())),
        "candidates": [candidate.to_dict() for candidate in candidates],
    }


def _brand_candidates(payload: dict[str, Any], *, source_url: str, domain: str) -> list[ContextDevEvidenceCandidate]:
    if _is_error(payload):
        return []
    brand = _dict(payload.get("brand"))
    candidates = []
    title = str(brand.get("title") or "")
    description = str(brand.get("description") or "")
    slogan = str(brand.get("slogan") or "")
    industries = _dict(brand.get("industries"))
    if title or description:
        candidates.append(
            _candidate(
                "entity_profile",
                "entity_resolution",
                _join_parts([title, description]),
                source_url,
                domain,
                raw_ref="retrieve_brand.brand",
            )
        )
    if slogan:
        candidates.append(_candidate("brand_slogan", "entity_resolution", slogan, source_url, domain, raw_ref="retrieve_brand.brand.slogan"))
    if industries:
        candidates.append(
            _candidate(
                "industry_classification",
                "industry_classification",
                _compact_json(industries),
                source_url,
                domain,
                raw_ref="retrieve_brand.brand.industries",
            )
        )
    return candidates


def _styleguide_candidates(payload: dict[str, Any], *, source_url: str, domain: str) -> list[ContextDevEvidenceCandidate]:
    if _is_error(payload):
        return []
    styleguide = _dict(payload.get("styleguide"))
    colors = _dict(styleguide.get("colors"))
    typography = _dict(styleguide.get("typography"))
    components = _dict(styleguide.get("components"))
    candidates = []
    if colors:
        candidates.append(_candidate("visual_colors", "visual_identity", _compact_json(colors), source_url, domain, raw_ref="styleguide.colors"))
    if typography:
        candidates.append(_candidate("visual_typography", "visual_identity", _compact_json(typography), source_url, domain, raw_ref="styleguide.typography"))
    if components:
        candidates.append(_candidate("visual_components", "visual_identity", _compact_json(components), source_url, domain, raw_ref="styleguide.components"))
    return candidates


def _font_candidates(payload: dict[str, Any], *, source_url: str, domain: str) -> list[ContextDevEvidenceCandidate]:
    if _is_error(payload):
        return []
    fonts = _list(payload.get("fonts"))
    names = [str(item.get("font") or "") for item in fonts if isinstance(item, dict) and item.get("font")]
    if not names:
        return []
    return [_candidate("visual_fonts", "visual_identity", ", ".join(names[:8]), source_url, domain, raw_ref="fonts.fonts")]


def _image_candidates(payload: dict[str, Any], *, source_url: str, domain: str) -> list[ContextDevEvidenceCandidate]:
    if _is_error(payload):
        return []
    images = _extract_images(payload)
    if not images:
        return []
    return [_candidate("visual_images", "visual_evidence", "\n".join(images[:12]), source_url, domain, raw_ref="images")]


def _screenshot_candidates(payload: dict[str, Any], *, source_url: str, domain: str) -> list[ContextDevEvidenceCandidate]:
    if _is_error(payload):
        return []
    screenshot = str(payload.get("screenshot") or "")
    if not screenshot:
        return []
    text = f"{payload.get('screenshotType') or 'screenshot'}: {screenshot}"
    return [_candidate("visual_screenshot", "visual_evidence", text, source_url, domain, raw_ref="screenshot.screenshot")]


def _product_candidates(payload: dict[str, Any], *, source_url: str, domain: str) -> list[ContextDevEvidenceCandidate]:
    if _is_error(payload):
        return []
    candidates = []
    for index, product in enumerate(_list(payload.get("products"))):
        name = str(product.get("name") or "")
        description = str(product.get("description") or "")
        features = ", ".join(str(item) for item in _str_list(product.get("features"))[:6])
        audience = ", ".join(str(item) for item in _str_list(product.get("target_audience"))[:4])
        text = _join_parts([name, description, f"Features: {features}" if features else "", f"Audience: {audience}" if audience else ""])
        if not text:
            continue
        candidates.append(
            _candidate(
                "product_profile",
                "product_extraction",
                text,
                str(product.get("url") or source_url),
                domain,
                raw_ref=f"products.products[{index}]",
            )
        )
    return candidates


def _candidate(candidate_type: str, supports_channel: str, text: str, source_url: str, domain: str, *, raw_ref: str) -> ContextDevEvidenceCandidate:
    cleaned = " ".join(str(text or "").split())
    return ContextDevEvidenceCandidate(
        candidate_id=_candidate_id(candidate_type, supports_channel, cleaned, source_url),
        candidate_type=candidate_type,
        supports_channel=supports_channel,
        text=cleaned,
        source_url=source_url,
        raw_ref=raw_ref,
        notes=[f"contextdev_domain:{domain}"] if domain else [],
    )


def _candidate_id(candidate_type: str, supports_channel: str, text: str, source_url: str) -> str:
    digest = hashlib.sha1(f"{candidate_type}|{supports_channel}|{source_url}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"ctxdev_{digest}"


def _dedupe_candidates(candidates: list[ContextDevEvidenceCandidate]) -> list[ContextDevEvidenceCandidate]:
    seen: set[tuple[str, str, str]] = set()
    result = []
    for candidate in candidates:
        key = (candidate.candidate_type, candidate.supports_channel, candidate.text.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _source_url(case: dict[str, Any]) -> str:
    url = str(case.get("url") or "")
    if url:
        return url
    domain = str(case.get("domain") or "")
    return f"https://{domain}" if domain else ""


def _extract_images(payload: dict[str, Any]) -> list[str]:
    for key in ("images", "image_urls", "urls"):
        value = payload.get(key)
        if isinstance(value, list):
            return [str(item.get("url") if isinstance(item, dict) else item) for item in value if item]
    return []


def _compact_json(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _join_parts(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def _is_error(payload: dict[str, Any]) -> bool:
    return bool(payload.get("status") == "error" or payload.get("error"))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []
