"""Dataclasses for the Visual Signature affordance semantics scaffold."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


AFFORDANCE_SEMANTICS_SCHEMA_VERSION = "visual-signature-affordance-semantics-1"
AFFORDANCE_EXPORT_SCHEMA_VERSION = "visual-signature-affordance-export-1"

AffordanceCategory = Literal[
    "close_control",
    "dismiss_control",
    "consent_accept",
    "consent_reject",
    "login_action",
    "subscription_action",
    "checkout_action",
    "external_navigation",
    "ambiguous_action",
    "unknown_action",
]

AffordancePolicy = Literal["safe_to_dismiss", "unsafe_to_mutate", "requires_human_review"]
EvidenceSource = Literal[
    "visible_text",
    "aria_label",
    "title",
    "role",
    "svg_icon_semantics",
    "dom_context",
    "overlay_context",
]
ConfidenceLevel = Literal["low", "medium", "high"]


@dataclass(slots=True)
class AffordanceEvidence:
    visible_text: list[str] = field(default_factory=list)
    aria_labels: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    svg_icon_semantics: list[str] = field(default_factory=list)
    dom_context: list[str] = field(default_factory=list)
    overlay_context: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "AffordanceEvidence":
        return cls(
            visible_text=_string_list(payload.get("visible_text")),
            aria_labels=_string_list(payload.get("aria_labels") or payload.get("aria_label") or payload.get("aria-label")),
            titles=_string_list(payload.get("titles") or payload.get("title")),
            roles=_string_list(payload.get("roles") or payload.get("role")),
            svg_icon_semantics=_string_list(
                payload.get("svg_icon_semantics")
                or payload.get("svg_semantics")
                or payload.get("svg-icon-semantics")
            ),
            dom_context=_string_list(payload.get("dom_context") or payload.get("dom-context")),
            overlay_context=_string_list(payload.get("overlay_context") or payload.get("overlay-context")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AffordancePolicyDecision:
    category: AffordanceCategory
    policy: AffordancePolicy
    confidence: float
    review_required: bool
    limitations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AffordanceClassification:
    schema_version: Literal[AFFORDANCE_SEMANTICS_SCHEMA_VERSION]
    record_type: Literal["affordance_classification"]
    affordance_id: str
    category: AffordanceCategory
    policy: AffordancePolicy
    confidence: float
    evidence: AffordanceEvidence
    evidence_sources: list[EvidenceSource] = field(default_factory=list)
    matched_signals: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    review_required: bool = False
    notes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence"] = self.evidence.to_dict()
        payload["created_at"] = self.created_at.isoformat().replace("+00:00", "Z")
        return payload


@dataclass(slots=True)
class AffordanceExport:
    schema_version: Literal[AFFORDANCE_EXPORT_SCHEMA_VERSION]
    record_type: Literal["affordance_export"]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str | None = None
    records: list[AffordanceClassification] = field(default_factory=list)
    status_counts: dict[str, int] = field(default_factory=dict)
    policy_counts: dict[str, int] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_type": self.record_type,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
            "source": self.source,
            "records": [record.to_dict() for record in self.records],
            "status_counts": dict(sorted(self.status_counts.items())),
            "policy_counts": dict(sorted(self.policy_counts.items())),
            "category_counts": dict(sorted(self.category_counts.items())),
        }


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
