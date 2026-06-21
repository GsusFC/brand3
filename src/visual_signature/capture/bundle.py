"""Evidence bundle contracts for Visual Diagnosis Lab."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none


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
    schema_version: str = "visual-evidence-bundle-v1"
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


def fuse_visual_signature_payloads(
    *,
    computed_payload: dict[str, Any] | None = None,
    web_payload: dict[str, Any] | None = None,
    screenshot_payload: dict[str, Any] | None = None,
    visual_signature_payload: dict[str, Any] | None = None,
    external_legacy_payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Fuse lab evidence without silently dropping available sources.

    This is intentionally conservative. It preserves the canonical
    Visual Signature payload when provided; otherwise it combines computed style
    evidence with web-derived DOM evidence and screenshot vision where present.
    """
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
        "dominant_colors": _dedupe(
            [*(left.get("dominant_colors") or []), *(right.get("dominant_colors") or [])]
        )[:10],
        "accent_candidates": _dedupe(
            [*(left.get("accent_candidates") or []), *(right.get("accent_candidates") or [])]
        )[:6],
    }


def _merge_components(primary: Any, secondary: Any) -> dict[str, Any]:
    left = primary if isinstance(primary, dict) else {}
    right = secondary if isinstance(secondary, dict) else {}
    return {
        **right,
        **left,
        "primary_ctas": _dedupe([*(left.get("primary_ctas") or []), *(right.get("primary_ctas") or [])])[:8],
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
    limitations = _dedupe([*(left.get("limitations") or []), *(right.get("limitations") or [])])
    return {
        **right,
        **left,
        "score": round(score, 3),
        "level": "medium" if score >= 0.55 else "low",
        "limitations": limitations,
    }


def _dedupe(items: list[Any]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
