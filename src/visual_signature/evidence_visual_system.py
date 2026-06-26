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
            "layout_patterns": string_list(layout.get("layout_patterns"))[:8],
        },
        "components": {
            "primary_ctas": string_list(components.get("primary_ctas"))[:8],
            "component_types": component_types(components),
        },
        "consistency": {
            "overall_consistency": score01(consistency.get("overall_consistency")),
        },
    }


def first_impression_contract(payload: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    semantic_data = _dict(_dict(payload.get("semantics")).get("data"))
    polish = _float_or_none(semantic_data.get("visual_polish_score"))
    if polish is not None and polish > 1:
        polish = polish / 10
    return {
        "status": "blocked" if capture.get("status") != "usable" else "available",
        "source": "llm_multimodal" if semantic_data else "heuristic",
        "visual_polish": round(max(0.0, min(1.0, polish)), 3) if polish is not None else None,
        "summary": optional_str(semantic_data.get("visual_coherence")) or "",
        "evidence_refs": ["visual_signature:semantics"] if semantic_data else ["visual_signature:capture"],
    }


def copy_visual_alignment_contract(payload: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    semantic_data = _dict(_dict(payload.get("semantics")).get("data"))
    coherence = semantic_data.get("visual_coherence")
    status = "blocked" if capture.get("status") != "usable" else "available" if coherence else "unknown"
    return {
        "status": status,
        "source": "llm_multimodal" if coherence else "heuristic",
        "summary": optional_str(coherence) or "",
        "evidence_refs": ["visual_signature:semantics"] if coherence else ["visual_signature:layout", "visual_signature:typography"],
    }
