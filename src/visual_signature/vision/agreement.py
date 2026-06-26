"""DOM and viewport agreement heuristics for Visual Signature vision evidence."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none


def compare_dom_and_viewport(
    visual_signature_payload: dict[str, Any],
    full_composition: Any,
    viewport_composition: Any,
    full_palette: Any,
    viewport_palette: Any,
) -> dict[str, Any]:
    dom_layout = visual_signature_payload.get("layout") or {}
    dom_density = str(dom_layout.get("visual_density") or "unknown")
    dom_consistency = _float_or_none((visual_signature_payload.get("consistency") or {}).get("overall_consistency"))
    dom_palette_complexity = _palette_complexity(visual_signature_payload.get("colors") or {})
    viewport_palette_complexity = _palette_complexity_from_vision(viewport_palette)
    agreement_level = "high"
    disagreement_flags: list[str] = []
    summary_notes: list[str] = []
    typed_agreement = {
        "structural": {"score": 1.0, "flags": []},
        "density": {"score": 1.0, "flags": []},
        "composition": {"score": 1.0, "flags": []},
        "palette": {"score": 1.0, "flags": []},
    }

    if dom_density == "dense" and viewport_composition.visual_density in {"sparse", "balanced"}:
        _add_disagreement(typed_agreement, "density", "dom_density_higher_than_viewport", 0.45)
        disagreement_flags.append("dom_density_higher_than_viewport")
        summary_notes.append("DOM suggests a denser page than the viewport first impression.")
    elif dom_density == "sparse" and viewport_composition.visual_density == "dense":
        _add_disagreement(typed_agreement, "density", "viewport_density_higher_than_dom", 0.45)
        disagreement_flags.append("viewport_density_higher_than_dom")
        summary_notes.append("Viewport looks denser than the DOM summary suggests.")

    if dom_palette_complexity - viewport_palette_complexity >= 0.25:
        _add_disagreement(typed_agreement, "palette", "dom_palette_more_complex_than_viewport", 0.5)
        disagreement_flags.append("dom_palette_more_complex_than_viewport")
        summary_notes.append("DOM palette is noisier than the viewport palette.")
    elif viewport_palette_complexity - dom_palette_complexity >= 0.25:
        _add_disagreement(typed_agreement, "palette", "viewport_palette_more_complex_than_dom", 0.5)
        disagreement_flags.append("viewport_palette_more_complex_than_dom")
        summary_notes.append("Viewport palette is noisier than the DOM palette.")

    viewport_whitespace = _float_or_none(viewport_composition.whitespace_ratio)
    dom_density_rank = _density_rank(dom_density)
    viewport_density_rank = _density_rank(getattr(viewport_composition, "visual_density", "unknown"))
    if dom_density_rank >= 2 and viewport_density_rank <= 1:
        _add_disagreement(typed_agreement, "density", "dom_density_disagrees_with_viewport_first_fold", 0.35)
        disagreement_flags.append("dom_density_disagrees_with_viewport_first_fold")
        summary_notes.append("DOM suggests a denser page, but the viewport reads as spacious.")
    elif dom_density_rank <= 0 and viewport_density_rank >= 2:
        _add_disagreement(typed_agreement, "density", "viewport_density_disagrees_with_dom", 0.35)
        disagreement_flags.append("viewport_density_disagrees_with_dom")
        summary_notes.append("Viewport reads denser than the DOM summary suggests.")

    dom_has_structure = bool(dom_layout.get("has_header") or dom_layout.get("has_navigation") or dom_layout.get("has_hero"))
    viewport_class = str(getattr(viewport_composition, "composition_classification", "unknown") or "unknown")
    if dom_has_structure and viewport_class == "blank":
        _add_disagreement(typed_agreement, "structural", "viewport_blank_despite_dom_structure", 0.85)
        disagreement_flags.append("viewport_blank_despite_dom_structure")
        summary_notes.append("DOM exposes page structure, but the captured viewport appears blank.")
    elif dom_layout.get("has_hero") and viewport_class == "dense_grid":
        _add_disagreement(typed_agreement, "composition", "hero_dom_but_dense_viewport", 0.4)
        disagreement_flags.append("hero_dom_but_dense_viewport")
        summary_notes.append("DOM suggests a hero-led page, while the viewport reads as a dense grid.")

    if dom_consistency is not None and viewport_whitespace is not None:
        if dom_consistency >= 0.7 and viewport_whitespace >= 0.7:
            summary_notes.append("DOM consistency and viewport whitespace both support a sparse, calm first impression.")
        elif dom_consistency >= 0.7 and viewport_whitespace <= 0.25:
            _add_disagreement(typed_agreement, "composition", "dom_consistency_conflicts_with_viewport_density", 0.35)
            disagreement_flags.append("dom_consistency_conflicts_with_viewport_density")
            summary_notes.append("DOM consistency suggests order, but the viewport is visually dense.")
        elif dom_consistency >= 0.7 and viewport_whitespace >= 0.7 and dom_palette_complexity >= 0.6:
            _add_disagreement(typed_agreement, "structural", "dom_complexity_hidden_below_the_fold", 0.3)
            disagreement_flags.append("dom_complexity_hidden_below_the_fold")
            summary_notes.append("DOM complexity may be hidden below the fold; the viewport remains sparse.")

    severity_score = _disagreement_severity_score(typed_agreement)
    severity = _severity_label(severity_score)
    if severity in {"major", "moderate"}:
        agreement_level = "low"
    elif severity == "minor":
        agreement_level = "medium"

    return {
        "agreement_level": agreement_level,
        "disagreement_severity": severity,
        "disagreement_severity_score": severity_score,
        "typed_agreement": typed_agreement,
        "disagreement_flags": disagreement_flags,
        "summary_notes": summary_notes,
        "dom_density": dom_density,
        "viewport_density": getattr(viewport_composition, "visual_density", "unknown"),
        "dom_palette_complexity": dom_palette_complexity,
        "viewport_palette_complexity": viewport_palette_complexity,
    }


def _add_disagreement(
    typed_agreement: dict[str, dict[str, Any]],
    agreement_type: str,
    flag: str,
    penalty: float,
) -> None:
    bucket = typed_agreement[agreement_type]
    bucket["score"] = round(max(0.0, float(bucket.get("score") or 0.0) - penalty), 3)
    flags = bucket.setdefault("flags", [])
    if isinstance(flags, list) and flag not in flags:
        flags.append(flag)


def _disagreement_severity_score(typed_agreement: dict[str, dict[str, Any]]) -> float:
    penalties = [1.0 - float(item.get("score") or 0.0) for item in typed_agreement.values()]
    if not penalties:
        return 0.0
    max_penalty = max(penalties)
    breadth_penalty = sum(1 for penalty in penalties if penalty > 0) * 0.08
    return round(min(1.0, max_penalty + breadth_penalty), 3)


def _severity_label(score: float) -> str:
    if score >= 0.75:
        return "major"
    if score >= 0.45:
        return "moderate"
    if score > 0:
        return "minor"
    return "none"


def _palette_complexity(colors: dict[str, Any]) -> float:
    palette = colors.get("palette") or colors.get("dominant_colors") or []
    count = sum(1 for item in palette if isinstance(item, dict) and item.get("hex"))
    confidence = _float_or_none(colors.get("confidence")) or 0.0
    return round(min(1.0, (count / 8.0) * 0.7 + confidence * 0.3), 3)


def _palette_complexity_from_vision(palette: Any) -> float:
    colors = getattr(palette, "dominant_colors", None) or []
    count = sum(1 for item in colors if getattr(item, "hex", None))
    confidence = _float_or_none(getattr(palette, "confidence", None)) or 0.0
    return round(min(1.0, (count / 8.0) * 0.7 + confidence * 0.3), 3)


def _density_rank(value: Any) -> int:
    density = str(value or "unknown")
    if density == "dense":
        return 2
    if density == "balanced":
        return 1
    if density == "sparse":
        return 0
    return 1
