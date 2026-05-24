"""Phase One: adapt real capture outputs into Phase Zero records."""

from src.visual_signature.phase_one.adapter import load_phase_one_sources
from src.visual_signature.phase_one.builder import build_phase_one_bundle
from src.visual_signature.phase_one.export import export_phase_one_bundle
from src.visual_signature.phase_one.validation import validate_phase_one_output_root

from pathlib import Path

PHASE_ONE_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "phase_one"

__all__ = [
    "PHASE_ONE_ROOT",
    "build_phase_one_bundle",
    "export_phase_one_bundle",
    "load_phase_one_sources",
    "validate_phase_one_output_root",
]
