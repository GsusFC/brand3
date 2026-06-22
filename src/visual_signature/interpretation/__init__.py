"""Lab-only visual interpretation contracts and Gemini runner helpers."""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "GeminiVisionClient",
    "InterpretationValidation",
    "VISUAL_EVIDENCE_PACK_SCHEMA_VERSION",
    "VISUAL_INTERPRETATION_SCHEMA_VERSION",
    "VisualEvidencePack",
    "VisualInterpretation",
    "validate_visual_interpretation",
]

_EXPORTS = {
    "GeminiVisionClient": ("src.visual_signature.interpretation.gemini", "GeminiVisionClient"),
    "InterpretationValidation": ("src.visual_signature.interpretation.validation", "InterpretationValidation"),
    "VISUAL_EVIDENCE_PACK_SCHEMA_VERSION": (
        "src.visual_signature.interpretation.models",
        "VISUAL_EVIDENCE_PACK_SCHEMA_VERSION",
    ),
    "VISUAL_INTERPRETATION_SCHEMA_VERSION": (
        "src.visual_signature.interpretation.models",
        "VISUAL_INTERPRETATION_SCHEMA_VERSION",
    ),
    "VisualEvidencePack": ("src.visual_signature.interpretation.models", "VisualEvidencePack"),
    "VisualInterpretation": ("src.visual_signature.interpretation.models", "VisualInterpretation"),
    "validate_visual_interpretation": ("src.visual_signature.interpretation.validation", "validate_visual_interpretation"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
