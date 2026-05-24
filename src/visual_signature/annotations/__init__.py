"""Offline multimodal annotation overlays for Visual Signature.

Annotations are semantic, model-shaped overlays on top of Visual Signature
evidence. They are calibration artifacts only and do not affect Brand3 scoring,
rubric dimensions, production reports, or UI.
"""

from src.visual_signature.annotations.annotate_visual_signature import annotate_visual_signature
from src.visual_signature.annotations.calibration import build_annotation_audit
from src.visual_signature.annotations.types import (
    AnnotationOverlay,
    AnnotationRequest,
    AnnotationStatus,
    AnnotationTarget,
)

__all__ = [
    "AnnotationOverlay",
    "AnnotationRequest",
    "AnnotationStatus",
    "AnnotationTarget",
    "annotate_visual_signature",
    "build_annotation_audit",
]
