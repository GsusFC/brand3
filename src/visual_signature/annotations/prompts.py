"""Prompt scaffolding for future Visual Signature multimodal annotations."""

from __future__ import annotations

from src.visual_signature.annotations.types import ANNOTATION_TARGETS, AnnotationRequest


PROMPT_VERSION = "visual-signature-annotation-prompt-1"


def build_annotation_prompt(request: AnnotationRequest) -> str:
    """Build the future multimodal prompt text.

    The mock provider does not call an LLM. This prompt is stored so future real
    providers share a constrained, evidence-only contract.
    """
    category = request.expected_category or "unknown"
    targets = ", ".join(ANNOTATION_TARGETS)
    return "\n".join(
        [
            "You are annotating visual evidence for Brand3 calibration.",
            "Return JSON only. Do not score the brand. Do not infer strategy.",
            "Use unknown when evidence is not visible in the supplied screenshot.",
            f"Brand: {request.brand_name}",
            f"Website: {request.website_url}",
            f"Expected category: {category}",
            f"Annotation targets: {targets}",
            "Each target must include label, confidence, evidence, source, limitations.",
            "Keep observations short and tied to visible evidence.",
        ]
    )
