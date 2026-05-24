"""Brand3 Visual Signature.

Visual Signature extracts structured evidence about the observable visual
behavior of a brand website. It is not yet a Brand3 scoring dimension and does
not modify scoring weights. Firecrawl is treated only as an acquisition layer;
Brand3 owns taxonomy, normalization, signal interpretation, and confidence
logic.
"""

from src.visual_signature.extract_visual_signature import extract_visual_signature

__all__ = ["extract_visual_signature"]
