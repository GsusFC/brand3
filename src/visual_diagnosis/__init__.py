"""Lab-only Brand3 visual diagnosis contracts.

This package is intentionally separate from scoring. It converts available
visual evidence into an explainable diagnosis candidate for validation.
"""

from src.visual_diagnosis.mapper import build_visual_diagnosis
from src.visual_diagnosis.models import VisualDiagnosis

__all__ = ["VisualDiagnosis", "build_visual_diagnosis"]
