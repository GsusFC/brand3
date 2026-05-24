"""Local screenshot-derived Vision Enrichment for Visual Signature.

Vision Enrichment is an additive evidence layer. It does not affect Brand3
scoring, rubric dimensions, reports, or production behavior.
"""

from src.visual_signature.vision.enrich_visual_signature import enrich_visual_signature_with_vision
from src.visual_signature.vision.viewport_obstruction import analyze_viewport_obstruction

__all__ = ["analyze_viewport_obstruction", "enrich_visual_signature_with_vision"]
