"""Strategic evidence packet derived from Brand Audit snapshots.

Brand Audit owns data collection. This module turns a persisted run snapshot into
small, named evidence groups that downstream interpreters can reuse without
reading raw scraper text or internal feature metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.reports.derivation import collect_evidences
from src.reports.strategic_evidence_packet_helpers import (
    CONTEXT_SOURCE_TYPES,
    GROUP_KEYWORDS,
    NOISE_MARKERS,
    OWNED_SOURCE_TYPES,
    _add_candidate_line as _add_candidate_line_impl,
    _add_owned_raw_web_candidates as _add_owned_raw_web_candidates_impl,
    _entity_research_packet as _entity_research_packet_impl,
    _rank_packet_groups as _rank_packet_groups_impl,
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


def build_strategic_evidence_packet(snapshot: dict[str, Any]) -> StrategicEvidencePacket:
    run = snapshot.get("run") or {}
    packet = StrategicEvidencePacket(
        brand_name=str(run.get("brand_name") or "Unknown Brand"),
        url=str(run.get("url") or ""),
        run_id=run.get("id"),
    )
    evidences = collect_evidences(snapshot)
    preferred = [ev for ev in evidences if str(ev.source_type) in OWNED_SOURCE_TYPES]
    context = [ev for ev in evidences if str(ev.source_type) in CONTEXT_SOURCE_TYPES]
    seen: set[tuple[str, str, str]] = set()
    for ev in preferred:
        source_type = str(ev.source_type)
        packet.source_counts[source_type] = packet.source_counts.get(source_type, 0) + 1
        _add_candidate_line_impl(
            packet,
            seen,
            text=str(ev.quote or ""),
            source_type=source_type,
            source_domain=ev.source_domain,
            url=ev.url,
            feature_name=ev.feature_name,
            dimension=ev.dimension,
            entity_research_packet=_entity_research_packet_impl(snapshot),
        )

    _add_owned_raw_web_candidates_impl(packet, snapshot, seen)

    for ev in context:
        source_type = str(ev.source_type)
        packet.source_counts[source_type] = packet.source_counts.get(source_type, 0) + 1
        _add_candidate_line_impl(
            packet,
            seen,
            text=str(ev.quote or ""),
            source_type=source_type,
            source_domain=ev.source_domain,
            url=ev.url,
            feature_name=ev.feature_name,
            dimension=ev.dimension,
            entity_research_packet=_entity_research_packet_impl(snapshot),
        )

    if not preferred:
        packet.warnings.append("No owned/social evidence found; packet relies on contextual evidence.")
    if not packet.groups:
        packet.warnings.append("No strategically usable evidence groups found.")
    _rank_packet_groups_impl(packet)
    if not packet.groups.get("product_offer"):
        packet.warnings.append("No product offer evidence group found.")
    if not packet.groups.get("audience"):
        packet.warnings.append("No audience evidence group found.")
    return packet

