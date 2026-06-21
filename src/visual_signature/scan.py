"""Visual Signature scanner contract.

This module promotes the existing Visual Signature payload into a stable,
scanner-shaped result: score, dimensions, evidence, limitations, and raw refs.
It does not modify Brand3 global scoring.
"""

from __future__ import annotations

from typing import Any

from src.visual_signature.extract_visual_signature import extract_visual_signature
from src.visual_signature.vision.enrich_visual_signature import enrich_visual_signature_with_vision
from src.visual_signature._internal.utils import int_or_none as _int_or_none, unique as _unique
from src.visual_signature.versions import VISUAL_SIGNATURE_SCAN_VERSION


def run_visual_signature_scan(
    *,
    brand_name: str,
    website_url: str,
    web_data: Any | None = None,
    content_web: Any | None = None,
    screenshot_payload: dict[str, Any] | None = None,
    adapter: Any | None = None,
    extractor=extract_visual_signature,
    vision_enricher=enrich_visual_signature_with_vision,
) -> dict[str, Any]:
    """Run Visual Signature and return the scanner contract."""

    payload = extractor(
        brand_name=brand_name,
        website_url=website_url,
        web_data=web_data,
        content_web=content_web,
        screenshot_payload=screenshot_payload,
        adapter=adapter,
    )
    if screenshot_payload:
        payload = vision_enricher(
            visual_signature_payload=payload,
            screenshot_path=str(screenshot_payload.get("path") or "") or None,
            screenshot_payload=screenshot_payload,
        )
    return build_visual_signature_scan(payload)

def build_visual_signature_scan(visual_signature_payload: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic visual scanner result from a Visual Signature payload."""

    payload = visual_signature_payload if isinstance(visual_signature_payload, dict) else {}
    capture = _capture_summary(payload)
    dimensions = _dimension_scores(payload, capture)
    score = _weighted_score(dimensions)
    evidence = _evidence_items(payload, capture, dimensions)
    limitations = _limitations(payload, capture)
    status = _status(payload, capture, score)
    return {
        "schema_version": VISUAL_SIGNATURE_SCAN_VERSION,
        "brand_name": str(payload.get("brand_name") or ""),
        "website_url": str(payload.get("website_url") or ""),
        "analyzed_url": str(payload.get("analyzed_url") or payload.get("website_url") or ""),
        "status": status,
        "score": score,
        "score_label": _score_label(score),
        "dimensions": dimensions,
        "capture": capture,
        "evidence": evidence,
        "limitations": limitations,
        "raw_refs": ["raw_inputs:visual_signature"],
    }

def _capture_summary(payload: dict[str, Any]) -> dict[str, Any]:
    vision = _dict(payload.get("vision"))
    vision_screenshot = _dict(vision.get("screenshot"))
    acquisition = _dict(payload.get("acquisition"))
    obstruction = _canonical_obstruction(
        _dict(vision.get("viewport_obstruction")) or _dict(acquisition.get("viewport_obstruction"))
    )
    screenshot_available = bool(vision_screenshot.get("available"))
    if not screenshot_available:
        assets = _dict(payload.get("assets"))
        screenshot_available = bool(assets.get("screenshot_available"))
    quality = str(vision_screenshot.get("quality") or ("usable" if screenshot_available else "missing"))
    capture_type = str(vision_screenshot.get("capture_type") or "unknown")
    return {
        "available": screenshot_available,
        "type": capture_type,
        "quality": quality,
        "path": str(vision_screenshot.get("path") or ""),
        "page_url": str(vision_screenshot.get("page_url") or payload.get("website_url") or ""),
        "width": _int_or_none(vision_screenshot.get("width")),
        "height": _int_or_none(vision_screenshot.get("height")),
        "obstruction": obstruction,
    }

def _dimension_scores(payload: dict[str, Any], capture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    extraction = _dict(payload.get("extraction_confidence"))
    logo = _dict(payload.get("logo"))
    consistency = _dict(payload.get("consistency"))
    assets = _dict(payload.get("assets"))
    vision = _dict(payload.get("vision"))
    viewport_confidence = _dict(vision.get("viewport_confidence"))
    semantics = _dict(payload.get("semantics"))
    semantic_data = _dict(semantics.get("data"))

    capture_quality = _clamp100(
        _score01(extraction.get("score")) * 35
        + _score01(viewport_confidence.get("score")) * 45
        + (20 if capture.get("available") else 0)
        - _obstruction_penalty(capture)
    )
    identity_clarity = _clamp100(
        (38 if logo.get("logo_detected") else 0)
        + _score01(logo.get("confidence")) * 42
        + (10 if logo.get("primary_location") in {"header", "nav"} else 0)
        + (10 if logo.get("favicon_detected") else 0)
    )
    system_consistency = _clamp100(_score01(consistency.get("overall_consistency")) * 100)
    distinctiveness = _distinctiveness_score(payload, assets)
    brand_fit = _brand_fit_score(semantics, semantic_data, consistency)
    return {
        "capture_quality": _dimension("capture_quality", capture_quality, "Visual capture quality and evaluability."),
        "identity_clarity": _dimension("identity_clarity", identity_clarity, "Logo and brand-mark clarity."),
        "system_consistency": _dimension("system_consistency", system_consistency, "Color, type, component and asset consistency."),
        "visual_distinctiveness": _dimension("visual_distinctiveness", distinctiveness, "How specific and non-generic the visual surface appears."),
        "brand_fit": _dimension("brand_fit", brand_fit, "Alignment between visible design and brand promise/category."),
    }

def _dimension(key: str, score: float, rationale: str) -> dict[str, Any]:
    return {"key": key, "score": round(score, 1), "label": _score_label(score), "rationale": rationale}

def _weighted_score(dimensions: dict[str, dict[str, Any]]) -> float:
    weights = {
        "capture_quality": 0.2,
        "identity_clarity": 0.22,
        "system_consistency": 0.22,
        "visual_distinctiveness": 0.18,
        "brand_fit": 0.18,
    }
    total = sum(float(dimensions[key]["score"]) * weight for key, weight in weights.items())
    return round(_clamp100(total), 1)

def _evidence_items(
    payload: dict[str, Any],
    capture: dict[str, Any],
    dimensions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if capture.get("available"):
        items.append(_evidence("capture", "Viewport screenshot available for visual evaluation.", "positive"))
    obstruction = _dict(capture.get("obstruction"))
    if obstruction.get("present"):
        items.append(
            _evidence(
                "obstruction",
                f"First viewport is affected by {obstruction.get('type') or 'an obstruction'}.",
                "negative" if obstruction.get("severity") in {"major", "blocking"} else "neutral",
            )
        )
    logo = _dict(payload.get("logo"))
    if logo.get("logo_detected"):
        items.append(_evidence("identity", "Brand mark evidence was detected.", "positive"))
    else:
        items.append(_evidence("identity", "No reliable brand mark was detected.", "negative"))
    colors = _dict(payload.get("colors"))
    palette = colors.get("dominant_colors") if isinstance(colors.get("dominant_colors"), list) else []
    if palette:
        items.append(_evidence("palette", f"Dominant palette detected: {', '.join(str(item) for item in palette[:5])}.", "neutral"))
    typography = _dict(payload.get("typography"))
    if typography.get("heading_scale") and typography.get("heading_scale") != "unknown":
        items.append(_evidence("typography", f"Heading scale reads as {typography.get('heading_scale')}.", "neutral"))
    semantics = _dict(payload.get("semantics"))
    semantic_data = _dict(semantics.get("data"))
    if semantic_data.get("visual_polish_score") is not None:
        items.append(
            _evidence(
                "semantics",
                f"Visual polish model score: {semantic_data.get('visual_polish_score')}/10.",
                "positive",
            )
        )
    weakest = min(dimensions.values(), key=lambda item: float(item["score"]))
    if float(weakest["score"]) < 55:
        items.append(_evidence(weakest["key"], f"Weakest visual dimension: {weakest['key']} at {weakest['score']}.", "negative"))
    return items[:8]

def _evidence(key: str, text: str, polarity: str) -> dict[str, Any]:
    return {"key": key, "text": text, "polarity": polarity, "source": "visual_signature"}

def _limitations(payload: dict[str, Any], capture: dict[str, Any]) -> list[str]:
    limitations: list[str] = []
    extraction = _dict(payload.get("extraction_confidence"))
    for item in extraction.get("limitations") or []:
        if item == "screenshot_not_available" and capture.get("available"):
            continue
        limitations.append(str(item))
    if not capture.get("available"):
        limitations.append("screenshot_not_available")
    obstruction = _dict(capture.get("obstruction"))
    if obstruction.get("present") and obstruction.get("first_impression_valid") is False:
        limitations.append("first_viewport_obstructed")
    if _dict(payload.get("semantics")).get("fallback_used"):
        limitations.append("semantic_visual_model_fallback")
    return _unique(limitations)

def _status(payload: dict[str, Any], capture: dict[str, Any], score: float) -> str:
    if payload.get("interpretation_status") == "not_interpretable":
        return "not_evaluable"
    if not capture.get("available"):
        return "partial"
    obstruction = _dict(capture.get("obstruction"))
    if obstruction.get("present") and obstruction.get("severity") == "blocking":
        return "review_required"
    if score < 45:
        return "weak"
    return "ready"

def _canonical_obstruction(obstruction: dict[str, Any]) -> dict[str, Any]:
    if not obstruction:
        return {"present": False, "type": "none", "severity": "none", "first_impression_valid": True}
    signals = [str(item) for item in obstruction.get("signals") or []]
    joined = " ".join(signals + [str(obstruction.get("type") or "")]).lower()
    kind = str(obstruction.get("type") or "unknown")
    if "cookie" in joined or "privacy" in joined:
        kind = "cookie_banner"
    elif "chat" in joined:
        kind = "chat_widget"
    severity = str(obstruction.get("severity") or "unknown")
    return {
        "present": bool(obstruction.get("present")),
        "type": kind,
        "severity": severity,
        "coverage_ratio": _float_or_none(obstruction.get("coverage_ratio")),
        "first_impression_valid": bool(obstruction.get("first_impression_valid", True)),
        "confidence": _float_or_none(obstruction.get("confidence")),
        "signals": signals[:12],
    }

def _obstruction_penalty(capture: dict[str, Any]) -> float:
    obstruction = _dict(capture.get("obstruction"))
    if not obstruction.get("present"):
        return 0.0
    severity = obstruction.get("severity")
    if severity == "blocking":
        return 22.0
    if severity == "major":
        return 16.0
    if severity == "moderate":
        return 10.0
    return 5.0

def _distinctiveness_score(payload: dict[str, Any], assets: dict[str, Any]) -> float:
    colors = _dict(payload.get("colors"))
    typography = _dict(payload.get("typography"))
    components = _dict(payload.get("components"))
    score = 42.0
    if colors.get("palette_complexity") == "high":
        score += 12
    elif colors.get("palette_complexity") == "medium":
        score += 8
    if typography.get("heading_scale") == "expressive":
        score += 14
    elif typography.get("heading_scale") == "moderate":
        score += 8
    if int(assets.get("video_count") or 0) > 0:
        score += 6
    if int(assets.get("background_image_count") or 0) > 0:
        score += 6
    primary_ctas = components.get("primary_ctas") if isinstance(components.get("primary_ctas"), list) else []
    if primary_ctas:
        score += 5
    return _clamp100(score)

def _brand_fit_score(semantics: dict[str, Any], semantic_data: dict[str, Any], consistency: dict[str, Any]) -> float:
    polish = semantic_data.get("visual_polish_score")
    if polish is not None:
        try:
            return _clamp100(float(polish) * 10)
        except (TypeError, ValueError):
            pass
    if semantics.get("status") == "unavailable":
        return _clamp100(45 + _score01(consistency.get("overall_consistency")) * 35)
    return _clamp100(50 + _score01(consistency.get("overall_consistency")) * 40)

def _score_label(score: float) -> str:
    if score >= 80:
        return "strong"
    if score >= 65:
        return "good"
    if score >= 45:
        return "mixed"
    return "weak"

def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

def _score01(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))

def _float_or_none(value: Any) -> float | None:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None

def _clamp100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))

