"""Visual system observations for Visual Signature evidence packets."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import dict_or_empty as _dict
from src.visual_signature._internal.utils import float_or_none as _float_or_none
from src.visual_signature.evidence_utils import component_types, optional_str, score01, string_list


def visual_system_contract(payload: dict[str, Any]) -> dict[str, Any]:
    colors = _dict(payload.get("colors"))
    typography = _dict(payload.get("typography"))
    layout = _dict(payload.get("layout"))
    components = _dict(payload.get("components"))
    consistency = _dict(payload.get("consistency"))
    semantics = _dict(_dict(payload.get("semantics")).get("data"))
    layout_patterns = string_list(layout.get("layout_patterns"))[:8]
    component_type_list = component_types(components)
    return {
        "palette": {
            "dominant_colors": string_list(colors.get("dominant_colors"))[:8],
            "accent_candidates": string_list(colors.get("accent_candidates"))[:6],
            "palette_complexity": str(colors.get("palette_complexity") or "unknown"),
        },
        "typography": {
            "heading_scale": str(typography.get("heading_scale") or "unknown"),
            "heading_font": optional_str(typography.get("heading_font")),
            "body_font": optional_str(typography.get("body_font")),
        },
        "layout": {
            "has_navigation": bool(layout.get("has_navigation")),
            "has_hero": bool(layout.get("has_hero")),
            "visual_density": str(layout.get("visual_density") or "unknown"),
            "layout_patterns": layout_patterns,
        },
        "components": {
            "primary_ctas": string_list(components.get("primary_ctas"))[:8],
            "component_types": component_type_list,
        },
        "consistency": {
            "overall_consistency": score01(consistency.get("overall_consistency")),
        },
        "synthesis": {
            "visual_tone": _visual_tone(colors, typography, layout),
            "category_fit": _category_fit(layout_patterns, component_type_list),
            "distinctiveness": _distinctiveness_label(payload),
            "semantic_summary": _semantic_text(semantics.get("visual_coherence")) or "",
        },
    }


def first_impression_contract(payload: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    semantics = _dict(payload.get("semantics"))
    semantic_data = _dict(semantics.get("data"))
    polish = _float_or_none(semantic_data.get("visual_polish_score"))
    if polish is not None and polish > 1:
        polish = polish / 10
    summary = _semantic_text(semantic_data.get("first_impression_summary")) or _semantic_text(semantic_data.get("visual_coherence")) or ""
    multimodal_available = _semantics_detected(semantics)
    return {
        "status": "blocked" if capture.get("status") != "usable" else "available",
        "source": "llm_multimodal" if multimodal_available else "heuristic",
        "visual_polish": round(max(0.0, min(1.0, polish)), 3) if polish is not None else None,
        "summary": summary,
        "evidence_refs": ["visual_signature:semantics"] if multimodal_available else ["visual_signature:capture"],
    }


def copy_visual_alignment_contract(payload: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    semantics = _dict(payload.get("semantics"))
    semantic_data = _dict(semantics.get("data"))
    alignment = _semantic_text(semantic_data.get("copy_visual_alignment")) or _semantic_text(semantic_data.get("visual_coherence"))
    multimodal_available = _semantics_detected(semantics)
    status = "blocked" if capture.get("status") != "usable" else "available" if alignment else "unknown"
    return {
        "status": status,
        "source": "llm_multimodal" if multimodal_available and alignment else "heuristic",
        "summary": alignment or "",
        "evidence_refs": ["visual_signature:semantics"] if multimodal_available and alignment else ["visual_signature:layout", "visual_signature:typography"],
    }


def _visual_tone(colors: dict[str, Any], typography: dict[str, Any], layout: dict[str, Any]) -> str:
    density = str(layout.get("visual_density") or "unknown")
    heading_scale = str(typography.get("heading_scale") or "unknown")
    palette_complexity = str(colors.get("palette_complexity") or "unknown")
    if density == "dense" and heading_scale in {"expressive", "strong"}:
        return "editorial"
    if heading_scale in {"expressive", "strong"} and palette_complexity in {"medium", "high"}:
        return "expressive"
    if density in {"balanced", "sparse"}:
        return "functional"
    return "unknown"


def _category_fit(layout_patterns: list[str], component_types: list[str]) -> str:
    patterns = {str(item).lower() for item in layout_patterns}
    components = {str(item).lower() for item in component_types}
    if "pricing" in patterns or "pricing" in components:
        return "saas_or_product"
    if {"card", "cta"} & components and "grid" in patterns:
        return "structured_marketing"
    if "form" in components and "navigation" in components:
        return "workflow_or_service"
    return "unknown"


def _distinctiveness_label(payload: dict[str, Any]) -> str:
    from src.visual_signature.evidence_utils import distinctiveness_proxy

    score = distinctiveness_proxy(payload)
    if score >= 0.72:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _semantic_text(value: Any) -> str | None:
    text = optional_str(value)
    if text is None:
        return None
    normalized = text.strip().lower()
    if normalized in {"not_detected", "unknown", "unavailable"}:
        return None
    return text


def _semantics_detected(semantics: dict[str, Any]) -> bool:
    if not semantics:
        return False
    return str(semantics.get("status") or "") == "detected" and not bool(semantics.get("fallback_used"))
