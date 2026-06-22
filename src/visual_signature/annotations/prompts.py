"""Prompt scaffold for mock-only Visual Signature multimodal annotations."""

from __future__ import annotations

from src.visual_signature.versions import ANNOTATION_PROMPT_VERSION as PROMPT_VERSION
from src.visual_signature.annotations.types import ANNOTATION_TARGETS, AnnotationRequest


from typing import Any


def _coerce_request(request: AnnotationRequest | dict[str, Any]) -> dict[str, Any]:
    if isinstance(request, AnnotationRequest):
        return {
            "brand_name": request.brand_name,
            "website_url": request.website_url,
            "expected_category": request.expected_category,
        }
    if isinstance(request, dict):
        return request
    raise TypeError(f"Unsupported request type: {type(request)}")


def build_annotation_prompt(request: AnnotationRequest | dict[str, Any]) -> str:
    """Build the constrained evidence-only prompt text used by the mock path."""
    payload = _coerce_request(request)
    category = payload.get("expected_category") or "unknown"
    targets = ", ".join(ANNOTATION_TARGETS)
    return "\n".join(
        [
            f"Prompt version: {PROMPT_VERSION}",
            "You are annotating visual evidence for Brand3 calibration.",
            "Return JSON only. Do not score the brand. Do not infer strategy.",
            "Use unknown when evidence is not visible in the supplied screenshot.",
            f"Brand: {payload.get('brand_name')}",
            f"Website: {payload.get('website_url')}",
            f"Expected category: {category}",
            f"Annotation targets: {targets}",
            "Each target must include label, confidence, evidence, source, limitations.",
            "Keep observations short and tied to visible evidence.",
        ]
    )
