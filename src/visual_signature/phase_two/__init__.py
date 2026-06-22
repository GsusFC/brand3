"""Phase Two: join Phase One records with explicit human review."""

from __future__ import annotations

from pathlib import Path

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

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

_EXPORTS = {
    "build_phase_two_bundle": ("src.visual_signature.phase_two.builder", "build_phase_two_bundle"),
    "export_phase_two_bundle": ("src.visual_signature.phase_two.export", "export_phase_two_bundle"),
    "join_phase_one_and_reviews": ("src.visual_signature.phase_two.builder", "join_phase_one_and_reviews"),
    "load_phase_one_eligibility_records": (
        "src.visual_signature.phase_two.adapter",
        "load_phase_one_eligibility_records",
    ),
    "load_review_records": ("src.visual_signature.phase_two.adapter", "load_review_records"),
    "validate_phase_two_output_root": ("src.visual_signature.phase_two.validation", "validate_phase_two_output_root"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
