"""Lab-only Brand3 visual diagnosis contracts.

This package is intentionally separate from scoring. It converts available
visual evidence into an explainable diagnosis candidate for validation.
"""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "VisualDiagnosis",
    "VisualEvidenceBundle",
    "VisualEvidenceSource",
    "VisualSignalProvenance",
    "VisualEvidence",
    "fuse_visual_signature_payloads",
    "build_visual_diagnosis",
    "build_clean_capture_decision",
    "build_visual_evidence_from_local_inputs",
    "clean_attempt_quality",
    "capture_computed_style_snapshot",
    "computed_style_snapshot_to_visual_signature",
    "enrich_visual_signature_with_local_screenshot",
    "screenshot_capture_to_visual_signature",
    "extract_computed_style_snapshot_from_page",
    "build_signal_provenance",
]

_EXPORTS = {
    "VisualDiagnosis": ("src.visual_signature.capture.models", "VisualDiagnosis"),
    "VisualEvidenceBundle": ("src.visual_signature.capture.visual_evidence", "VisualEvidenceBundle"),
    "VisualEvidenceSource": ("src.visual_signature.capture.visual_evidence", "VisualEvidenceSource"),
    "VisualSignalProvenance": ("src.visual_signature.capture.provenance", "VisualSignalProvenance"),
    "VisualEvidence": ("src.visual_signature.capture.visual_evidence", "VisualEvidence"),
    "fuse_visual_signature_payloads": (
        "src.visual_signature.capture.visual_evidence",
        "fuse_visual_signature_payloads",
    ),
    "build_visual_diagnosis": ("src.visual_signature.capture.mapper", "build_visual_diagnosis"),
    "build_clean_capture_decision": ("src.visual_signature.capture.clean_capture", "build_clean_capture_decision"),
    "build_visual_evidence_from_local_inputs": (
        "src.visual_signature.capture.visual_evidence",
        "build_visual_evidence_from_local_inputs",
    ),
    "capture_computed_style_snapshot": ("src.visual_signature.capture.computed_style", "capture_computed_style_snapshot"),
    "clean_attempt_quality": ("src.visual_signature.capture.clean_capture", "clean_attempt_quality"),
    "computed_style_snapshot_to_visual_signature": (
        "src.visual_signature.capture.computed_style",
        "computed_style_snapshot_to_visual_signature",
    ),
    "enrich_visual_signature_with_local_screenshot": (
        "src.visual_signature.capture.visual_evidence",
        "enrich_visual_signature_with_local_screenshot",
    ),
    "screenshot_capture_to_visual_signature": (
        "src.visual_signature.capture.visual_evidence",
        "screenshot_capture_to_visual_signature",
    ),
    "extract_computed_style_snapshot_from_page": (
        "src.visual_signature.capture.computed_style",
        "extract_computed_style_snapshot_from_page",
    ),
    "build_signal_provenance": ("src.visual_signature.capture.provenance", "build_signal_provenance"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
