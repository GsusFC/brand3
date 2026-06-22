"""Unified visual evidence contracts and builders for Visual Diagnosis Lab."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none
from src.visual_signature._internal.utils import unique_text as _unique_text
from src.visual_signature.versions import VISUAL_EVIDENCE_PACK_SCHEMA_VERSION


@dataclass
class VisualEvidenceSource:
    source_id: str
    source_type: str
    available: bool
    visual_signature_payload: dict[str, Any] | None = None
    evidence_refs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.visual_signature_payload is None:
            data.pop("visual_signature_payload", None)
        return data


@dataclass
class VisualEvidenceBundle:
    schema_version: str = VISUAL_EVIDENCE_PACK_SCHEMA_VERSION
    sources: list[VisualEvidenceSource] = field(default_factory=list)
    fused_visual_signature_payload: dict[str, Any] | None = None
    fusion_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sources": [source.to_dict() for source in self.sources],
            "available_source_types": [
                source.source_type for source in self.sources if source.available
            ],
            "fusion_notes": list(self.fusion_notes),
        }


@dataclass
class VisualEvidence:
    source_mode: str
    visual_signature_payload: dict[str, Any] | None
    evidence_refs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fuse_visual_signature_payloads(
    *,
    computed_payload: dict[str, Any] | None = None,
    web_payload: dict[str, Any] | None = None,
    screenshot_payload: dict[str, Any] | None = None,
    visual_signature_payload: dict[str, Any] | None = None,
    external_legacy_payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Fuse lab evidence without silently dropping available sources."""
    if visual_signature_payload:
        return visual_signature_payload, ["visual_signature_payload_used_as_canonical"]

    notes: list[str] = []
    if computed_payload and web_payload:
        fused = _merge_visual_payloads(primary=computed_payload, secondary=web_payload)
        fused["source"] = "visual_evidence_bundle_lab"
        fused["bundle_sources"] = ["computed_style_visual_lab", "dom_css_visual_lab"]
        notes.append("computed_style_and_web_payload_fused")
        if screenshot_payload:
            fused = _merge_visual_payloads(primary=fused, secondary=screenshot_payload)
            fused["bundle_sources"].append("screenshot_vision_lab")
            notes.append("screenshot_vision_merged_into_fused_payload")
        return fused, notes

    if computed_payload:
        notes.append("computed_style_payload_used")
        return computed_payload, notes
    if web_payload:
        notes.append("web_payload_used")
        return web_payload, notes
    if screenshot_payload:
        notes.append("screenshot_vision_payload_used")
        return screenshot_payload, notes
    if external_legacy_payload:
        notes.append("external_candidate_summary_legacy_used")
        return external_legacy_payload, notes
    return None, ["visual_evidence_missing"]


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


def enrich_visual_signature_with_local_screenshot(
    payload: dict[str, Any],
    screenshot_capture: dict[str, Any],
) -> dict[str, Any]:
    """Add local screenshot-derived evidence to a lab visual payload."""
    return _enrich_with_local_screenshot(payload, screenshot_capture)


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


def _merge_visual_payloads(*, primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    fused = dict(primary)
    fused["assets"] = _merge_dict(primary.get("assets"), secondary.get("assets"))
    fused["layout"] = _merge_dict(primary.get("layout"), secondary.get("layout"))
    fused["logo"] = _merge_dict(primary.get("logo"), secondary.get("logo"))
    fused["components"] = _merge_components(primary.get("components"), secondary.get("components"))
    fused["colors"] = _merge_colors(primary.get("colors"), secondary.get("colors"))
    fused["typography"] = _merge_dict(primary.get("typography"), secondary.get("typography"))
    fused["consistency"] = _merge_consistency(primary.get("consistency"), secondary.get("consistency"))
    fused["semantics"] = _merge_dict(primary.get("semantics"), secondary.get("semantics"))
    if isinstance(secondary.get("vision"), dict) and secondary["vision"]:
        fused["vision"] = _merge_dict(primary.get("vision"), secondary.get("vision"))
    fused["extraction_confidence"] = _merge_confidence(
        primary.get("extraction_confidence"),
        secondary.get("extraction_confidence"),
    )
    return fused


def _merge_dict(primary: Any, secondary: Any) -> dict[str, Any]:
    left = primary if isinstance(primary, dict) else {}
    right = secondary if isinstance(secondary, dict) else {}
    return {**right, **left}


def _merge_colors(primary: Any, secondary: Any) -> dict[str, Any]:
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


def _merge_components(primary: Any, secondary: Any) -> dict[str, Any]:
    left = primary if isinstance(primary, dict) else {}
    right = secondary if isinstance(secondary, dict) else {}
    return {
        **right,
        **left,
        "primary_ctas": _unique_text([*(left.get("primary_ctas") or []), *(right.get("primary_ctas") or [])])[:8],
        "components": _merge_component_counts(left.get("components") or [], right.get("components") or []),
    }


def _merge_component_counts(left_items: list[Any], right_items: list[Any]) -> list[dict[str, Any]]:
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


def _merge_consistency(primary: Any, secondary: Any) -> dict[str, Any]:
    merged = _merge_dict(primary, secondary)
    scores = [
        _float_or_none((primary or {}).get("overall_consistency")) if isinstance(primary, dict) else None,
        _float_or_none((secondary or {}).get("overall_consistency")) if isinstance(secondary, dict) else None,
    ]
    present = [score for score in scores if score is not None]
    if present:
        merged["overall_consistency"] = round(max(present), 3)
    return merged


def _merge_confidence(primary: Any, secondary: Any) -> dict[str, Any]:
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


def _bounded_float(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, parsed))
