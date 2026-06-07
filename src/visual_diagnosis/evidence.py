"""Lab-only visual evidence builders.

This module adapts existing Brand3 local evidence into a single visual payload
that Visual Diagnosis can consume. It does not call network providers, does not
mutate scoring, and does not require an LLM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class VisualEvidence:
    source_mode: str
    visual_signature_payload: dict[str, Any] | None
    evidence_refs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_visual_evidence_from_local_inputs(
    *,
    brand_name: str,
    website_url: str,
    web_payload: dict[str, Any] | None = None,
    screenshot_capture: dict[str, Any] | None = None,
    derive_from_screenshot: bool = False,
) -> VisualEvidence:
    """Build visual evidence from already-collected local inputs."""
    if web_payload:
        payload = _visual_signature_from_web_payload(
            brand_name=brand_name,
            website_url=website_url,
            web_payload=web_payload,
        )
        refs = ["raw_inputs:web"]
        limitations = ["dom_css_visual_lab"]
        if derive_from_screenshot and screenshot_capture:
            payload = _enrich_with_local_screenshot(payload, screenshot_capture)
            refs.append("raw_inputs:screenshot_capture")
            limitations.append("screenshot_vision_only")
        payload["source"] = "dom_css_visual_lab"
        return VisualEvidence(
            source_mode="dom_css_visual_lab",
            visual_signature_payload=payload,
            evidence_refs=refs,
            limitations=limitations,
        )

    if derive_from_screenshot and screenshot_capture:
        payload = screenshot_capture_to_visual_signature(
            screenshot_capture,
            brand_name=brand_name,
            website_url=website_url,
        )
        return VisualEvidence(
            source_mode="screenshot_vision_lab",
            visual_signature_payload=payload,
            evidence_refs=["raw_inputs:screenshot_capture"],
            limitations=["screenshot_vision_only"],
        )

    return VisualEvidence(
        source_mode="none",
        visual_signature_payload=None,
        limitations=["visual_evidence_missing"],
    )


def screenshot_capture_to_visual_signature(
    screenshot_capture: dict[str, Any],
    *,
    brand_name: str,
    website_url: str,
) -> dict[str, Any]:
    """Build lab-only visual evidence from an existing local screenshot."""
    base_payload: dict[str, Any] = {
        "brand_name": brand_name,
        "website_url": website_url,
        "interpretation_status": "interpretable",
        "source": "screenshot_vision_lab",
        "assets": {"screenshot_available": True},
        "layout": {},
        "logo": {},
        "components": {"primary_ctas": [], "components": []},
        "colors": {},
        "typography": {},
        "consistency": {},
        "extraction_confidence": {
            "score": 0.1,
            "level": "low",
            "limitations": ["screenshot_vision_only"],
        },
    }
    return _enrich_with_local_screenshot(base_payload, screenshot_capture)


def _visual_signature_from_web_payload(
    *,
    brand_name: str,
    website_url: str,
    web_payload: dict[str, Any],
) -> dict[str, Any]:
    from src.visual_signature import extract_visual_signature

    payload = extract_visual_signature(
        brand_name=brand_name,
        website_url=website_url,
        web_data=web_payload,
        screenshot_payload=None,
        adapter=None,
    )
    payload["source"] = "dom_css_visual_lab"
    limitations = (payload.get("extraction_confidence") or {}).get("limitations") or []
    payload.setdefault("extraction_confidence", {})["limitations"] = [
        *limitations,
        "dom_css_visual_lab",
    ]
    return payload


def _enrich_with_local_screenshot(
    payload: dict[str, Any],
    screenshot_capture: dict[str, Any],
) -> dict[str, Any]:
    try:
        from src.visual_signature.vision import enrich_visual_signature_with_vision

        enriched = enrich_visual_signature_with_vision(
            visual_signature_payload=payload,
            screenshot_payload=screenshot_capture,
        )
    except Exception as exc:
        return {
            **payload,
            "interpretation_status": "not_interpretable",
            "extraction_confidence": {
                "score": 0.0,
                "level": "low",
                "limitations": [f"screenshot_vision_failed: {exc}"],
            },
        }
    return _promote_vision_evidence(enriched)


def _promote_vision_evidence(payload: dict[str, Any]) -> dict[str, Any]:
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


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, parsed))
