"""Parallel evidence vNext experiment.

This module is intentionally offline and side-effect free. It adapts the
existing snapshot into a stricter evidence view, then builds a filtered
EvidenceGraph/BrandResearchPack so we can compare it against current outputs
without changing acquisition, scoring, runtime routes, or prompts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.reports.brand_research_pack import BrandResearchPack, build_brand_research_pack_from_snapshot
from src.reports.evidence_packet import build_evidence_packet_v0
from src.research.evidence_graph import EvidenceGraph, build_evidence_graph_from_snapshot
from src.research.evidence_vnext_acquisition_contracts import (
    AcquisitionContractExclusion,
    AcquisitionContractResult,
    _acquisition_diagnostics_from_snapshot,
    apply_evidence_vnext_acquisition_contracts,
)
from src.research.evidence_vnext_comparison import (
    EvidenceVNextComparison,
    compare_evidence_vnext_from_snapshot,
    compare_legacy_current_and_vnext_from_snapshot,
)
from src.research.evidence_vnext_helpers import (
    _filter_claims,
    _observation_reason,
    _observations_from_packet,
    _optional_int,
    _unique,
    _vnext_gaps,
    _vnext_warnings,
)
from src.research.evidence_vnext_semantics import (
    build_evidence_vnext_semantic_assessment as _build_evidence_vnext_semantic_assessment,
)
from src.research.research_pack_builder import build_brand_research_pack_from_graph


EVIDENCE_VNEXT_VERSION = "brand3_evidence_vnext_v0_1"


@dataclass(frozen=True, slots=True)
class SourceObservation:
    """One normalized source/evidence observation for the vNext gate."""

    observation_id: str
    text: str
    url: str
    dimension: str
    provider: str
    feature_name: str
    source_class: str
    eligibility: str
    gate_status: str
    classification_reason: str = ""
    limits: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "observation_id": self.observation_id,
            "text": self.text,
            "url": self.url,
            "dimension": self.dimension,
            "provider": self.provider,
            "feature_name": self.feature_name,
            "source_class": self.source_class,
            "eligibility": self.eligibility,
            "gate_status": self.gate_status,
            "classification_reason": self.classification_reason,
            "limits": self.limits,
        }


@dataclass(frozen=True, slots=True)
class EvidenceVNextPacket:
    """Gate result used to build and compare vNext outputs."""

    version: str
    run_id: int | None
    brand_name: str
    url: str
    observations: tuple[SourceObservation, ...]
    legacy_packet_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> tuple[SourceObservation, ...]:
        return tuple(item for item in self.observations if item.gate_status == "accepted")

    @property
    def review_required(self) -> tuple[SourceObservation, ...]:
        return tuple(item for item in self.observations if item.gate_status == "review_required")

    @property
    def rejected(self) -> tuple[SourceObservation, ...]:
        return tuple(item for item in self.observations if item.gate_status == "rejected")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "runtime_effect": False,
            "prompt_effect": False,
            "run_id": self.run_id,
            "brand_name": self.brand_name,
            "url": self.url,
            "observations": [item.to_dict() for item in self.observations],
            "accepted": [item.to_dict() for item in self.accepted],
            "review_required": [item.to_dict() for item in self.review_required],
            "rejected": [item.to_dict() for item in self.rejected],
            "summary": self.summary(),
            "legacy_packet_summary": dict(self.legacy_packet_summary),
        }

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        source_class_counts: dict[str, int] = {}
        eligibility_counts: dict[str, int] = {}
        review_reason_counts: dict[str, int] = {}
        rejected_reason_counts: dict[str, int] = {}
        for item in self.observations:
            status_counts[item.gate_status] = status_counts.get(item.gate_status, 0) + 1
            source_class_counts[item.source_class] = source_class_counts.get(item.source_class, 0) + 1
            eligibility_counts[item.eligibility] = eligibility_counts.get(item.eligibility, 0) + 1
            if item.gate_status == "review_required":
                reason = _observation_reason(item)
                review_reason_counts[reason] = review_reason_counts.get(reason, 0) + 1
            elif item.gate_status == "rejected":
                reason = _observation_reason(item)
                rejected_reason_counts[reason] = rejected_reason_counts.get(reason, 0) + 1
        return {
            "observation_count": len(self.observations),
            "accepted_count": len(self.accepted),
            "review_required_count": len(self.review_required),
            "rejected_count": len(self.rejected),
            "status_counts": dict(sorted(status_counts.items())),
            "source_class_counts": dict(sorted(source_class_counts.items())),
            "eligibility_counts": dict(sorted(eligibility_counts.items())),
            "review_reason_counts": dict(sorted(review_reason_counts.items())),
            "rejected_reason_counts": dict(sorted(rejected_reason_counts.items())),
        }


def build_evidence_vnext_packet_from_snapshot(snapshot: dict[str, Any]) -> EvidenceVNextPacket:
    """Build the offline vNext gate packet from the existing snapshot."""

    packet = build_evidence_packet_v0(snapshot)
    observations = _observations_from_packet(packet, snapshot=snapshot)
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    return EvidenceVNextPacket(
        version=EVIDENCE_VNEXT_VERSION,
        run_id=_optional_int(run.get("id")),
        brand_name=str(run.get("brand_name") or ""),
        url=str(run.get("url") or ""),
        observations=tuple(observations),
        legacy_packet_summary={
            "case_id": packet.get("case_id") or "",
            "counts": (packet.get("metadata") or {}).get("counts") or {},
            "dimension_readiness": packet.get("dimension_readiness") or {},
        },
    )


def build_vnext_evidence_graph_from_snapshot(snapshot: dict[str, Any]) -> EvidenceGraph:
    """Build an EvidenceGraph filtered by the vNext evidence gate."""

    base_graph = build_evidence_graph_from_snapshot(snapshot)
    gate = build_evidence_vnext_packet_from_snapshot(snapshot)
    filtered_claims = _filter_claims(base_graph.claims, gate)
    return EvidenceGraph(
        version=f"{base_graph.version}+evidence_vnext",
        run=base_graph.run,
        sources=base_graph.sources,
        claims=filtered_claims,
        gaps=_unique(list(base_graph.gaps) + _vnext_gaps(gate, filtered_claims)),
        warnings=_unique(list(base_graph.warnings) + _vnext_warnings(gate)),
        shadow_sources=base_graph.shadow_sources,
        dedupe_stats={
            **dict(base_graph.dedupe_stats),
            "vnext_input_claim_count": len(base_graph.claims),
            "vnext_filtered_claim_count": len(filtered_claims),
            "vnext_removed_claim_count": len(base_graph.claims) - len(filtered_claims),
        },
    )


def build_vnext_brand_research_pack_from_snapshot(snapshot: dict[str, Any]) -> BrandResearchPack:
    """Build a BrandResearchPack from the vNext filtered graph."""

    return build_brand_research_pack_from_graph(build_vnext_evidence_graph_from_snapshot(snapshot))


def build_evidence_vnext_semantic_assessment(packet: EvidenceVNextPacket) -> dict[str, Any]:
    return _build_evidence_vnext_semantic_assessment(packet)
