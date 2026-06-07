"""Deterministic lab-only mapper for Brand3 visual diagnosis."""

from __future__ import annotations

from typing import Any

from src.visual_diagnosis.models import (
    VisualDiagnosis,
    VisualDiagnosisCapture,
    VisualDiagnosisRead,
    VisualDiagnosisSignals,
)


def build_visual_diagnosis(
    *,
    brand_name: str,
    website_url: str,
    screenshot_capture: dict[str, Any] | None = None,
    visual_signature_payload: dict[str, Any] | None = None,
    coherence_breakdown: dict[str, Any] | None = None,
    category_hint: str | None = None,
) -> VisualDiagnosis:
    """Build an explainable visual diagnosis from existing evidence.

    This mapper is intentionally cheap and deterministic. It does not call LLMs,
    does not mutate scoring, and should be treated as lab output only.
    """
    del brand_name, website_url
    payload = visual_signature_payload or {}
    capture = _capture(screenshot_capture, payload)
    evidence_refs = _evidence_refs(screenshot_capture, payload, coherence_breakdown)

    if not capture.available or capture.quality in {"missing", "poor"}:
        limitations = _dedupe([*capture.limitations, "visual_evidence_not_evaluable"])
        return VisualDiagnosis(
            status="unavailable",
            capture=capture,
            diagnosis=VisualDiagnosisRead(
                identity_read="not_evaluable",
                reference_profile="unknown",
                profile_confidence="low",
                distinctiveness="unknown",
                polish="unknown",
                brand_fit="unknown",
                template_likeness="unknown",
            ),
            signals=VisualDiagnosisSignals(
                negative=["visual evidence is unavailable or too weak to diagnose"],
                antipatterns=["capture_not_evaluable"],
            ),
            evidence_refs=evidence_refs,
            confidence="low",
            limitations=limitations,
        )
    if not _has_visual_analysis_evidence(payload):
        limitations = _dedupe([*capture.limitations, "visual_analysis_not_interpretable"])
        return VisualDiagnosis(
            status="unavailable",
            capture=capture,
            diagnosis=VisualDiagnosisRead(
                identity_read="not_evaluable",
                reference_profile="unknown",
                profile_confidence="low",
                distinctiveness="unknown",
                polish="unknown",
                brand_fit="unknown",
                template_likeness="unknown",
            ),
            signals=VisualDiagnosisSignals(
                positive=["screenshot evidence available"] if capture.available else [],
                negative=["visual analysis evidence is unavailable or not interpretable"],
                antipatterns=["visual_analysis_not_interpretable"],
            ),
            evidence_refs=evidence_refs,
            confidence="low",
            limitations=limitations,
        )

    profile, profile_confidence = _reference_profile(payload, category_hint)
    antipatterns = _antipatterns(payload, coherence_breakdown, capture, profile)
    positive = _positive_signals(payload, capture)
    negative = _negative_signals(payload, coherence_breakdown, capture, profile, antipatterns)
    distinctiveness = _distinctiveness(payload, antipatterns)
    polish = _polish(payload)
    template_likeness = _template_likeness(profile, antipatterns)
    brand_fit = _brand_fit(coherence_breakdown, antipatterns)
    identity_read = _identity_read(
        profile=profile,
        distinctiveness=distinctiveness,
        polish=polish,
        template_likeness=template_likeness,
        brand_fit=brand_fit,
        capture=capture,
        antipatterns=antipatterns,
    )
    confidence = _diagnosis_confidence(capture, payload, coherence_breakdown, profile_confidence)
    limitations = _limitations(capture, payload, coherence_breakdown)
    status = "limited" if limitations else "usable"

    return VisualDiagnosis(
        status=status,
        capture=capture,
        diagnosis=VisualDiagnosisRead(
            identity_read=identity_read,
            reference_profile=profile,
            profile_confidence=profile_confidence,
            distinctiveness=distinctiveness,
            polish=polish,
            brand_fit=brand_fit,
            template_likeness=template_likeness,
        ),
        signals=VisualDiagnosisSignals(
            positive=_dedupe(positive),
            negative=_dedupe(negative),
            antipatterns=_dedupe(antipatterns),
        ),
        evidence_refs=evidence_refs,
        confidence=confidence,
        limitations=limitations,
    )


def _capture(screenshot_capture: dict[str, Any] | None, payload: dict[str, Any]) -> VisualDiagnosisCapture:
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = (vision or {}).get("screenshot") if isinstance(vision, dict) else {}
    available = bool(
        (screenshot_capture or {}).get("screenshot_url")
        or (screenshot or {}).get("available")
        or (payload.get("assets") or {}).get("screenshot_available")
    )
    capture_type = str(
        (screenshot or {}).get("capture_type")
        or (screenshot_capture or {}).get("capture_type")
        or "unknown"
    )
    if capture_type not in {"viewport", "full_page"}:
        capture_type = "unknown"
    screenshot_quality = str(
        (screenshot or {}).get("quality")
        or (screenshot_capture or {}).get("quality")
        or ""
    ).strip().lower()
    if not available:
        quality = "missing"
    elif screenshot_quality in {"usable", "good"}:
        quality = "good"
    elif screenshot_quality in {"low_detail", "unreadable", "blank"}:
        quality = "poor"
    elif screenshot_quality:
        quality = "partial"
    else:
        quality = "partial"

    obstruction_payload = _first_dict(
        (vision or {}).get("viewport_obstruction") if isinstance(vision, dict) else None,
        ((payload.get("acquisition") or {}).get("viewport_obstruction") if isinstance(payload.get("acquisition"), dict) else None),
    )
    obstruction = _obstruction_state(obstruction_payload)
    limitations = []
    if not available:
        limitations.append("screenshot_missing")
    if quality in {"poor", "partial"}:
        limitations.append(f"capture_quality_{quality}")
    if obstruction != "none":
        limitations.append(f"viewport_obstruction_{obstruction}")
    return VisualDiagnosisCapture(
        available=available,
        type=capture_type,  # type: ignore[arg-type]
        quality=quality,  # type: ignore[arg-type]
        obstruction=obstruction,  # type: ignore[arg-type]
        limitations=_dedupe(limitations),
    )


def _reference_profile(payload: dict[str, Any], category_hint: str | None) -> tuple[str, str]:
    category = (category_hint or "").lower()
    if _category_has_any(category, "luxury", "premium", "fashion"):
        return "premium_luxury", "medium"
    if _category_has_any(category, "developer", "devtools", "api", "infrastructure"):
        return "developer_first", "medium"
    if _category_has_any(category, "media", "editorial", "publisher"):
        return "editorial_media", "medium"
    if _category_has_any(category, "ai", "ai-native", "artificial-intelligence"):
        return "ai_native", "medium"
    if _category_has_any(category, "wellness", "health", "lifestyle"):
        return "wellness_lifestyle", "medium"
    if _category_has_any(category, "ecommerce", "retail", "commerce"):
        return "ecommerce_mass_market", "medium"
    if _category_has_any(category, "local", "service"):
        return "local_service", "medium"

    components = payload.get("components") or {}
    layout = payload.get("layout") or {}
    assets = payload.get("assets") or {}
    component_types = _component_types(components)
    patterns = {str(item).lower() for item in layout.get("layout_patterns") or []}
    image_count = _as_int(assets.get("image_count"))
    card_count = _component_count(components, "card")
    cta_count = _component_count(components, "cta") + _component_count(components, "button")
    if "pricing" in component_types or "pricing" in patterns:
        return "template_saas", "medium"
    if card_count >= 3 and cta_count >= 1:
        return "template_saas", "medium"
    if image_count >= 8 and cta_count >= 1:
        return "ecommerce_mass_market", "low"
    if layout.get("visual_density") == "dense":
        return "editorial_media", "low"
    return "unknown", "low"


def _has_visual_analysis_evidence(payload: dict[str, Any]) -> bool:
    if not payload:
        return False
    if str(payload.get("interpretation_status") or "") == "not_interpretable":
        return False
    extraction = payload.get("extraction_confidence") or {}
    if _as_float(extraction.get("score")) > 0:
        return True
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    if isinstance(vision, dict) and (
        vision.get("screenshot_palette") or vision.get("composition") or vision.get("viewport_composition")
    ):
        return True
    return False


def _antipatterns(
    payload: dict[str, Any],
    coherence_breakdown: dict[str, Any] | None,
    capture: VisualDiagnosisCapture,
    profile: str,
) -> list[str]:
    if capture.quality in {"missing", "poor"}:
        return ["capture_not_evaluable"]
    components = payload.get("components") or {}
    layout = payload.get("layout") or {}
    colors = payload.get("colors") or {}
    typography = payload.get("typography") or {}
    semantics = payload.get("semantics") or {}
    data = semantics.get("data") if isinstance(semantics, dict) else {}
    source = str(payload.get("source") or "")
    result = []
    card_count = _component_count(components, "card")
    cta_count = _component_count(components, "cta") + _component_count(components, "button")
    if profile == "template_saas":
        result.append("template_saas_layout")
    if card_count >= 3:
        result.append("card_heavy_composition")
    if profile == "ai_native" and _palette_has_ai_gradient_like_colors(colors):
        result.append("generic_ai_aesthetic")
    if _as_float((coherence_breakdown or {}).get("visual_identity"), default=100.0) < 70:
        result.append("visual_promise_mismatch")
    if cta_count == 0 and source != "screenshot_vision_lab":
        result.append("weak_cta_weight")
    if typography.get("heading_scale") == "flat":
        result.append("flat_typographic_hierarchy")
    if profile == "ai_native" and _palette_has_ai_gradient_like_colors(colors):
        result.append("overused_gradient_palette")
    if layout.get("has_hero") and profile in {"template_saas", "ai_native", "unknown"}:
        visual_coherence = str((data or {}).get("visual_coherence") or "").lower()
        if not visual_coherence or visual_coherence == "not_detected":
            result.append("low_distinctiveness_hero")
    if capture.obstruction != "none":
        result.append("capture_not_evaluable")
    return _dedupe(result)


def _positive_signals(payload: dict[str, Any], capture: VisualDiagnosisCapture) -> list[str]:
    layout = payload.get("layout") or {}
    logo = payload.get("logo") or {}
    components = payload.get("components") or {}
    consistency = payload.get("consistency") or {}
    positives = []
    if capture.available:
        positives.append("screenshot evidence available")
    if layout.get("has_navigation"):
        positives.append("navigation is detectable")
    if layout.get("has_hero"):
        positives.append("hero area is detectable")
    if logo.get("logo_detected") or logo.get("textual_brand_mark_detected"):
        positives.append("brand mark is detectable")
    if _component_count(components, "cta") or (components.get("primary_ctas") or []):
        positives.append("primary action is detectable")
    if _as_float(consistency.get("overall_consistency")) >= 0.7:
        positives.append("visual system appears internally consistent")
    return positives


def _negative_signals(
    payload: dict[str, Any],
    coherence_breakdown: dict[str, Any] | None,
    capture: VisualDiagnosisCapture,
    profile: str,
    antipatterns: list[str],
) -> list[str]:
    del profile
    negatives = []
    if capture.limitations:
        negatives.extend(capture.limitations)
    if "template_saas_layout" in antipatterns:
        negatives.append("layout resembles a common SaaS template")
    if "generic_ai_aesthetic" in antipatterns:
        negatives.append("AI visual signals appear generic")
    if "visual_promise_mismatch" in antipatterns:
        negatives.append("visual identity score is below support threshold")
    if _as_float((coherence_breakdown or {}).get("visual_identity"), default=100.0) < 70:
        negatives.append("current Magnetism visual_identity is weak")
    consistency = payload.get("consistency") or {}
    if _as_float(consistency.get("overall_consistency")) < 0.45:
        negatives.append("visual consistency evidence is weak")
    return negatives


def _distinctiveness(payload: dict[str, Any], antipatterns: list[str]) -> str:
    consistency = payload.get("consistency") or {}
    if "generic_ai_aesthetic" in antipatterns or "template_saas_layout" in antipatterns:
        return "low"
    if _as_float(consistency.get("overall_consistency")) >= 0.75 and "low_distinctiveness_hero" not in antipatterns:
        return "medium"
    return "unknown"


def _polish(payload: dict[str, Any]) -> str:
    semantics = payload.get("semantics") or {}
    data = semantics.get("data") if isinstance(semantics, dict) else {}
    score = _as_float((data or {}).get("visual_polish_score"), default=0.0)
    if score >= 8:
        return "high"
    if score >= 5:
        return "medium"
    consistency = payload.get("consistency") or {}
    if _as_float(consistency.get("overall_consistency")) >= 0.7:
        return "medium"
    if _as_float(consistency.get("overall_consistency")) > 0:
        return "low"
    return "unknown"


def _template_likeness(profile: str, antipatterns: list[str]) -> str:
    if profile == "template_saas" or "template_saas_layout" in antipatterns:
        return "high"
    if "card_heavy_composition" in antipatterns:
        return "medium"
    return "low"


def _brand_fit(coherence_breakdown: dict[str, Any] | None, antipatterns: list[str]) -> str:
    visual_score = _as_float((coherence_breakdown or {}).get("visual_identity"), default=-1)
    if visual_score >= 85:
        return "high"
    if visual_score >= 70:
        return "medium"
    if visual_score >= 0 or "visual_promise_mismatch" in antipatterns:
        return "low"
    return "unknown"


def _identity_read(
    *,
    profile: str,
    distinctiveness: str,
    polish: str,
    template_likeness: str,
    brand_fit: str,
    capture: VisualDiagnosisCapture,
    antipatterns: list[str],
) -> str:
    if capture.quality in {"missing", "poor"}:
        return "not_evaluable"
    if brand_fit == "low" and "visual_promise_mismatch" in antipatterns:
        return "weak_or_inconsistent"
    if profile == "premium_luxury" and distinctiveness in {"high", "medium"}:
        return "visually_distinctive"
    if profile == "developer_first":
        return "functionally_clear"
    if profile == "editorial_media":
        return "editorially_coherent"
    if profile == "wellness_lifestyle":
        return "emotionally_coherent"
    if profile == "ecommerce_mass_market":
        return "commerce_clear"
    if profile == "local_service":
        return "practical_but_generic"
    if template_likeness == "high":
        return "coherent_but_generic" if polish in {"medium", "high"} else "polished_but_undifferentiated"
    if distinctiveness == "low":
        return "polished_but_undifferentiated"
    return "coherent_but_generic"


def _diagnosis_confidence(
    capture: VisualDiagnosisCapture,
    payload: dict[str, Any],
    coherence_breakdown: dict[str, Any] | None,
    profile_confidence: str,
) -> str:
    score = 0
    if capture.quality == "good":
        score += 2
    elif capture.quality == "partial":
        score += 1
    if payload:
        score += 1
    if coherence_breakdown:
        score += 1
    if profile_confidence == "medium":
        score += 1
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _limitations(
    capture: VisualDiagnosisCapture,
    payload: dict[str, Any],
    coherence_breakdown: dict[str, Any] | None,
) -> list[str]:
    limitations = list(capture.limitations)
    if not payload:
        limitations.append("visual_signature_payload_missing")
    if not coherence_breakdown:
        limitations.append("coherence_breakdown_missing")
    extraction = payload.get("extraction_confidence") or {}
    for item in extraction.get("limitations") or []:
        limitation = str(item)
        if limitation == "screenshot_not_available" and capture.available:
            continue
        limitations.append(limitation)
    return _dedupe(limitations)


def _evidence_refs(
    screenshot_capture: dict[str, Any] | None,
    payload: dict[str, Any],
    coherence_breakdown: dict[str, Any] | None,
) -> list[str]:
    refs = []
    if screenshot_capture:
        refs.append("raw_inputs:screenshot_capture")
    if payload:
        source = str(payload.get("source") or "")
        if source == "contextdev_candidate_summary":
            refs.append("raw_inputs:contextdev_candidate_summary")
        elif source == "screenshot_vision_lab":
            refs.append("raw_inputs:screenshot_vision_lab")
        else:
            refs.append("raw_inputs:visual_signature")
    if coherence_breakdown:
        refs.append("magnetism:coherence_breakdown")
    return refs


def _obstruction_state(payload: dict[str, Any]) -> str:
    if not payload:
        return "none"
    present = bool(payload.get("present") or payload.get("detected"))
    if not present and str(payload.get("type") or "").lower() in {"", "none", "not_detected"}:
        return "none"
    kind = str(payload.get("type") or payload.get("obstruction_type") or "unknown").lower()
    if "cookie" in kind or "consent" in kind:
        return "cookie_banner"
    if "login" in kind:
        return "login_wall"
    if "paywall" in kind:
        return "paywall"
    if "modal" in kind or "overlay" in kind:
        return "modal"
    return "unknown"


def _component_types(components: dict[str, Any]) -> set[str]:
    return {
        str(item.get("type") or "").lower()
        for item in components.get("components") or []
        if isinstance(item, dict)
    }


def _category_has_any(category: str, *needles: str) -> bool:
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in category)
    tokens = set(normalized.split())
    joined = " ".join(tokens)
    for needle in needles:
        needle_normalized = needle.replace("-", " ").lower()
        if " " in needle_normalized:
            if needle_normalized in joined:
                return True
        elif needle_normalized in tokens:
            return True
    return False


def _component_count(components: dict[str, Any], component_type: str) -> int:
    total = 0
    for item in components.get("components") or []:
        if isinstance(item, dict) and str(item.get("type") or "").lower() == component_type:
            total += _as_int(item.get("count"), default=1)
    return total


def _palette_has_ai_gradient_like_colors(colors: dict[str, Any]) -> bool:
    candidates = [
        str(item).lower()
        for item in [
            *(colors.get("dominant_colors") or []),
            *(colors.get("accent_candidates") or []),
        ]
        if item
    ]
    return any(color.startswith(("#6", "#7", "#8", "#9", "#a", "#b")) for color in candidates)


def _first_dict(*items: Any) -> dict[str, Any]:
    for item in items:
        if isinstance(item, dict):
            return item
    return {}


def _as_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
