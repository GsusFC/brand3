"""Brand3 Visual Signature.

Visual Signature extracts structured evidence about the observable visual
behavior of a brand website. It is not yet a Brand3 scoring dimension and does
not modify scoring weights. Firecrawl is treated only as an acquisition layer;
Brand3 owns taxonomy, normalization, signal interpretation, and confidence
logic. The scanner contract can produce its own visual score for evidence
review without changing the global Brand3 score.
"""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr
from src.visual_signature.extract_visual_signature import extract_visual_signature

__all__ = [
    "build_visual_signature_evidence_v1",
    "build_visual_signature_scan",
    "extract_visual_signature",
    "run_visual_signature_scan",
]

_EXPORTS = {
    "build_visual_signature_evidence_v1": (
        "src.visual_signature.evidence",
        "build_visual_signature_evidence_v1",
    ),
    "build_visual_signature_scan": ("src.visual_signature.scan", "build_visual_signature_scan"),
    "extract_visual_signature": ("src.visual_signature.extract_visual_signature", "extract_visual_signature"),
    "run_visual_signature_scan": ("src.visual_signature.scan", "run_visual_signature_scan"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
