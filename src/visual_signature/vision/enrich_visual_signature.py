"""Add local screenshot-derived evidence to a Visual Signature payload."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.visual_signature.vision.composition import analyze_composition
from src.visual_signature.vision.confidence import calculate_vision_confidence
from src.visual_signature.vision.palette_from_screenshot import extract_palette_from_screenshot
from src.visual_signature.vision.screenshot_quality import (
    resolve_screenshot_path,
    resolve_screenshot_metadata,
    screenshot_evidence_for_path,
)
from src.visual_signature.vision.types import RasterImage, VisionEvidence
from src.visual_signature.vision.viewport_obstruction import analyze_viewport_obstruction


def enrich_visual_signature_with_vision(
    *,
    visual_signature_payload: dict[str, Any],
    screenshot_path: str | None = None,
    screenshot_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a Visual Signature payload with additive local vision evidence.

    This function does not call multimodal models, does not influence scoring,
    and does not mutate the input payload.
    """
    payload = deepcopy(visual_signature_payload)
    metadata = resolve_screenshot_metadata(screenshot_payload=screenshot_payload)
    resolved_path = resolve_screenshot_path(
        screenshot_path=screenshot_path,
        screenshot_payload=screenshot_payload,
        visual_signature_payload=payload,
    )
    screenshot, image = screenshot_evidence_for_path(resolved_path, screenshot_payload=metadata)
    if metadata.get("capture_type") and screenshot.available:
        screenshot.capture_type = _normalize_capture_type(metadata.get("capture_type"))
    if metadata.get("page_url") and screenshot.available:
        screenshot.page_url = str(metadata.get("page_url"))
    if metadata.get("width") and screenshot.available:
        screenshot.viewport_width = _int_or_none(metadata.get("viewport_width") or metadata.get("width"))
    if metadata.get("height") and screenshot.available:
        screenshot.viewport_height = _int_or_none(metadata.get("viewport_height") or metadata.get("height"))
    if screenshot.available and screenshot.capture_type == "unknown":
        screenshot.capture_type = "full_page" if resolved_path else "unknown"
    palette = extract_palette_from_screenshot(image)
    composition = analyze_composition(image)
    confidence = calculate_vision_confidence(
        screenshot=screenshot,
        palette=palette,
        composition=composition,
    )
    viewport_image = _viewport_image(image, screenshot)
    viewport_palette = extract_palette_from_screenshot(viewport_image)
    viewport_composition = analyze_composition(viewport_image)
    viewport_confidence = calculate_vision_confidence(
        screenshot=screenshot,
        palette=viewport_palette,
        composition=viewport_composition,
    )
    agreement = compare_dom_and_viewport(payload, composition, viewport_composition, palette, viewport_palette)
    acquisition = payload.get("acquisition") if isinstance(payload.get("acquisition"), dict) else {}
    existing_obstruction = acquisition.get("viewport_obstruction") if isinstance(acquisition, dict) else None
    dom_html = str(acquisition.get("rendered_html") or acquisition.get("raw_html") or "") if isinstance(acquisition, dict) else ""
    viewport_obstruction = analyze_viewport_obstruction(
        dom_html=dom_html,
        viewport_image=viewport_image,
        existing_obstruction=existing_obstruction if isinstance(existing_obstruction, dict) else None,
    )
    payload["vision"] = VisionEvidence(
        screenshot=screenshot,
        screenshot_palette=palette,
        composition=composition,
        vision_confidence=confidence,
        agreement=agreement,
        viewport_palette=viewport_palette,
        viewport_whitespace_ratio=viewport_composition.whitespace_ratio,
        viewport_visual_density=viewport_composition.visual_density,
        viewport_composition=viewport_composition,
        viewport_confidence=viewport_confidence,
        viewport_obstruction=viewport_obstruction.to_dict(),
    ).to_dict()
    return payload


def _viewport_image(image: RasterImage | None, screenshot: Any) -> RasterImage | None:
    if image is None:
        return None
    if screenshot is None or not getattr(screenshot, "available", False):
        return image

    viewport_width = _int_or_none(getattr(screenshot, "viewport_width", None)) or image.width
    viewport_height = _int_or_none(getattr(screenshot, "viewport_height", None))
    capture_type = _normalize_capture_type(getattr(screenshot, "capture_type", "unknown"))
    if capture_type == "viewport" and viewport_height is None:
        viewport_height = image.height
    if viewport_height is None:
        viewport_height = min(image.height, 900)
    viewport_height = min(viewport_height, 900)
    viewport_width = max(1, min(image.width, viewport_width))
    viewport_height = max(1, min(image.height, viewport_height))
    if viewport_width == image.width and viewport_height == image.height:
        return image

    pixels: list[tuple[int, int, int]] = []
    for y in range(viewport_height):
        row_offset = y * image.width
        pixels.extend(image.pixels[row_offset:row_offset + viewport_width])
    return RasterImage(
        width=viewport_width,
        height=viewport_height,
        pixels=pixels,
        source_path=image.source_path,
    )


def _normalize_capture_type(value: Any) -> str:
    capture_type = str(value or "").strip().lower()
    if capture_type in {"viewport", "full_page"}:
        return capture_type
    return "unknown"


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
