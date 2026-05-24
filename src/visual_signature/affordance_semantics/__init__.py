"""Affordance semantics for Visual Signature.

This layer classifies interaction affordances without executing mutations.
It is deterministic-first and exists as a scaffold for later policy wiring.
"""

from src.visual_signature.affordance_semantics.affordance_classifier import (
    classify_affordance,
    classify_affordances,
)
from src.visual_signature.affordance_semantics.affordance_localization import (
    AFFORDANCE_LOCALIZATION_SCHEMA_VERSION,
    AffordanceLocalizationDecision,
    AffordanceLocalizationEvidence,
    AffordanceLocalizationExport,
    AffordanceOwner,
    build_affordance_localization_export,
    classify_affordance_owner,
    classify_affordance_owners,
    export_affordance_localization_json,
)
from src.visual_signature.affordance_semantics.affordance_export import (
    AFFORDANCE_EXPORT_SCHEMA_VERSION,
    build_affordance_export,
    export_affordance_json,
)
from src.visual_signature.affordance_semantics.affordance_models import (
    AFFORDANCE_SEMANTICS_SCHEMA_VERSION,
    AffordanceClassification,
    AffordanceEvidence,
    AffordanceExport,
    AffordancePolicy,
    AffordanceCategory,
    AffordancePolicyDecision,
)
from src.visual_signature.affordance_semantics.affordance_policy import resolve_affordance_policy

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
