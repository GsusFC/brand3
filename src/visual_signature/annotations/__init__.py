"""Offline multimodal annotation overlays for Visual Signature.

Annotations are semantic, model-shaped overlays on top of Visual Signature
evidence. They are calibration artifacts only and do not affect Brand3 scoring,
rubric dimensions, production reports, or UI.
"""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "AnnotationOverlay",
    "AnnotationRequest",
    "AnnotationStatus",
    "AnnotationTarget",
    "annotate_visual_signature",
    "build_annotation_audit",
]

_EXPORTS = {
    "AnnotationOverlay": ("src.visual_signature.annotations.types", "AnnotationOverlay"),
    "AnnotationRequest": ("src.visual_signature.annotations.types", "AnnotationRequest"),
    "AnnotationStatus": ("src.visual_signature.annotations.types", "AnnotationStatus"),
    "AnnotationTarget": ("src.visual_signature.annotations.types", "AnnotationTarget"),
    "annotate_visual_signature": ("src.visual_signature.annotations.annotate_visual_signature", "annotate_visual_signature"),
    "build_annotation_audit": ("src.visual_signature.annotations.calibration", "build_annotation_audit"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
