"""Annotation provider implementations."""

from src.visual_signature.annotations.providers.base import MultimodalAnnotationProvider
from src.visual_signature.annotations.providers.mock_provider import MockMultimodalAnnotationProvider

__all__ = ["MockMultimodalAnnotationProvider", "MultimodalAnnotationProvider"]
