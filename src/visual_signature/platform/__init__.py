"""Local static Visual Signature platform."""

from src.visual_signature.platform.platform_builder import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SCORING_OUTPUT_ROOT,
    PROJECT_ROOT,
    VISUAL_SIGNATURE_PLATFORM_RECORD_TYPE,
    VISUAL_SIGNATURE_PLATFORM_SCHEMA_VERSION,
    build_platform_bundle,
    validate_platform_bundle,
    write_platform_bundle,
)
from src.visual_signature.platform.platform_models import (
    PlatformArtifact,
    PlatformBundle,
    PlatformSection,
)

__all__ = [
    "DEFAULT_OUTPUT_ROOT",
    "DEFAULT_SCORING_OUTPUT_ROOT",
    "PROJECT_ROOT",
    "VISUAL_SIGNATURE_PLATFORM_RECORD_TYPE",
    "VISUAL_SIGNATURE_PLATFORM_SCHEMA_VERSION",
    "PlatformArtifact",
    "PlatformBundle",
    "PlatformSection",
    "build_platform_bundle",
    "validate_platform_bundle",
    "write_platform_bundle",
]
