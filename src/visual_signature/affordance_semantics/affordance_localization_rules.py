"""Heuristic helpers for affordance ownership localization."""

from __future__ import annotations

from typing import Any

from src.visual_signature._internal.utils import float_or_none as _float_or_none, slug as _slug
from src.visual_signature.affordance_semantics.affordance_localization_tokens import (
    ACTIVE_OBSTRUCTION_CONTEXT_TOKENS,
    CART_DRAWER_TOKENS,
    CHAT_WIDGET_TOKENS,
    HEADER_NAVIGATION_TOKENS,
    PROXIMITY_HINT_TOKENS,
    SOCIAL_TOKENS,
)


def classify_owner_fields(
    evidence: Any,
    *,
    affordance_category: str | None,
    interaction_policy: str | None,
) -> tuple[str, float, list[str], list[str]]:
    tokens = all_tokens(evidence)
    ancestry_tokens = ancestry_tokens_for(evidence.dom_ancestry)
    overlay_tokens = normalized_tokens([*evidence.overlay_context, *evidence.obstruction_context, *evidence.dom_context])
    location = normalize_token(evidence.viewport_location or "")
    position = normalize_token(evidence.position or "")
    role_hint = normalize_token(evidence.role_hint or "")
    label_tokens = normalized_tokens([*evidence.visible_text, *evidence.aria_labels, *evidence.titles])
    semantics = normalized_tokens(evidence.svg_icon_semantics)

    if is_chat_widget(tokens, ancestry_tokens, overlay_tokens, location, position, semantics, label_tokens):
        signals = evidence_signals("chat_widget", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "unrelated_chat_widget", 0.94 if "close" in label_tokens or "dismiss" in label_tokens else 0.91, signals, [
            "chat_widget_affordance_is_unrelated_to_active_obstruction",
        ]
    if is_cart_drawer(tokens, ancestry_tokens, overlay_tokens, location, position, semantics, label_tokens):
        signals = evidence_signals("cart_drawer", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "unrelated_cart_drawer", 0.93 if "close" in label_tokens or "dismiss" in label_tokens else 0.9, signals, [
            "cart_drawer_affordance_is_unrelated_to_active_obstruction",
        ]
    if is_social_link(tokens, ancestry_tokens, overlay_tokens, semantics, label_tokens):
        signals = evidence_signals("social_link", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "social_link", 0.89, signals, ["social_or_share_affordance"]
    if is_header_navigation(tokens, ancestry_tokens, overlay_tokens, location, position, role_hint, label_tokens):
        signals = evidence_signals("header_navigation", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "header_navigation", 0.88, signals, ["global_navigation_or_header_chrome"]
    if is_active_obstruction(
        evidence,
        tokens,
        ancestry_tokens,
        overlay_tokens,
        location,
        position,
        role_hint,
        affordance_category,
        interaction_policy,
    ):
        signals = evidence_signals("active_obstruction", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "active_obstruction", 0.95, signals, []

    signals = evidence_signals("unknown_owner", evidence, ancestry_tokens, overlay_tokens, location, position)
    limitations = ["insufficient_or_mixed_ownership_evidence"]
    if affordance_category in {"ambiguous_action", "unknown_action"}:
        limitations.append("ambiguous_affordance_category")
    return "unknown_owner", 0.35, signals, limitations


def is_active_obstruction(
    evidence: Any,
    tokens: set[str],
    ancestry_tokens: set[str],
    overlay_tokens: set[str],
    location: str,
    position: str,
    role_hint: str,
    affordance_category: str | None,
    interaction_policy: str | None,
) -> bool:
    overlay_score = 0
    if evidence.aria_modal:
        overlay_score += 2
    if role_hint == "dialog" or "dialog" in ancestry_tokens or "modal" in ancestry_tokens:
        overlay_score += 2
    if any(token in ACTIVE_OBSTRUCTION_CONTEXT_TOKENS for token in overlay_tokens | tokens | ancestry_tokens):
        overlay_score += 2
    if position in {"fixed", "absolute", "sticky"}:
        overlay_score += 1
    if location in {"center", "top_center", "bottom_center", "full"}:
        overlay_score += 1
    if evidence.bounding_box and is_large_overlay_box(evidence.bounding_box):
        overlay_score += 1
    if any(token in PROXIMITY_HINT_TOKENS for token in overlay_tokens | ancestry_tokens):
        overlay_score += 1
    if affordance_category in {"close_control", "dismiss_control", "consent_accept", "consent_reject"}:
        overlay_score += 1
    if interaction_policy == "safe_to_dismiss":
        overlay_score += 1
    if any(token in {"chat", "cart", "header", "nav", "social"} for token in tokens | ancestry_tokens):
        overlay_score -= 2
    return overlay_score >= 4


def is_chat_widget(tokens: set[str], ancestry_tokens: set[str], overlay_tokens: set[str], location: str, position: str, semantics: set[str], label_tokens: set[str]) -> bool:
    if any(token in CHAT_WIDGET_TOKENS for token in tokens | ancestry_tokens | overlay_tokens | semantics | label_tokens):
        return True
    return position in {"fixed", "sticky"} and location in {"bottom_right", "bottom_left", "right_center"} and "chat" in (tokens | ancestry_tokens | overlay_tokens)


def is_cart_drawer(tokens: set[str], ancestry_tokens: set[str], overlay_tokens: set[str], location: str, position: str, semantics: set[str], label_tokens: set[str]) -> bool:
    if any(token in CART_DRAWER_TOKENS for token in tokens | ancestry_tokens | overlay_tokens | semantics | label_tokens):
        return True
    return position in {"fixed", "sticky"} and location in {"right_center", "right", "bottom_right"} and "cart" in (tokens | ancestry_tokens | overlay_tokens)


def is_header_navigation(tokens: set[str], ancestry_tokens: set[str], overlay_tokens: set[str], location: str, position: str, role_hint: str, label_tokens: set[str]) -> bool:
    navigation_tokens = tokens | ancestry_tokens | overlay_tokens | label_tokens
    if any(token in HEADER_NAVIGATION_TOKENS for token in navigation_tokens):
        return True
    return role_hint in {"navigation", "menu"} or (location in {"top", "top_left", "top_right", "top_center"} and position in {"fixed", "sticky"})


def is_social_link(tokens: set[str], ancestry_tokens: set[str], overlay_tokens: set[str], semantics: set[str], label_tokens: set[str]) -> bool:
    values = tokens | ancestry_tokens | overlay_tokens | semantics | label_tokens
    return any(token in SOCIAL_TOKENS for token in values)


def evidence_signals(owner_label: str, evidence: Any, ancestry_tokens: set[str], overlay_tokens: set[str], location: str, position: str) -> list[str]:
    signals: list[str] = []
    if evidence.aria_modal:
        signals.append("aria_modal:true")
    if evidence.role_hint:
        signals.append(f"role:{evidence.role_hint}")
    if evidence.bounding_box:
        bbox = evidence.bounding_box
        signals.append(f"bounding_box:{bbox.get('x')}:{bbox.get('y')}:{bbox.get('width')}:{bbox.get('height')}")
    if position:
        signals.append(f"position:{position}")
    if location:
        signals.append(f"viewport_location:{location}")
    if ancestry_tokens:
        signals.append(f"dom_ancestry:{','.join(sorted(list(ancestry_tokens))[:6])}")
    if overlay_tokens:
        signals.append(f"overlay_context:{','.join(sorted(list(overlay_tokens))[:6])}")
    signals.append(f"owner_classification:{owner_label}")
    return signals


def is_large_overlay_box(bounding_box: dict[str, Any]) -> bool:
    width = _float_or_none(bounding_box.get("width"))
    height = _float_or_none(bounding_box.get("height"))
    if width is None or height is None:
        return False
    return width >= 360 and height >= 240


def all_tokens(evidence: Any) -> set[str]:
    values = (
        evidence.visible_text
        + evidence.aria_labels
        + evidence.titles
        + evidence.roles
        + evidence.svg_icon_semantics
        + evidence.dom_context
        + evidence.overlay_context
        + evidence.obstruction_context
        + evidence.proximity_context
    )
    tokens = normalized_tokens(values)
    tokens |= normalized_tokens(flatten_ancestry(evidence.dom_ancestry))
    return tokens


def affordance_id(evidence: Any, owner: str) -> str:
    primary = next(iter(evidence.visible_text or evidence.aria_labels or evidence.titles or evidence.svg_icon_semantics or [owner]))
    return _slug(f"{owner}-{primary}", default="affordance-owner")


def flatten_ancestry(values: list[Any]) -> list[str]:
    tokens: list[str] = []
    for value in values:
        if isinstance(value, dict):
            for key in ("tag", "id", "role", "aria-label", "aria_label", "class", "name", "text"):
                item = value.get(key)
                if item:
                    tokens.append(str(item))
        else:
            tokens.append(str(value))
    return tokens


def ancestry_tokens_for(values: list[Any]) -> set[str]:
    return normalized_tokens(flatten_ancestry(values))


def normalized_tokens(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = normalize_token(value)
        if text:
            tokens.add(text)
            tokens.update(text.split())
    return tokens


def normalize_token(value: str) -> str:
    return " ".join("".join(ch if ch.isalnum() or ch.isspace() else " " for ch in (value or "").lower().replace("-", " ").replace("/", " ")).split())
