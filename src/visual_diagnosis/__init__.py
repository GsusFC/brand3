"""Lab-only Brand3 visual diagnosis contracts.

This package is intentionally separate from scoring. It converts available
visual evidence into an explainable diagnosis candidate for validation.
"""

from src.visual_diagnosis.mapper import build_visual_diagnosis
from src.visual_diagnosis.models import VisualDiagnosis
from src.visual_diagnosis.computed_style import computed_style_snapshot_to_visual_signature
from src.visual_diagnosis.clean_capture import build_clean_capture_decision, clean_attempt_quality
from src.visual_diagnosis.bundle import VisualEvidenceBundle, VisualEvidenceSource
from src.visual_diagnosis.evidence import (
    VisualEvidence,
    build_visual_evidence_from_local_inputs,
    enrich_visual_signature_with_local_screenshot,
)
from src.visual_diagnosis.style_capture import (
    capture_computed_style_snapshot,
    extract_computed_style_snapshot_from_page,
)
from src.visual_diagnosis.provenance import VisualSignalProvenance, build_signal_provenance

__all__ = [
    "VisualDiagnosis",
    "VisualEvidenceBundle",
    "VisualEvidenceSource",
    "VisualSignalProvenance",
    "VisualEvidence",
    "build_visual_diagnosis",
    "build_clean_capture_decision",
    "build_visual_evidence_from_local_inputs",
    "clean_attempt_quality",
    "capture_computed_style_snapshot",
    "computed_style_snapshot_to_visual_signature",
    "enrich_visual_signature_with_local_screenshot",
    "extract_computed_style_snapshot_from_page",
    "build_signal_provenance",
]
