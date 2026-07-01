"""Brand3 Visual Acquisition Layer, implemented in the legacy Visual Signature package.

This layer extracts structured evidence about the observable visual behavior of
a brand website. It is not yet a Brand3 scoring dimension; it is acquisition
infrastructure and must not modify scoring weights.
Firecrawl is treated only as an acquisition layer.
The public naming should move toward Visual Acquisition Layer and visual
evidence packets while this package keeps legacy imports stable.
"""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr
from src.visual_signature.extract_visual_signature import extract_visual_signature

__all__ = [
    "build_visual_signature_evidence_v1",
    "build_visual_signature_scan",
    "extract_visual_signature",
    "run_visual_signature_scan",
    "VISUAL_ACQUISITION_LAYER_NAME",
    "VISUAL_ACQUISITION_RAW_SOURCE",
    "VISUAL_EVIDENCE_PACKET_KEY",
]

_EXPORTS = {
    "VISUAL_ACQUISITION_LAYER_NAME": (
        "src.visual_signature.acquisition_contract",
        "VISUAL_ACQUISITION_LAYER_NAME",
    ),
    "VISUAL_ACQUISITION_RAW_SOURCE": (
        "src.visual_signature.acquisition_contract",
        "VISUAL_ACQUISITION_RAW_SOURCE",
    ),
    "VISUAL_EVIDENCE_PACKET_KEY": (
        "src.visual_signature.acquisition_contract",
        "VISUAL_EVIDENCE_PACKET_KEY",
    ),
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
