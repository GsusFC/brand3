"""Local static Visual Signature platform."""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

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

_EXPORTS = {
    "DEFAULT_OUTPUT_ROOT": ("src.visual_signature.platform.platform_builder", "DEFAULT_OUTPUT_ROOT"),
    "DEFAULT_SCORING_OUTPUT_ROOT": ("src.visual_signature.platform.platform_builder", "DEFAULT_SCORING_OUTPUT_ROOT"),
    "PROJECT_ROOT": ("src.visual_signature.platform.platform_builder", "PROJECT_ROOT"),
    "VISUAL_SIGNATURE_PLATFORM_RECORD_TYPE": (
        "src.visual_signature.platform.platform_builder",
        "VISUAL_SIGNATURE_PLATFORM_RECORD_TYPE",
    ),
    "VISUAL_SIGNATURE_PLATFORM_SCHEMA_VERSION": (
        "src.visual_signature.platform.platform_builder",
        "VISUAL_SIGNATURE_PLATFORM_SCHEMA_VERSION",
    ),
    "PlatformArtifact": ("src.visual_signature.platform.platform_models", "PlatformArtifact"),
    "PlatformBundle": ("src.visual_signature.platform.platform_models", "PlatformBundle"),
    "PlatformSection": ("src.visual_signature.platform.platform_models", "PlatformSection"),
    "build_platform_bundle": ("src.visual_signature.platform.platform_builder", "build_platform_bundle"),
    "validate_platform_bundle": ("src.visual_signature.platform.platform_builder", "validate_platform_bundle"),
    "write_platform_bundle": ("src.visual_signature.platform.platform_builder", "write_platform_bundle"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
