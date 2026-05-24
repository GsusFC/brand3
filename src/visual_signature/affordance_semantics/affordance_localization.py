"""Diagnostic affordance ownership localization for Visual Signature.

This layer classifies whether a discovered affordance belongs to the active
obstruction or to unrelated UI. It does not execute mutations and does not
influence click eligibility.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from src.visual_signature.affordance_semantics.affordance_models import (
    AFFORDANCE_SEMANTICS_SCHEMA_VERSION,
)


AffordanceOwner = Literal[
    "active_obstruction",
    "unrelated_chat_widget",
    "unrelated_cart_drawer",
    "header_navigation",
    "social_link",
    "unknown_owner",
]

AFFORDANCE_LOCALIZATION_SCHEMA_VERSION = "visual-signature-affordance-localization-1"


@dataclass(slots=True)
class AffordanceLocalizationEvidence:
    visible_text: list[str] = field(default_factory=list)
    aria_labels: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    svg_icon_semantics: list[str] = field(default_factory=list)
    dom_context: list[str] = field(default_factory=list)
    overlay_context: list[str] = field(default_factory=list)
    obstruction_context: list[str] = field(default_factory=list)
    dom_ancestry: list[Any] = field(default_factory=list)
    bounding_box: dict[str, Any] | None = None
    viewport_location: str | None = None
    position: str | None = None
    z_index: str | None = None
    aria_modal: bool | None = None
    role_hint: str | None = None
    proximity_context: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "AffordanceLocalizationEvidence":
        return cls(
            visible_text=_string_list(payload.get("visible_text")),
            aria_labels=_string_list(payload.get("aria_labels") or payload.get("aria_label") or payload.get("aria-label")),
            titles=_string_list(payload.get("titles") or payload.get("title")),
            roles=_string_list(payload.get("roles") or payload.get("role")),
            svg_icon_semantics=_string_list(payload.get("svg_icon_semantics") or payload.get("svg_semantics")),
            dom_context=_string_list(payload.get("dom_context") or payload.get("dom-context")),
            overlay_context=_string_list(payload.get("overlay_context") or payload.get("overlay-context")),
            obstruction_context=_string_list(payload.get("obstruction_context") or payload.get("obstruction-context")),
            dom_ancestry=_object_list(payload.get("dom_ancestry") or payload.get("ancestry")),
            bounding_box=_dict_or_none(payload.get("bounding_box") or payload.get("bounding-box")),
            viewport_location=_string_or_none(payload.get("viewport_location") or payload.get("viewport-location")),
            position=_string_or_none(payload.get("position")),
            z_index=_string_or_none(payload.get("z_index") or payload.get("z-index")),
            aria_modal=_bool_or_none(payload.get("aria_modal") or payload.get("aria-modal")),
            role_hint=_string_or_none(payload.get("role_hint") or payload.get("role-hint")),
            proximity_context=_string_list(payload.get("proximity_context") or payload.get("proximity-context")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AffordanceLocalizationDecision:
    schema_version: Literal[AFFORDANCE_LOCALIZATION_SCHEMA_VERSION]
    record_type: Literal["affordance_localization"]
    affordance_id: str
    owner: AffordanceOwner
    owner_confidence: float
    owner_evidence: list[str] = field(default_factory=list)
    owner_limitations: list[str] = field(default_factory=list)
    evidence: AffordanceLocalizationEvidence = field(default_factory=AffordanceLocalizationEvidence)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence"] = self.evidence.to_dict()
        payload["created_at"] = self.created_at.isoformat().replace("+00:00", "Z")
        return payload


@dataclass(slots=True)
class AffordanceLocalizationExport:
    schema_version: Literal["visual-signature-affordance-localization-export-1"]
    record_type: Literal["affordance_localization_export"]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str | None = None
    records: list[AffordanceLocalizationDecision] = field(default_factory=list)
    owner_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_type": self.record_type,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
            "source": self.source,
            "records": [record.to_dict() for record in self.records],
            "owner_counts": dict(sorted(self.owner_counts.items())),
        }


def classify_affordance_owner(
    evidence: dict[str, Any],
    *,
    affordance_id: str | None = None,
    affordance_category: str | None = None,
    interaction_policy: str | None = None,
) -> AffordanceLocalizationDecision:
    model = AffordanceLocalizationEvidence.from_mapping(evidence)
    owner, confidence, signals, limitations = _classify_owner(
        model,
        affordance_category=affordance_category,
        interaction_policy=interaction_policy,
    )
    return AffordanceLocalizationDecision(
        schema_version=AFFORDANCE_LOCALIZATION_SCHEMA_VERSION,
        record_type="affordance_localization",
        affordance_id=affordance_id or _affordance_id(model, owner),
        owner=owner,
        owner_confidence=min(1.0, max(0.0, round(confidence, 3))),
        owner_evidence=signals,
        owner_limitations=limitations,
        evidence=model,
    )


def classify_affordance_owners(items: list[dict[str, Any]]) -> list[AffordanceLocalizationDecision]:
    return [classify_affordance_owner(item) for item in items]


def build_affordance_localization_export(
    records: list[AffordanceLocalizationDecision],
    *,
    source: str | None = None,
) -> AffordanceLocalizationExport:
    owner_counts: dict[str, int] = {}
    for record in records:
        owner_counts[record.owner] = owner_counts.get(record.owner, 0) + 1
    return AffordanceLocalizationExport(
        schema_version="visual-signature-affordance-localization-export-1",
        record_type="affordance_localization_export",
        source=source,
        records=records,
        owner_counts=owner_counts,
    )


def export_affordance_localization_json(
    path,
    records: list[AffordanceLocalizationDecision],
    *,
    source: str | None = None,
) -> dict[str, Any]:
    export = build_affordance_localization_export(records, source=source)
    payload = export.to_dict()
    from pathlib import Path
    import json

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _classify_owner(
    evidence: AffordanceLocalizationEvidence,
    *,
    affordance_category: str | None,
    interaction_policy: str | None,
) -> tuple[AffordanceOwner, float, list[str], list[str]]:
    tokens = _all_tokens(evidence)
    ancestry_tokens = _ancestry_tokens(evidence.dom_ancestry)
    overlay_tokens = _normalized_tokens([*evidence.overlay_context, *evidence.obstruction_context, *evidence.dom_context])
    location = _normalize(evidence.viewport_location or "")
    position = _normalize(evidence.position or "")
    role_hint = _normalize(evidence.role_hint or "")
    label_tokens = _normalized_tokens([*evidence.visible_text, *evidence.aria_labels, *evidence.titles])
    semantics = _normalized_tokens(evidence.svg_icon_semantics)

    if _is_chat_widget(tokens, ancestry_tokens, overlay_tokens, location, position, semantics, label_tokens):
        signals = _evidence_signals("chat_widget", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "unrelated_chat_widget", 0.94 if "close" in label_tokens or "dismiss" in label_tokens else 0.91, signals, [
            "chat_widget_affordance_is_unrelated_to_active_obstruction",
        ]

    if _is_cart_drawer(tokens, ancestry_tokens, overlay_tokens, location, position, semantics, label_tokens):
        signals = _evidence_signals("cart_drawer", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "unrelated_cart_drawer", 0.93 if "close" in label_tokens or "dismiss" in label_tokens else 0.9, signals, [
            "cart_drawer_affordance_is_unrelated_to_active_obstruction",
        ]

    if _is_social_link(tokens, ancestry_tokens, overlay_tokens, semantics, label_tokens):
        signals = _evidence_signals("social_link", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "social_link", 0.89, signals, ["social_or_share_affordance"]

    if _is_header_navigation(tokens, ancestry_tokens, overlay_tokens, location, position, role_hint, label_tokens):
        signals = _evidence_signals("header_navigation", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "header_navigation", 0.88, signals, ["global_navigation_or_header_chrome"]

    if _is_active_obstruction(
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
        signals = _evidence_signals("active_obstruction", evidence, ancestry_tokens, overlay_tokens, location, position)
        return "active_obstruction", 0.95, signals, []

    signals = _evidence_signals("unknown_owner", evidence, ancestry_tokens, overlay_tokens, location, position)
    limitations = ["insufficient_or_mixed_ownership_evidence"]
    if affordance_category in {"ambiguous_action", "unknown_action"}:
        limitations.append("ambiguous_affordance_category")
    return "unknown_owner", 0.35, signals, limitations


def _is_active_obstruction(
    evidence: AffordanceLocalizationEvidence,
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
    if evidence.bounding_box and _is_large_overlay_box(evidence.bounding_box):
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


def _is_chat_widget(
    tokens: set[str],
    ancestry_tokens: set[str],
    overlay_tokens: set[str],
    location: str,
    position: str,
    semantics: set[str],
    label_tokens: set[str],
) -> bool:
    if any(token in CHAT_WIDGET_TOKENS for token in tokens | ancestry_tokens | overlay_tokens | semantics | label_tokens):
        return True
    return position in {"fixed", "sticky"} and location in {"bottom_right", "bottom_left", "right_center"} and "chat" in (tokens | ancestry_tokens | overlay_tokens)


def _is_cart_drawer(
    tokens: set[str],
    ancestry_tokens: set[str],
    overlay_tokens: set[str],
    location: str,
    position: str,
    semantics: set[str],
    label_tokens: set[str],
) -> bool:
    if any(token in CART_DRAWER_TOKENS for token in tokens | ancestry_tokens | overlay_tokens | semantics | label_tokens):
        return True
    return position in {"fixed", "sticky"} and location in {"right_center", "right", "bottom_right"} and "cart" in (tokens | ancestry_tokens | overlay_tokens)


def _is_header_navigation(
    tokens: set[str],
    ancestry_tokens: set[str],
    overlay_tokens: set[str],
    location: str,
    position: str,
    role_hint: str,
    label_tokens: set[str],
) -> bool:
    navigation_tokens = tokens | ancestry_tokens | overlay_tokens | label_tokens
    if any(token in HEADER_NAVIGATION_TOKENS for token in navigation_tokens):
        return True
    return role_hint in {"navigation", "menu"} or (location in {"top", "top_left", "top_right", "top_center"} and position in {"fixed", "sticky"})


def _is_social_link(
    tokens: set[str],
    ancestry_tokens: set[str],
    overlay_tokens: set[str],
    semantics: set[str],
    label_tokens: set[str],
) -> bool:
    values = tokens | ancestry_tokens | overlay_tokens | semantics | label_tokens
    return any(token in SOCIAL_TOKENS for token in values)


def _evidence_signals(
    owner_label: str,
    evidence: AffordanceLocalizationEvidence,
    ancestry_tokens: set[str],
    overlay_tokens: set[str],
    location: str,
    position: str,
) -> list[str]:
    signals: list[str] = []
    if evidence.aria_modal:
        signals.append("aria_modal:true")
    if evidence.role_hint:
        signals.append(f"role:{evidence.role_hint}")
    if evidence.bounding_box:
        bbox = evidence.bounding_box
        signals.append(
            f"bounding_box:{bbox.get('x')}:{bbox.get('y')}:{bbox.get('width')}:{bbox.get('height')}"
        )
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


def _is_large_overlay_box(bounding_box: dict[str, Any]) -> bool:
    width = _float_or_none(bounding_box.get("width"))
    height = _float_or_none(bounding_box.get("height"))
    if width is None or height is None:
        return False
    return width >= 360 and height >= 240


def _all_tokens(evidence: AffordanceLocalizationEvidence) -> set[str]:
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
    tokens = _normalized_tokens(values)
    tokens |= _normalized_tokens(_flatten_ancestry(evidence.dom_ancestry))
    return tokens


def _affordance_id(evidence: AffordanceLocalizationEvidence, owner: str) -> str:
    primary = next(
        iter(
            evidence.visible_text
            or evidence.aria_labels
            or evidence.titles
            or evidence.svg_icon_semantics
            or [owner]
        )
    )
    return _slug(f"{owner}-{primary}")


def _flatten_ancestry(values: list[Any]) -> list[str]:
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


def _ancestry_tokens(values: list[Any]) -> set[str]:
    return _normalized_tokens(_flatten_ancestry(values))


def _normalized_tokens(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = _normalize(value)
        if text:
            tokens.add(text)
            tokens.update(text.split())
    return tokens


def _normalize(value: str) -> str:
    return " ".join(
        "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in (value or "").lower().replace("-", " ").replace("/", " "))
        .split()
    )


def _slug(value: str) -> str:
    out: list[str] = []
    for char in value.lower().strip():
        if char.isalnum():
            out.append(char)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-") or "affordance-owner"


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                out.append(text)
        return out
    text = str(value).strip()
    return [text] if text else []


def _object_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if item is not None]
    return [value]


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


CHAT_WIDGET_TOKENS = {
    "chat",
    "live chat",
    "support chat",
    "messenger",
    "intercom",
    "zendesk",
    "help widget",
    "help chat",
    "talk to us",
    "chat launcher",
    "chat bubble",
    "support",
}

CART_DRAWER_TOKENS = {
    "cart",
    "mini cart",
    "cart drawer",
    "shopping cart",
    "bag",
    "shopping bag",
    "basket",
    "order summary",
    "checkout",
    "purchase panel",
}

HEADER_NAVIGATION_TOKENS = {
    "header",
    "nav",
    "navigation",
    "menu",
    "global nav",
    "site nav",
    "brand",
    "logo",
    "skip to content",
    "top bar",
}

SOCIAL_TOKENS = {
    "social",
    "share",
    "follow",
    "facebook",
    "twitter",
    "x twitter",
    "x-twitter",
    "linkedin",
    "instagram",
    "youtube",
    "tiktok",
    "pinterest",
    "threads",
}

ACTIVE_OBSTRUCTION_CONTEXT_TOKENS = {
    "modal",
    "dialog",
    "popup",
    "overlay",
    "banner",
    "cookie",
    "consent",
    "privacy",
    "newsletter",
    "subscribe",
    "promo",
    "promotion",
    "offer",
}

PROXIMITY_HINT_TOKENS = {
    "obstruction",
    "overlay root",
    "dialog root",
    "modal root",
    "blocking overlay",
    "active obstruction",
}
