"""Affordance semantics for Visual Signature.

This layer classifies interaction affordances without executing mutations.
It is deterministic-first and exists as a scaffold for later policy wiring.
"""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "AFFORDANCE_EXPORT_SCHEMA_VERSION",
    "AFFORDANCE_LOCALIZATION_SCHEMA_VERSION",
    "AFFORDANCE_SEMANTICS_SCHEMA_VERSION",
    "AffordanceCategory",
    "AffordanceClassification",
    "AffordanceLocalizationDecision",
    "AffordanceLocalizationEvidence",
    "AffordanceLocalizationExport",
    "AffordanceEvidence",
    "AffordanceOwner",
    "AffordanceExport",
    "AffordancePolicy",
    "AffordancePolicyDecision",
    "build_affordance_export",
    "build_affordance_localization_export",
    "classify_affordance",
    "classify_affordances",
    "classify_affordance_owner",
    "classify_affordance_owners",
    "export_affordance_json",
    "export_affordance_localization_json",
    "resolve_affordance_policy",
]

_EXPORTS = {
    "AFFORDANCE_EXPORT_SCHEMA_VERSION": ("src.visual_signature.affordance_semantics.affordance_export", "AFFORDANCE_EXPORT_SCHEMA_VERSION"),
    "AFFORDANCE_LOCALIZATION_SCHEMA_VERSION": (
        "src.visual_signature.affordance_semantics.affordance_localization",
        "AFFORDANCE_LOCALIZATION_SCHEMA_VERSION",
    ),
    "AFFORDANCE_SEMANTICS_SCHEMA_VERSION": ("src.visual_signature.affordance_semantics.affordance_models", "AFFORDANCE_SEMANTICS_SCHEMA_VERSION"),
    "AffordanceCategory": ("src.visual_signature.affordance_semantics.affordance_models", "AffordanceCategory"),
    "AffordanceClassification": ("src.visual_signature.affordance_semantics.affordance_models", "AffordanceClassification"),
    "AffordanceLocalizationDecision": (
        "src.visual_signature.affordance_semantics.affordance_localization",
        "AffordanceLocalizationDecision",
    ),
    "AffordanceLocalizationEvidence": (
        "src.visual_signature.affordance_semantics.affordance_localization",
        "AffordanceLocalizationEvidence",
    ),
    "AffordanceLocalizationExport": (
        "src.visual_signature.affordance_semantics.affordance_localization",
        "AffordanceLocalizationExport",
    ),
    "AffordanceEvidence": ("src.visual_signature.affordance_semantics.affordance_models", "AffordanceEvidence"),
    "AffordanceOwner": ("src.visual_signature.affordance_semantics.affordance_localization", "AffordanceOwner"),
    "AffordanceExport": ("src.visual_signature.affordance_semantics.affordance_models", "AffordanceExport"),
    "AffordancePolicy": ("src.visual_signature.affordance_semantics.affordance_models", "AffordancePolicy"),
    "AffordancePolicyDecision": ("src.visual_signature.affordance_semantics.affordance_models", "AffordancePolicyDecision"),
    "build_affordance_export": ("src.visual_signature.affordance_semantics.affordance_export", "build_affordance_export"),
    "build_affordance_localization_export": (
        "src.visual_signature.affordance_semantics.affordance_localization",
        "build_affordance_localization_export",
    ),
    "classify_affordance": ("src.visual_signature.affordance_semantics.affordance_classifier", "classify_affordance"),
    "classify_affordances": ("src.visual_signature.affordance_semantics.affordance_classifier", "classify_affordances"),
    "classify_affordance_owner": ("src.visual_signature.affordance_semantics.affordance_localization", "classify_affordance_owner"),
    "classify_affordance_owners": ("src.visual_signature.affordance_semantics.affordance_localization", "classify_affordance_owners"),
    "export_affordance_json": ("src.visual_signature.affordance_semantics.affordance_export", "export_affordance_json"),
    "export_affordance_localization_json": (
        "src.visual_signature.affordance_semantics.affordance_localization",
        "export_affordance_localization_json",
    ),
    "resolve_affordance_policy": ("src.visual_signature.affordance_semantics.affordance_policy", "resolve_affordance_policy"),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
