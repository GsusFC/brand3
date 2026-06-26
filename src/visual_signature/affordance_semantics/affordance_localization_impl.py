"""Diagnostic affordance ownership localization for Visual Signature.

This layer classifies whether a discovered affordance belongs to the active
obstruction or to unrelated UI. It does not execute mutations and does not
influence click eligibility.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from src.visual_signature.affordance_semantics.affordance_localization_rules import (
    affordance_id as _affordance_id,
    classify_owner_fields as _classify_owner_fields,
)
from src.visual_signature.versions import AFFORDANCE_LOCALIZATION_SCHEMA_VERSION
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
    owner, confidence, signals, limitations = _classify_owner_fields(
        evidence,
        affordance_category=affordance_category,
        interaction_policy=interaction_policy,
    )
    return owner, confidence, signals, limitations

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
