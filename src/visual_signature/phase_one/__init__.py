"""Phase One: adapt real capture outputs into Phase Zero records."""

from pathlib import Path

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

PHASE_ONE_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "phase_one"

__all__ = [
    "PHASE_ONE_ROOT",
    "build_phase_one_bundle",
    "export_phase_one_bundle",
    "load_phase_one_sources",
    "validate_phase_one_output_root",
]

_EXPORTS = {
    "build_phase_one_bundle": ("src.visual_signature.phase_one.builder", "build_phase_one_bundle"),
    "export_phase_one_bundle": ("src.visual_signature.phase_one.export", "export_phase_one_bundle"),
    "load_phase_one_sources": ("src.visual_signature.phase_one.adapter", "load_phase_one_sources"),
    "validate_phase_one_output_root": ("src.visual_signature.phase_one.validation", "validate_phase_one_output_root"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
