"""Public viewport obstruction API for Visual Signature."""

from src.visual_signature._internal.viewport_obstruction_heuristics import ObstructionSeverity
from src.visual_signature._internal.viewport_obstruction_heuristics import ObstructionType
from src.visual_signature._internal.viewport_obstruction_heuristics import ViewportObstructionEvidence
from src.visual_signature._internal.viewport_obstruction_heuristics import analyze_viewport_obstruction

__all__ = [
    "ObstructionSeverity",
    "ObstructionType",
    "ViewportObstructionEvidence",
    "analyze_viewport_obstruction",
]
