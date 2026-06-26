"""Unified visual evidence contracts and builders for Visual Diagnosis Lab."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.visual_signature.versions import VISUAL_EVIDENCE_PACK_SCHEMA_VERSION
from src.visual_signature.capture.visual_evidence_support import merge_visual_payloads as _merge_visual_payloads
from src.visual_signature.capture.visual_evidence_support import promote_vision_evidence as _promote_vision_evidence


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
