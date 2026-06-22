"""Annotation provider implementations."""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = ["MockMultimodalAnnotationProvider"]

_EXPORTS = {
    "MockMultimodalAnnotationProvider": (
        "src.visual_signature.annotations.providers.mock_provider",
        "MockMultimodalAnnotationProvider",
    ),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
