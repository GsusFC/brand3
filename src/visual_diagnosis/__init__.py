"""Lab-only Brand3 visual diagnosis contracts.

This package is intentionally separate from scoring. It converts available
visual evidence into an explainable diagnosis candidate for validation.
"""

from src.visual_diagnosis.mapper import build_visual_diagnosis
from src.visual_diagnosis.models import VisualDiagnosis
from src.visual_diagnosis.computed_style import computed_style_snapshot_to_visual_signature
from src.visual_diagnosis.evidence import VisualEvidence, build_visual_evidence_from_local_inputs
from src.visual_diagnosis.style_capture import (
    capture_computed_style_snapshot,
    extract_computed_style_snapshot_from_page,
)

__all__ = [
    "VisualDiagnosis",
    "VisualEvidence",
    "build_visual_diagnosis",
    "build_visual_evidence_from_local_inputs",
    "capture_computed_style_snapshot",
    "computed_style_snapshot_to_visual_signature",
    "extract_computed_style_snapshot_from_page",
]
