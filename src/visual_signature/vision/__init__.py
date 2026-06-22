"""Local screenshot-derived Vision Enrichment for Visual Signature.

Vision Enrichment is an additive evidence layer. It does not affect Brand3
scoring, rubric dimensions, reports, or production behavior.
"""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = ["analyze_viewport_obstruction", "enrich_visual_signature_with_vision"]

_EXPORTS = {
    "analyze_viewport_obstruction": ("src.visual_signature.vision.viewport_obstruction", "analyze_viewport_obstruction"),
    "enrich_visual_signature_with_vision": (
        "src.visual_signature.vision.enrich_visual_signature",
        "enrich_visual_signature_with_vision",
    ),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
