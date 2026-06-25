"""Builder for strategic evidence packets derived from run snapshots."""

from __future__ import annotations

from typing import Any

from src.reports.derivation import collect_evidences
from src.reports.strategic_evidence_packet_helpers import (
    CONTEXT_SOURCE_TYPES,
    OWNED_SOURCE_TYPES,
    _add_candidate_line as _add_candidate_line_impl,
    _add_owned_raw_web_candidates as _add_owned_raw_web_candidates_impl,
    _entity_research_packet as _entity_research_packet_impl,
    _rank_packet_groups as _rank_packet_groups_impl,
)
from src.reports.strategic_evidence_packet_models import StrategicEvidencePacket


def build_packet(snapshot: dict[str, Any]) -> StrategicEvidencePacket:
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
    entity_research_packet = _entity_research_packet_impl(snapshot)

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
            entity_research_packet=entity_research_packet,
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
            entity_research_packet=entity_research_packet,
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
