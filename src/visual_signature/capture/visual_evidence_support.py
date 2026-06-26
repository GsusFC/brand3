"""Internal helpers for lab visual evidence fusion and screenshot promotion."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none
from src.visual_signature._internal.utils import unique_text as _unique_text


def promote_vision_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision.get("screenshot"), dict) else {}
    viewport_palette = vision.get("viewport_palette") if isinstance(vision.get("viewport_palette"), dict) else {}
    viewport_composition = (
        vision.get("viewport_composition") if isinstance(vision.get("viewport_composition"), dict) else {}
    )
    viewport_confidence = (
        vision.get("viewport_confidence") if isinstance(vision.get("viewport_confidence"), dict) else {}
    )
    if not screenshot.get("available"):
        payload["interpretation_status"] = "not_interpretable"
        payload["extraction_confidence"] = {
            "score": 0.0,
            "level": "low",
            "limitations": ["screenshot_vision_unavailable"],
        }
        return payload

    dominant_colors = [
        str(item.get("hex"))
        for item in viewport_palette.get("dominant_colors") or []
        if isinstance(item, dict) and item.get("hex")
    ]
    density = str(viewport_composition.get("visual_density") or "unknown")
    confidence_score = _bounded_float(viewport_confidence.get("score"), default=0.45)
    existing_assets = payload.get("assets") if isinstance(payload.get("assets"), dict) else {}
    existing_colors = payload.get("colors") if isinstance(payload.get("colors"), dict) else {}
    existing_layout = payload.get("layout") if isinstance(payload.get("layout"), dict) else {}
    existing_consistency = payload.get("consistency") if isinstance(payload.get("consistency"), dict) else {}
    payload["assets"] = {
        **existing_assets,
        "screenshot_available": True,
        "image_count": max(1, int(existing_assets.get("image_count") or 0)),
    }
    payload["colors"] = {
        **existing_colors,
        "dominant_colors": existing_colors.get("dominant_colors") or dominant_colors[:6],
        "accent_candidates": existing_colors.get("accent_candidates") or dominant_colors[6:8],
    }
    payload["layout"] = {
        **existing_layout,
        "visual_density": existing_layout.get("visual_density") or density,
        "layout_patterns": existing_layout.get("layout_patterns") or ["screenshot_vision"],
    }
    payload["consistency"] = {
        **existing_consistency,
        "overall_consistency": existing_consistency.get("overall_consistency")
        or round(max(0.1, min(0.85, confidence_score)), 3),
    }
    payload["extraction_confidence"] = {
        "score": round(max(0.1, min(0.75, confidence_score)), 3),
        "level": "medium" if confidence_score >= 0.55 else "low",
        "limitations": [
            *((payload.get("extraction_confidence") or {}).get("limitations") or []),
            "screenshot_vision_only",
        ],
    }
    return payload


def merge_visual_payloads(*, primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    fused = dict(primary)
    fused["assets"] = merge_dict(primary.get("assets"), secondary.get("assets"))
    fused["layout"] = merge_dict(primary.get("layout"), secondary.get("layout"))
    fused["logo"] = merge_dict(primary.get("logo"), secondary.get("logo"))
    fused["components"] = merge_components(primary.get("components"), secondary.get("components"))
    fused["colors"] = merge_colors(primary.get("colors"), secondary.get("colors"))
    fused["typography"] = merge_dict(primary.get("typography"), secondary.get("typography"))
    fused["consistency"] = merge_consistency(primary.get("consistency"), secondary.get("consistency"))
    fused["semantics"] = merge_dict(primary.get("semantics"), secondary.get("semantics"))
    if isinstance(secondary.get("vision"), dict) and secondary["vision"]:
        fused["vision"] = merge_dict(primary.get("vision"), secondary.get("vision"))
    fused["extraction_confidence"] = merge_confidence(
        primary.get("extraction_confidence"),
        secondary.get("extraction_confidence"),
    )
    return fused


def merge_dict(primary: Any, secondary: Any) -> dict[str, Any]:
    left = primary if isinstance(primary, dict) else {}
    right = secondary if isinstance(secondary, dict) else {}
    return {**right, **left}


def merge_colors(primary: Any, secondary: Any) -> dict[str, Any]:
    left = primary if isinstance(primary, dict) else {}
    right = secondary if isinstance(secondary, dict) else {}
    return {
        **right,
        **left,
        "dominant_colors": _unique_text(
            [*(left.get("dominant_colors") or []), *(right.get("dominant_colors") or [])]
        )[:10],
        "accent_candidates": _unique_text(
            [*(left.get("accent_candidates") or []), *(right.get("accent_candidates") or [])]
        )[:6],
    }


def merge_components(primary: Any, secondary: Any) -> dict[str, Any]:
    left = primary if isinstance(primary, dict) else {}
    right = secondary if isinstance(secondary, dict) else {}
    return {
        **right,
        **left,
        "primary_ctas": _unique_text([*(left.get("primary_ctas") or []), *(right.get("primary_ctas") or [])])[:8],
        "components": merge_component_counts(left.get("components") or [], right.get("components") or []),
    }


def merge_component_counts(left_items: list[Any], right_items: list[Any]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in [*left_items, *right_items]:
        if not isinstance(item, dict):
            continue
        component_type = str(item.get("type") or "").strip().lower()
        if not component_type:
            continue
        try:
            count = int(item.get("count") or 1)
        except (TypeError, ValueError):
            count = 1
        counts[component_type] = max(counts.get(component_type, 0), count)
    return [{"type": key, "count": value} for key, value in sorted(counts.items())]


def merge_consistency(primary: Any, secondary: Any) -> dict[str, Any]:
    merged = merge_dict(primary, secondary)
    scores = [
        _float_or_none((primary or {}).get("overall_consistency")) if isinstance(primary, dict) else None,
        _float_or_none((secondary or {}).get("overall_consistency")) if isinstance(secondary, dict) else None,
    ]
    present = [score for score in scores if score is not None]
    if present:
        merged["overall_consistency"] = round(max(present), 3)
    return merged


def merge_confidence(primary: Any, secondary: Any) -> dict[str, Any]:
    left = primary if isinstance(primary, dict) else {}
    right = secondary if isinstance(secondary, dict) else {}
    score = max(_float_or_none(left.get("score")) or 0.0, _float_or_none(right.get("score")) or 0.0)
    limitations = _unique_text([*(left.get("limitations") or []), *(right.get("limitations") or [])])
    return {
        **right,
        **left,
        "score": round(score, 3),
        "level": "medium" if score >= 0.55 else "low",
        "limitations": limitations,
    }


def bounded_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, parsed))


def _bounded_float(value: Any, *, default: float) -> float:
    return bounded_float(value, default=default)
