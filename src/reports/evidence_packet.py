"""Support helpers for the offline Evidence Packet v0 builder."""

from __future__ import annotations

from typing import Any

from src.reports.evidence_packet_analysis import (
    _build_exa_url_metadata as _build_exa_url_metadata_impl,
    _classify_candidate as _classify_candidate_impl,
    _dedupe as _dedupe_impl,
    _map_exa_source_class_to_packet as _map_exa_source_class_to_packet_impl,
)
from src.reports.evidence_packet_builder_support import (
    empty_packet as _empty_packet,
    finalize_metadata_counts as _finalize_metadata_counts,
    packet_identity as _packet_identity,
    process_candidate as _process_candidate,
)
from src.reports.evidence_packet_candidates import build_evidence_candidates as _evidence_candidates
from src.reports.evidence_packet_inventory import build_source_inventory as _source_inventory
from src.reports.evidence_packet_readiness_support import (
    _cross_dimension_evidence as _cross_dimension_evidence_impl,
    _dimension_readiness as _dimension_readiness_impl,
    _entity_resolution as _entity_resolution_impl,
)

_dedupe = _dedupe_impl


def build_evidence_packet_v0(snapshot: dict) -> dict:
    identity = _packet_identity(snapshot)
    exa_url_metadata = _build_exa_url_metadata_impl(snapshot)

    packet = _empty_packet(**identity)

    candidates = _evidence_candidates(snapshot)
    classified_candidates: list[dict] = []

    seen_ambiguities: set[tuple[str, str]] = set()
    seen_reviews: set[tuple[str, str]] = set()
    seen_missing: set[tuple[str, str]] = set()

    for candidate in candidates:
        classified = _classify_candidate_impl(
            candidate,
            audit_host=identity["audit_host"],
            audit_root=identity["audit_root"],
            exa_url_metadata=exa_url_metadata,
        )
        classified_candidates.append(classified)
        _process_candidate(
            packet=packet,
            classified=classified,
            seen_ambiguities=seen_ambiguities,
            seen_reviews=seen_reviews,
            seen_missing=seen_missing,
        )

    packet["entity_resolution"] = _entity_resolution_impl(packet)
    packet["source_inventory"] = _source_inventory(snapshot, classified_candidates)
    packet["dimension_readiness"] = _dimension_readiness_impl(packet, classified_candidates)
    packet["cross_dimension_evidence"] = _cross_dimension_evidence_impl(packet, classified_candidates)
    _finalize_metadata_counts(packet)
    return packet
