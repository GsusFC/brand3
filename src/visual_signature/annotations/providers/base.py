"""Provider protocol for offline Visual Signature annotations."""

from __future__ import annotations

from typing import Protocol

from src.visual_signature.annotations.types import AnnotationProviderResult, AnnotationRequest


class MultimodalAnnotationProvider(Protocol):
    """Protocol implemented by annotation providers.

    Implementations must return structured annotations only. Real API providers
    are intentionally out of scope for the offline scaffold.
    """

    name: str
    model: str

    def annotate(self, request: AnnotationRequest) -> AnnotationProviderResult:
        ...
