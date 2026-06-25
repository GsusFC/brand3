"""Serializable models for strategic evidence packets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.reports.strategic_evidence_packet_helpers import (
    GROUP_KEYWORDS,
    _rejected_reason_counts as _rejected_reason_counts_impl,
)


@dataclass
class StrategicEvidenceLine:
    text: str
    source_type: str
    source_domain: str | None = None
    url: str | None = None
    feature_name: str | None = None
    dimension: str | None = None
    surface_role: str | None = None
    entity_scope: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source_type": self.source_type,
            "source_domain": self.source_domain,
            "url": self.url,
            "feature_name": self.feature_name,
            "dimension": self.dimension,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
        }


@dataclass
class StrategicEvidencePacket:
    brand_name: str
    url: str
    run_id: int | None
    groups: dict[str, list[StrategicEvidenceLine]] = field(default_factory=dict)
    rejected: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_counts: dict[str, int] = field(default_factory=dict)

    def group_text(self, group: str, limit: int = 6) -> list[str]:
        return [line.text for line in self.groups.get(group, [])[:limit]]

    def to_interpreter_text(self) -> str:
        lines: list[str] = []
        seen: set[str] = set()
        for group in GROUP_KEYWORDS:
            for line in self.group_text(group):
                key = line.lower()
                if key in seen:
                    continue
                seen.add(key)
                lines.append(line)
        return "\n".join(lines).strip()

    def to_summary(self) -> dict[str, Any]:
        return {
            "source": "strategic_evidence_packet",
            "source_label": "Strategic Evidence Packet",
            "evidence_basis": "Grouped Brand Audit evidence reused by TLDR interpreters.",
            "run_id": self.run_id,
            "group_counts": {key: len(value) for key, value in self.groups.items()},
            "source_counts": self.source_counts,
            "rejected_count": len(self.rejected),
            "rejected_reason_counts": _rejected_reason_counts_impl(self.rejected),
            "warnings": self.warnings,
            "value_policy": "Brand Audit owns collection; this packet only groups strategically relevant public evidence.",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_summary(),
            "brand_name": self.brand_name,
            "url": self.url,
            "groups": {
                key: [line.to_dict() for line in value]
                for key, value in self.groups.items()
            },
            "rejected": self.rejected[:40],
        }
