"""Deterministic affordance classification for Visual Signature."""

from __future__ import annotations

from typing import Any, Iterable

from src.visual_signature.affordance_semantics.affordance_models import (
    AFFORDANCE_SEMANTICS_SCHEMA_VERSION,
    AffordanceClassification,
    AffordanceEvidence,
)
from src.visual_signature.affordance_semantics.affordance_policy import resolve_affordance_policy


def classify_affordance(evidence: dict[str, Any], *, affordance_id: str | None = None) -> AffordanceClassification:
    model = AffordanceEvidence.from_mapping(evidence)
    category, confidence, signals, limitations = _classify(model)
    policy = resolve_affordance_policy(category, model)
    classification = AffordanceClassification(
        schema_version=AFFORDANCE_SEMANTICS_SCHEMA_VERSION,
        record_type="affordance_classification",
        affordance_id=affordance_id or _affordance_id(model, category),
        category=category,
        policy=policy.policy,
        confidence=min(1.0, round(max(confidence, policy.confidence), 3)),
        evidence=model,
        evidence_sources=_evidence_sources(model),
        matched_signals=signals,
        limitations=_dedupe([*limitations, *policy.limitations]),
        review_required=policy.review_required,
        notes=policy.notes,
    )
    return classification


def classify_affordances(items: Iterable[dict[str, Any]]) -> list[AffordanceClassification]:
    return [classify_affordance(item) for item in items]


def _classify(evidence: AffordanceEvidence) -> tuple[str, float, list[str], list[str]]:
    signals: list[str] = []
    limitations: list[str] = []
    tokens = _candidate_tokens(evidence)
    consent_context = _has_consent_context(evidence)

    category = _classify_close_or_dismiss(evidence, tokens, signals, limitations)
    if category:
        return category

    category = _classify_checkout(evidence, tokens, signals, limitations)
    if category:
        return category

    category = _classify_login(evidence, tokens, signals, limitations)
    if category:
        return category

    category = _classify_subscription(evidence, tokens, signals, limitations)
    if category:
        return category

    category = _classify_external_navigation(evidence, tokens, signals, limitations)
    if category:
        return category

    category = _classify_consent(evidence, tokens, consent_context, signals, limitations)
    if category:
        return category

    if any(token in AMBIGUOUS_TOKENS for token in tokens):
        signals.append("text:ambiguous")
        limitations.append("generic_action_label")
        return "ambiguous_action", 0.38, signals, limitations

    if tokens:
        signals.append("context:insufficient_for_confident_classification")
    limitations.append("no_deterministic_match")
    return "unknown_action", 0.2, signals, limitations


def _classify_close_or_dismiss(
    evidence: AffordanceEvidence,
    tokens: set[str],
    signals: list[str],
    limitations: list[str],
) -> tuple[str, float, list[str], list[str]] | None:
    aria_or_title_tokens = _normalized_tokens([*evidence.aria_labels, *evidence.titles])
    if _matches_any_phrase(aria_or_title_tokens, DISMISS_TOKENS):
        signals.append("aria_or_title:close_or_dismiss")
        return "dismiss_control", 0.92, signals, limitations
    if _matches_any_phrase(aria_or_title_tokens, CLOSE_TOKENS):
        signals.append("aria_or_title:close_or_dismiss")
        category = "close_control"
        return category, 0.92, signals, limitations
    semantics = _normalized_semantics(evidence.svg_icon_semantics)
    if "dismiss" in semantics or "x" in semantics:
        signals.append("svg_icon_semantics:close_or_dismiss")
        return "dismiss_control", 0.9, signals, limitations
    if "close" in semantics:
        signals.append("svg_icon_semantics:close_or_dismiss")
        return "close_control", 0.9, signals, limitations
    if _matches_any_phrase(tokens, DISMISS_TOKENS):
        signals.append("text_or_context:dismiss")
        return "dismiss_control", 0.95, signals, limitations
    if _matches_any_phrase(tokens, CLOSE_TOKENS):
        signals.append("text_or_context:close")
        return "close_control", 0.96, signals, limitations
    return None


def _classify_consent(
    evidence: AffordanceEvidence,
    tokens: set[str],
    consent_context: bool,
    signals: list[str],
    limitations: list[str],
) -> tuple[str, float, list[str], list[str]] | None:
    accept = _matches_any_phrase(tokens, CONSENT_ACCEPT_TOKENS)
    reject = _matches_any_phrase(tokens, CONSENT_REJECT_TOKENS)
    if not accept and not reject:
        return None
    if not consent_context:
        limitations.append("consent_context_required")
        signals.append("text:consent_without_context")
        return "ambiguous_action", 0.44, signals, limitations
    if reject:
        signals.append("text:consent_reject")
        return "consent_reject", 0.9, signals, limitations
    signals.append("text:consent_accept")
    if "continue" in tokens:
        limitations.append("generic_continue_inside_consent_context")
        return "consent_accept", 0.72, signals, limitations
    return "consent_accept", 0.94, signals, limitations


def _classify_login(
    evidence: AffordanceEvidence,
    tokens: set[str],
    signals: list[str],
    limitations: list[str],
) -> tuple[str, float, list[str], list[str]] | None:
    if _matches_any_phrase(tokens, LOGIN_TOKENS):
        signals.append("text_or_context:login")
        limitations.append("stateful_auth_action")
        return "login_action", 0.93, signals, limitations
    return None


def _classify_subscription(
    evidence: AffordanceEvidence,
    tokens: set[str],
    signals: list[str],
    limitations: list[str],
) -> tuple[str, float, list[str], list[str]] | None:
    if _matches_any_phrase(tokens, SUBSCRIPTION_TOKENS):
        signals.append("text_or_context:subscription")
        limitations.append("stateful_subscription_action")
        return "subscription_action", 0.92, signals, limitations
    return None


def _classify_checkout(
    evidence: AffordanceEvidence,
    tokens: set[str],
    signals: list[str],
    limitations: list[str],
) -> tuple[str, float, list[str], list[str]] | None:
    if _matches_any_phrase(tokens, CHECKOUT_TOKENS):
        signals.append("text_or_context:checkout")
        limitations.append("purchase_flow_action")
        return "checkout_action", 0.94, signals, limitations
    if "continue" in tokens and any(token in CHECKOUT_CONTEXT_TOKENS for token in _normalized_context(evidence)):
        signals.append("context:continue_to_checkout")
        limitations.append("purchase_flow_context")
        return "checkout_action", 0.91, signals, limitations
    return None


def _classify_external_navigation(
    evidence: AffordanceEvidence,
    tokens: set[str],
    signals: list[str],
    limitations: list[str],
) -> tuple[str, float, list[str], list[str]] | None:
    if _matches_any_phrase(tokens, EXTERNAL_NAVIGATION_TOKENS):
        signals.append("text_or_context:external_navigation")
        limitations.append("navigates_away_from_current_view")
        return "external_navigation", 0.87, signals, limitations
    if any(token in {"external-link", "external_link"} for token in _normalized_semantics(evidence.svg_icon_semantics)):
        signals.append("svg_icon_semantics:external_link")
        limitations.append("navigates_away_from_current_view")
        return "external_navigation", 0.85, signals, limitations
    if "link" in _normalized_roles(evidence.roles) and any(token in EXTERNAL_NAVIGATION_TOKENS for token in _normalized_tokens(evidence.visible_text + evidence.titles)):
        signals.append("role:link_with_navigation_cta")
        limitations.append("navigates_away_from_current_view")
        return "external_navigation", 0.8, signals, limitations
    return None


def _candidate_tokens(evidence: AffordanceEvidence) -> set[str]:
    values = (
        evidence.visible_text
        + evidence.aria_labels
        + evidence.titles
        + evidence.roles
        + evidence.svg_icon_semantics
        + evidence.dom_context
        + evidence.overlay_context
    )
    return _normalized_tokens(values)


def _normalized_tokens(values: Iterable[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = _normalize(value)
        if text:
            tokens.add(text)
    return tokens


def _normalized_roles(values: list[str]) -> set[str]:
    return {token for token in _normalized_tokens(values) if token in {"button", "link", "menuitem"}}


def _normalized_semantics(values: list[str]) -> set[str]:
    return _normalized_tokens(values)


def _normalized_context(evidence: AffordanceEvidence) -> set[str]:
    return _normalized_tokens([*evidence.dom_context, *evidence.overlay_context])


def _matches_any_phrase(tokens: set[str], phrases: set[str]) -> bool:
    for token in tokens:
        for phrase in phrases:
            if _token_matches_phrase(token, phrase):
                return True
    return False


def _token_matches_phrase(token: str, phrase: str) -> bool:
    token = _normalize(token)
    phrase = _normalize(phrase)
    return token == phrase or token.startswith(f"{phrase} ")


def _has_consent_context(evidence: AffordanceEvidence) -> bool:
    return any(token in CONSENT_CONTEXT_TOKENS for token in _normalized_context(evidence))


def _evidence_sources(evidence: AffordanceEvidence) -> list[str]:
    sources: list[str] = []
    if evidence.visible_text:
        sources.append("visible_text")
    if evidence.aria_labels:
        sources.append("aria_label")
    if evidence.titles:
        sources.append("title")
    if evidence.roles:
        sources.append("role")
    if evidence.svg_icon_semantics:
        sources.append("svg_icon_semantics")
    if evidence.dom_context:
        sources.append("dom_context")
    if evidence.overlay_context:
        sources.append("overlay_context")
    return sources


def _affordance_id(evidence: AffordanceEvidence, category: str) -> str:
    primary = next(iter(evidence.visible_text or evidence.aria_labels or evidence.titles or evidence.svg_icon_semantics or [category]))
    return _slug(f"{category}-{primary}")


def _slug(value: str) -> str:
    out: list[str] = []
    for char in value.lower().strip():
        if char.isalnum():
            out.append(char)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-") or "affordance"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _normalize(value: str) -> str:
    return " ".join(
        "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in (value or "").lower().replace("-", " ").replace("/", " "))
        .split()
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

CLOSE_TOKENS = {
    "close",
    "close dialog",
    "close modal",
    "close banner",
    "close popup",
    "close window",
}

DISMISS_TOKENS = {
    "dismiss",
    "dismiss dialog",
    "dismiss modal",
    "dismiss banner",
    "dismiss popup",
}

CONSENT_ACCEPT_TOKENS = {
    "accept all",
    "accept",
    "allow all",
    "agree",
    "i agree",
    "ok",
    "got it",
    "continue",
}

CONSENT_REJECT_TOKENS = {
    "reject all",
    "reject",
    "decline",
    "no thanks",
    "not now",
}

LOGIN_TOKENS = {
    "log in",
    "login",
    "sign in",
    "sign in now",
    "create account",
    "register",
    "sign up",
    "join",
    "join now",
}

SUBSCRIPTION_TOKENS = {
    "subscribe",
    "subscribe now",
    "newsletter signup",
    "sign up for newsletter",
    "get updates",
    "join newsletter",
}

CHECKOUT_TOKENS = {
    "checkout",
    "continue to checkout",
    "proceed to checkout",
    "continue to payment",
    "buy now",
    "complete purchase",
    "pay now",
}

EXTERNAL_NAVIGATION_TOKENS = {
    "learn more",
    "read more",
    "visit site",
    "visit",
    "explore",
    "open link",
    "open in new tab",
    "see details",
    "view details",
}

CHECKOUT_CONTEXT_TOKENS = {
    "checkout",
    "cart",
    "payment",
    "purchase",
    "buy",
    "order",
}

AMBIGUOUS_TOKENS = {
    "ok",
    "continue",
    "next",
    "more",
    "proceed",
    "view more",
    "details",
    "manage choices",
    "manage preferences",
    "privacy settings",
    "preferences",
    "settings",
    "customize",
    "learn more",
}
