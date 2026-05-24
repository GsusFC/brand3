"""Metric extraction for Visual Signature category baselines."""

from __future__ import annotations

import math
from typing import Any

from src.visual_signature.baselines.types import VisualSignatureMetricRow


_SIGNAL_KEYS = ("colors", "typography", "logo", "layout", "components", "assets", "consistency")


def metric_row_from_payload(
    payload: dict[str, Any],
    *,
    source_path: str | None = None,
) -> VisualSignatureMetricRow:
    calibration = payload.get("calibration") if isinstance(payload.get("calibration"), dict) else {}
    category = str(
        calibration.get("expected_category")
        or payload.get("expected_category")
        or payload.get("category")
        or "uncategorized"
    ).strip() or "uncategorized"
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    agreement = vision.get("agreement") if isinstance(vision.get("agreement"), dict) else {}
    viewport_composition = (
        vision.get("viewport_composition")
        if isinstance(vision.get("viewport_composition"), dict)
        else {}
    )
    components = payload.get("components") if isinstance(payload.get("components"), dict) else {}
    typography = payload.get("typography") if isinstance(payload.get("typography"), dict) else {}
    extraction_confidence = (
        payload.get("extraction_confidence")
        if isinstance(payload.get("extraction_confidence"), dict)
        else {}
    )
    vision_confidence = (
        vision.get("viewport_confidence")
        if isinstance(vision.get("viewport_confidence"), dict)
        else vision.get("vision_confidence")
        if isinstance(vision.get("vision_confidence"), dict)
        else {}
    )
    interpretation_status = str(payload.get("interpretation_status") or "unknown")

    limitations: list[str] = []
    if interpretation_status == "not_interpretable":
        limitations.append("not_interpretable_excluded_from_baseline_averages")
    if not vision:
        limitations.append("vision_payload_missing")
    if not agreement:
        limitations.append("agreement_payload_missing")

    return VisualSignatureMetricRow(
        category=category,
        brand_name=str(payload.get("brand_name") or payload.get("brand") or "Unknown"),
        website_url=str(payload.get("website_url") or payload.get("url") or payload.get("analyzed_url") or ""),
        interpretation_status=interpretation_status,
        viewport_whitespace=_float_or_none(
            vision.get("viewport_whitespace_ratio")
            or viewport_composition.get("whitespace_ratio")
        ),
        viewport_whitespace_band=_whitespace_band(
            _float_or_none(vision.get("viewport_whitespace_ratio") or viewport_composition.get("whitespace_ratio"))
        ),
        viewport_density=str(
            vision.get("viewport_visual_density")
            or viewport_composition.get("visual_density")
            or "unknown"
        ),
        viewport_density_score=_density_score(
            vision.get("viewport_visual_density")
            or viewport_composition.get("visual_density")
            or "unknown"
        ),
        viewport_composition=str(
            viewport_composition.get("composition_classification")
            or vision.get("viewport_composition")
            or "unknown"
        ),
        composition_stability=_composition_stability(vision),
        palette_complexity=_palette_complexity(payload),
        dom_viewport_agreement_level=str(agreement.get("agreement_level") or "unknown"),
        dom_viewport_agreement_score=_agreement_score(agreement.get("agreement_level")),
        dom_viewport_disagreement_severity=_agreement_severity(agreement),
        dom_viewport_disagreement_severity_score=_severity_score(_agreement_severity(agreement)),
        structural_agreement_score=_typed_agreement_score(agreement, "structural"),
        density_agreement_score=_typed_agreement_score(agreement, "density"),
        composition_agreement_score=_typed_agreement_score(agreement, "composition"),
        palette_agreement_score=_typed_agreement_score(agreement, "palette"),
        cta_density=_cta_density(components),
        visible_cta_weight=_visible_cta_weight(components, viewport_composition),
        component_density=_component_density(components),
        typography_complexity=_typography_complexity(typography),
        extraction_confidence=_float_or_none(extraction_confidence.get("score")),
        vision_confidence=_float_or_none(vision_confidence.get("score")),
        signal_availability=_signal_availability(payload),
        signal_usability=_signal_usability(payload),
        signal_coverage=_signal_coverage(payload),
        source_path=source_path,
        limitations=limitations,
    )


def _palette_complexity(payload: dict[str, Any]) -> float | None:
    colors = payload.get("colors") if isinstance(payload.get("colors"), dict) else {}
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    viewport_palette = (
        vision.get("viewport_palette")
        if isinstance(vision.get("viewport_palette"), dict)
        else {}
    )
    screenshot_palette = (
        vision.get("screenshot_palette")
        if isinstance(vision.get("screenshot_palette"), dict)
        else {}
    )
    dom_count = _color_count(colors)
    viewport_count = _int_or_none(viewport_palette.get("color_count"))
    screenshot_count = _int_or_none(screenshot_palette.get("color_count"))
    count = max([value for value in (dom_count, viewport_count, screenshot_count) if value is not None], default=None)
    if count is None:
        return None
    color_count_score = min(1.0, math.log1p(count) / math.log1p(96))
    entropy_score = _palette_entropy(viewport_palette) or _palette_entropy(screenshot_palette)
    dom_score = min(1.0, (dom_count or 0) / 10.0)
    if entropy_score is None:
        return round((color_count_score * 0.75) + (dom_score * 0.25), 3)
    return round((color_count_score * 0.55) + (entropy_score * 0.30) + (dom_score * 0.15), 3)


def _color_count(colors: dict[str, Any]) -> int | None:
    candidates = colors.get("palette") or colors.get("dominant_colors") or []
    if not isinstance(candidates, list):
        return None
    count = 0
    for item in candidates:
        if isinstance(item, dict) and item.get("hex"):
            count += 1
        elif isinstance(item, str) and item.strip():
            count += 1
    return count


def _cta_density(components: dict[str, Any]) -> float:
    primary_ctas = components.get("primary_ctas") if isinstance(components.get("primary_ctas"), list) else []
    component_ctas = 0
    for item in components.get("components") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").lower() == "cta":
            component_ctas += int(_float_or_none(item.get("count")) or 1)
    return round(min(1.0, (len(primary_ctas) + component_ctas) / 8.0), 3)


def _component_density(components: dict[str, Any]) -> float:
    weighted_total = 0.0
    for item in components.get("components") or []:
        if not isinstance(item, dict):
            continue
        count = int(_float_or_none(item.get("count")) or 1)
        weighted_total += count * _component_weight(str(item.get("type") or "unknown"))
    if weighted_total <= 0:
        return 0.0
    return round(min(1.0, math.log1p(weighted_total) / math.log1p(48)), 3)


def _visible_cta_weight(components: dict[str, Any], viewport_composition: dict[str, Any]) -> float:
    base = _cta_density(components)
    density = str(viewport_composition.get("visual_density") or "unknown")
    whitespace = _float_or_none(viewport_composition.get("whitespace_ratio"))
    if density == "dense":
        density_factor = 0.8
    elif density == "sparse":
        density_factor = 1.1
    else:
        density_factor = 1.0
    if whitespace is not None and whitespace >= 0.65:
        density_factor += 0.1
    return round(min(1.0, base * density_factor), 3)


def _typography_complexity(typography: dict[str, Any]) -> float:
    families = typography.get("font_families") if isinstance(typography.get("font_families"), list) else []
    family_count = 0
    for item in families:
        if isinstance(item, dict) and item.get("family"):
            family_count += 1
        elif isinstance(item, str) and item.strip():
            family_count += 1
    size_count = len(typography.get("size_samples_px") or [])
    weight_count = len(typography.get("weight_range") or {})
    return round(min(1.0, (family_count * 0.18) + (size_count * 0.03) + (weight_count * 0.08)), 3)


def _agreement_score(level: Any) -> float | None:
    normalized = str(level or "").strip().lower()
    if normalized == "high":
        return 1.0
    if normalized == "medium":
        return 0.5
    if normalized == "low":
        return 0.0
    return None


def _signal_coverage(payload: dict[str, Any]) -> float:
    availability = _signal_availability(payload)
    usability = _signal_usability(payload)
    return round((availability * 0.35) + (usability * 0.65), 3)


def _signal_availability(payload: dict[str, Any]) -> float:
    covered = 0
    for key in _SIGNAL_KEYS:
        value = payload.get(key)
        if not isinstance(value, dict):
            continue
        if any(item not in (None, "", [], {}, "unknown", ["unknown"]) for item in value.values()):
            covered += 1
    return round(covered / len(_SIGNAL_KEYS), 3)


def _signal_usability(payload: dict[str, Any]) -> float:
    scores: list[float] = []
    for key in _SIGNAL_KEYS:
        value = payload.get(key)
        if not isinstance(value, dict):
            scores.append(0.0)
            continue
        confidence = _float_or_none(value.get("confidence"))
        if confidence is not None:
            scores.append(max(0.0, min(1.0, confidence)))
        elif any(item not in (None, "", [], {}, "unknown", ["unknown"]) for item in value.values()):
            scores.append(0.45)
        else:
            scores.append(0.0)
    return round(sum(scores) / len(scores), 3)


def _palette_entropy(palette: dict[str, Any]) -> float | None:
    colors = palette.get("dominant_colors")
    if not isinstance(colors, list) or not colors:
        return None
    ratios: list[float] = []
    for item in colors:
        if isinstance(item, dict):
            ratio = _float_or_none(item.get("ratio"))
            if ratio is not None and ratio > 0:
                ratios.append(ratio)
    if not ratios:
        return None
    total = sum(ratios)
    if total <= 0:
        return None
    normalized = [ratio / total for ratio in ratios]
    entropy = -sum(ratio * math.log(ratio, 2) for ratio in normalized if ratio > 0)
    max_entropy = math.log(len(normalized), 2) if len(normalized) > 1 else 1.0
    return round(entropy / max_entropy, 3) if max_entropy else 0.0


def _component_weight(component_type: str) -> float:
    return {
        "cta": 1.8,
        "button": 1.1,
        "form": 1.4,
        "navigation": 0.9,
        "pricing": 1.2,
        "card": 0.55,
        "accordion": 0.45,
        "tabs": 0.45,
        "modal": 0.35,
    }.get(component_type, 0.4)


def _density_score(value: Any) -> float | None:
    density = str(value or "unknown")
    if density == "sparse":
        return 0.2
    if density == "balanced":
        return 0.55
    if density == "dense":
        return 0.9
    return None


def _whitespace_band(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value < 0.25:
        return "low"
    if value < 0.45:
        return "moderate"
    if value < 0.70:
        return "high"
    return "very_high"


def _composition_stability(vision: dict[str, Any]) -> float | None:
    full = vision.get("composition") if isinstance(vision.get("composition"), dict) else {}
    viewport = vision.get("viewport_composition") if isinstance(vision.get("viewport_composition"), dict) else {}
    if not full or not viewport:
        return None
    score = 1.0
    if full.get("visual_density") != viewport.get("visual_density"):
        score -= 0.35
    if full.get("composition_classification") != viewport.get("composition_classification"):
        score -= 0.25
    full_ws = _float_or_none(full.get("whitespace_ratio"))
    viewport_ws = _float_or_none(viewport.get("whitespace_ratio"))
    if full_ws is not None and viewport_ws is not None:
        score -= min(0.3, abs(full_ws - viewport_ws))
    return round(max(0.0, score), 3)


def _severity_score(value: Any) -> float | None:
    severity = str(value or "none")
    if severity == "none":
        return 0.0
    if severity == "minor":
        return 0.25
    if severity == "moderate":
        return 0.6
    if severity == "major":
        return 1.0
    return None


def _typed_agreement_score(agreement: dict[str, Any], key: str) -> float | None:
    typed = agreement.get("typed_agreement")
    if not isinstance(typed, dict):
        return _typed_agreement_score_from_flags(agreement, key)
    value = typed.get(key)
    if isinstance(value, dict):
        return _float_or_none(value.get("score"))
    return _float_or_none(value)


def _agreement_severity(agreement: dict[str, Any]) -> str:
    explicit = str(agreement.get("disagreement_severity") or "").strip()
    if explicit:
        return explicit
    flags = agreement.get("disagreement_flags")
    if not isinstance(flags, list) or not flags:
        return "none"
    if len(flags) >= 3:
        return "major"
    if len(flags) == 2:
        return "moderate"
    return "minor"


def _typed_agreement_score_from_flags(agreement: dict[str, Any], key: str) -> float:
    flags = [str(item) for item in agreement.get("disagreement_flags") or []]
    if not flags:
        return 1.0
    penalty = 0.0
    for flag in flags:
        if key == "density" and "density" in flag:
            penalty += 0.45
        elif key == "palette" and "palette" in flag:
            penalty += 0.45
        elif key == "composition" and ("composition" in flag or "hero" in flag or "consistency" in flag):
            penalty += 0.35
        elif key == "structural" and ("blank" in flag or "structure" in flag or "below_the_fold" in flag):
            penalty += 0.5
    return round(max(0.0, 1.0 - penalty), 3)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
