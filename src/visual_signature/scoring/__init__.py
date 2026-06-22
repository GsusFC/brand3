from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = ["calculate_extraction_confidence"]

_EXPORTS = {
    "calculate_extraction_confidence": (
        "src.visual_signature.scoring.extraction_confidence",
        "calculate_extraction_confidence",
    ),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
