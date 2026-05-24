"""Phase Two: join Phase One records with explicit human review."""

from __future__ import annotations

from pathlib import Path

from src.visual_signature.phase_two.adapter import load_phase_one_eligibility_records, load_review_records
from src.visual_signature.phase_two.builder import build_phase_two_bundle, join_phase_one_and_reviews
from src.visual_signature.phase_two.export import export_phase_two_bundle
from src.visual_signature.phase_two.validation import validate_phase_two_output_root

PHASE_TWO_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "phase_two"

__all__ = [
    "PHASE_TWO_ROOT",
    "build_phase_two_bundle",
    "export_phase_two_bundle",
    "join_phase_one_and_reviews",
    "load_phase_one_eligibility_records",
    "load_review_records",
    "validate_phase_two_output_root",
]
