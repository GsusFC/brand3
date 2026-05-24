"""Policy helpers for affordance semantics.

This layer decides whether a classified affordance is safe to dismiss,
unsafe to mutate, or requires human review. It does not execute any action.
"""

from __future__ import annotations

from typing import Any

from src.visual_signature.affordance_semantics.affordance_models import (
    AffordanceCategory,
    AffordanceEvidence,
    AffordancePolicy,
    AffordancePolicyDecision,
)


CONSENT_CONTEXT_TOKENS = {
    "cookie",
    "consent",
    "privacy",
    "gdpr",
    "cmp",
    "onetrust",
    "trustarc",
    "usercentrics",
}

SAFE_DISMISS_CATEGORIES = {"close_control", "dismiss_control"}
UNSAFE_TO_MUTATE_CATEGORIES = {
    "login_action",
    "subscription_action",
    "checkout_action",
    "external_navigation",
}
REVIEW_REQUIRED_CATEGORIES = {"ambiguous_action", "unknown_action"}
CONSENT_CATEGORIES = {"consent_accept", "consent_reject"}


def resolve_affordance_policy(
    category: AffordanceCategory,
    evidence: AffordanceEvidence | dict[str, Any] | None = None,
) -> AffordancePolicyDecision:
    evidence_model = _evidence_model(evidence)
    consent_context = _has_consent_context(evidence_model)
    policy, confidence, limitations, notes = _base_policy(category, evidence_model, consent_context)
    review_required = policy == "requires_human_review"
    return AffordancePolicyDecision(
        category=category,
        policy=policy,
        confidence=confidence,
        review_required=review_required,
        limitations=limitations,
        notes=notes,
    )


def _base_policy(
    category: AffordanceCategory,
    evidence: AffordanceEvidence,
    consent_context: bool,
) -> tuple[AffordancePolicy, float, list[str], list[str]]:
    limitations: list[str] = []
    notes: list[str] = []

    if category in SAFE_DISMISS_CATEGORIES:
        return "safe_to_dismiss", 0.95, limitations, notes

    if category in UNSAFE_TO_MUTATE_CATEGORIES:
        notes.append("interaction_changes_state_or_navigates")
        return "unsafe_to_mutate", 0.9, limitations, notes

    if category in CONSENT_CATEGORIES:
        if consent_context:
            notes.append("consent_context_detected")
            return "safe_to_dismiss", 0.78, limitations, notes
        limitations.append("consent_context_missing")
        notes.append("consent_action_requires_context")
        return "requires_human_review", 0.45, limitations, notes

    if category in REVIEW_REQUIRED_CATEGORIES:
        limitations.append("affordance_is_ambiguous")
        notes.append("ambiguous_affordance_requires_review")
        return "requires_human_review", 0.35, limitations, notes

    limitations.append("unknown_affordance_category")
    notes.append("affordance_category_unrecognized")
    return "requires_human_review", 0.25, limitations, notes


def _has_consent_context(evidence: AffordanceEvidence) -> bool:
    tokens = {
        _normalize(value)
        for values in (
            evidence.visible_text,
            evidence.aria_labels,
            evidence.titles,
            evidence.roles,
            evidence.svg_icon_semantics,
            evidence.dom_context,
            evidence.overlay_context,
        )
        for value in values
    }
    return any(token in CONSENT_CONTEXT_TOKENS for token in tokens)


def _evidence_model(value: AffordanceEvidence | dict[str, Any] | None) -> AffordanceEvidence:
    if isinstance(value, AffordanceEvidence):
        return value
    if isinstance(value, dict):
        return AffordanceEvidence.from_mapping(value)
    return AffordanceEvidence()


def _normalize(value: str) -> str:
    return " ".join((value or "").lower().replace("-", " ").replace("/", " ").split())
