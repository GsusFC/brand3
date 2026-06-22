"""Governance registry for Visual Signature capabilities."""

from src.visual_signature._internal.lazy import make_lazy_dir, make_lazy_getattr

__all__ = [
    "CAPABILITY_REGISTRY_SCHEMA_VERSION",
    "CapabilityEntry",
    "CapabilityRegistry",
    "CapabilityEvidenceStatus",
    "CapabilityMaturityState",
    "GOVERNANCE_SCOPE",
    "RUNTIME_POLICY_MATRIX_SCHEMA_VERSION",
    "GOVERNANCE_INTEGRITY_SCHEMA_VERSION",
    "THREE_TRACK_VALIDATION_PLAN_SCHEMA_VERSION",
    "MutationRisk",
    "build_capability_registry",
    "build_three_track_validation_plan",
    "build_runtime_policy_matrix",
    "check_governance_integrity",
    "capability_registry_markdown",
    "governance_integrity_report_markdown",
    "three_track_validation_plan_markdown",
    "runtime_policy_matrix_markdown",
    "validate_capability_registry",
    "validate_three_track_validation_plan_payload",
    "validate_runtime_policy_matrix_payload",
    "write_capability_registry",
    "write_governance_integrity_report",
    "write_three_track_validation_plan",
    "write_runtime_policy_matrix",
    "RuntimeMutationPolicy",
    "RuntimePolicy",
    "RuntimePolicyEntry",
    "RuntimePolicyMatrix",
]

_EXPORTS = {
    "CAPABILITY_REGISTRY_SCHEMA_VERSION": ("src.visual_signature.governance.capability_models", "CAPABILITY_REGISTRY_SCHEMA_VERSION"),
    "CapabilityEntry": ("src.visual_signature.governance.capability_models", "CapabilityEntry"),
    "CapabilityRegistry": ("src.visual_signature.governance.capability_models", "CapabilityRegistry"),
    "CapabilityEvidenceStatus": ("src.visual_signature.governance.capability_models", "CapabilityEvidenceStatus"),
    "CapabilityMaturityState": ("src.visual_signature.governance.capability_models", "CapabilityMaturityState"),
    "MutationRisk": ("src.visual_signature.governance.capability_models", "MutationRisk"),
    "validate_capability_registry": ("src.visual_signature.governance.capability_models", "validate_capability_registry"),
    "GOVERNANCE_SCOPE": ("src.visual_signature.governance.capability_registry", "GOVERNANCE_SCOPE"),
    "build_capability_registry": ("src.visual_signature.governance.capability_registry", "build_capability_registry"),
    "capability_registry_markdown": ("src.visual_signature.governance.capability_registry", "capability_registry_markdown"),
    "write_capability_registry": ("src.visual_signature.governance.capability_registry", "write_capability_registry"),
    "build_runtime_policy_matrix": ("src.visual_signature.governance.runtime_policy_matrix", "build_runtime_policy_matrix"),
    "runtime_policy_matrix_markdown": ("src.visual_signature.governance.runtime_policy_matrix", "runtime_policy_matrix_markdown"),
    "write_runtime_policy_matrix": ("src.visual_signature.governance.runtime_policy_matrix", "write_runtime_policy_matrix"),
    "GOVERNANCE_INTEGRITY_SCHEMA_VERSION": ("src.visual_signature.governance.governance_integrity", "GOVERNANCE_INTEGRITY_SCHEMA_VERSION"),
    "check_governance_integrity": ("src.visual_signature.governance.governance_integrity", "check_governance_integrity"),
    "governance_integrity_report_markdown": ("src.visual_signature.governance.governance_integrity", "governance_integrity_report_markdown"),
    "write_governance_integrity_report": ("src.visual_signature.governance.governance_integrity", "write_governance_integrity_report"),
    "THREE_TRACK_VALIDATION_PLAN_SCHEMA_VERSION": (
        "src.visual_signature.governance.three_track_validation_plan",
        "THREE_TRACK_VALIDATION_PLAN_SCHEMA_VERSION",
    ),
    "build_three_track_validation_plan": (
        "src.visual_signature.governance.three_track_validation_plan",
        "build_three_track_validation_plan",
    ),
    "three_track_validation_plan_markdown": (
        "src.visual_signature.governance.three_track_validation_plan",
        "three_track_validation_plan_markdown",
    ),
    "validate_three_track_validation_plan_payload": (
        "src.visual_signature.governance.three_track_validation_plan",
        "validate_three_track_validation_plan_payload",
    ),
    "write_three_track_validation_plan": ("src.visual_signature.governance.three_track_validation_plan", "write_three_track_validation_plan"),
    "RUNTIME_POLICY_MATRIX_SCHEMA_VERSION": ("src.visual_signature.governance.runtime_policy_models", "RUNTIME_POLICY_MATRIX_SCHEMA_VERSION"),
    "RuntimeMutationPolicy": ("src.visual_signature.governance.runtime_policy_models", "RuntimeMutationPolicy"),
    "RuntimePolicy": ("src.visual_signature.governance.runtime_policy_models", "RuntimePolicy"),
    "RuntimePolicyEntry": ("src.visual_signature.governance.runtime_policy_models", "RuntimePolicyEntry"),
    "RuntimePolicyMatrix": ("src.visual_signature.governance.runtime_policy_models", "RuntimePolicyMatrix"),
    "validate_runtime_policy_matrix_payload": (
        "src.visual_signature.governance.runtime_policy_models",
        "validate_runtime_policy_matrix_payload",
    ),
}

__getattr__ = make_lazy_getattr(globals(), _EXPORTS)
__dir__ = make_lazy_dir(globals(), _EXPORTS)
