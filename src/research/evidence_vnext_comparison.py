"""Comparison helpers for evidence vNext snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.reports.brand_research_pack import BrandResearchPack, build_brand_research_pack_from_snapshot
from src.reports.evidence_packet import build_evidence_packet_v0
from src.research.evidence_graph import EvidenceClaim, EvidenceGraph, build_evidence_graph_from_snapshot
from src.research.evidence_vnext_acquisition_contracts import (
    _acquisition_diagnostics_from_snapshot,
    apply_evidence_vnext_acquisition_contracts,
)
from src.research.evidence_vnext_semantics import (
    build_evidence_vnext_semantic_assessment as _build_evidence_vnext_semantic_assessment,
)
from src.research.pack_comparison import FieldComparison
from src.research.research_pack_builder import build_brand_research_pack_from_graph
from src.research.evidence_vnext_comparison_support import (
    _compare_field,
    _filter_claims,
    _normalize_value,
    _optional_int,
    _preview,
    _preview_looks_nonmaterial,
    _reclassified_to_noise_count,
    _scorecard_status,
    _text_key,
    _unique,
    _url_key,
    _vnext_gaps,
    _vnext_warnings,
)
from src.research.evidence_vnext_helpers import (
    _observation_reason,
    _observations_from_packet,
)


MATERIAL_FIELDS = {
    "company_summary",
    "product_summary",
    "audience",
    "offer",
    "outcome",
    "declared_purpose",
    "declared_mission",
    "future_direction",
    "proof_points",
    "founder_or_press_context",
    "competitive_context",
}


@dataclass(frozen=True, slots=True)
class EvidenceVNextComparison:
    """Comparison of legacy/current graph/vNext outputs for one snapshot."""

    run_id: int | None
    brand_name: str
    url: str
    current_graph_summary: dict[str, Any]
    vnext_graph_summary: dict[str, Any]
    gate_summary: dict[str, Any]
    reclassified_to_noise_count: int
    fields: tuple[FieldComparison, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "brand_name": self.brand_name,
            "url": self.url,
            "current_graph_summary": dict(self.current_graph_summary),
            "vnext_graph_summary": dict(self.vnext_graph_summary),
            "gate_summary": dict(self.gate_summary),
            "reclassified_to_noise_count": self.reclassified_to_noise_count,
            "fields": [item.to_dict() for item in self.fields],
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, Any]:
        gained = [item.field for item in self.fields if item.legacy_empty and not item.graph_empty]
        lost = [item.field for item in self.fields if not item.legacy_empty and item.graph_empty]
        changed = [item.field for item in self.fields if item.changed]
        material_lost = [
            item.field
            for item in self.fields
            if not item.legacy_empty
            and item.graph_empty
            and item.field in MATERIAL_FIELDS
            and not _preview_looks_nonmaterial(item.legacy_preview)
        ]
        non_material_lost = [field for field in lost if field not in material_lost]
        review_count = int(self.gate_summary.get("review_required_count") or 0)
        rejected_count = int(self.gate_summary.get("rejected_count") or 0)
        scorecard = _scorecard_status(
            material_lost=material_lost,
            non_material_lost=non_material_lost,
            review_count=review_count,
            rejected_count=rejected_count,
        )
        return {
            "gained_fields": gained,
            "lost_fields": lost,
            "material_lost_fields": material_lost,
            "non_material_lost_fields": non_material_lost,
            "changed_fields": changed,
            "gained_count": len(gained),
            "lost_count": len(lost),
            "material_lost_count": len(material_lost),
            "non_material_lost_count": len(non_material_lost),
            "changed_count": len(changed),
            "claim_delta": int(self.vnext_graph_summary.get("claim_count") or 0)
            - int(self.current_graph_summary.get("claim_count") or 0),
            "noise_delta": int(self.vnext_graph_summary.get("noise_claim_count") or 0)
            - int(self.current_graph_summary.get("noise_claim_count") or 0),
            "reclassified_to_noise_count": self.reclassified_to_noise_count,
            "scorecard": scorecard,
        }


def compare_evidence_vnext_from_snapshot(snapshot: dict[str, Any]) -> EvidenceVNextComparison:
    """Compare current graph-backed pack against vNext filtered pack."""

    from src.research.evidence_vnext import (
        build_evidence_vnext_packet_from_snapshot,
        build_vnext_evidence_graph_from_snapshot,
    )

    current_graph = build_evidence_graph_from_snapshot(snapshot)
    current_pack = build_brand_research_pack_from_graph(current_graph).to_dict()
    vnext_graph = build_vnext_evidence_graph_from_snapshot(snapshot)
    vnext_pack = build_brand_research_pack_from_graph(vnext_graph).to_dict()
    gate = build_evidence_vnext_packet_from_snapshot(snapshot)
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    fields = tuple(
        _compare_field(field, current_pack.get(field), vnext_pack.get(field))
        for field in (
            "company_summary",
            "product_summary",
            "audience",
            "offer",
            "outcome",
            "category",
            "declared_purpose",
            "declared_mission",
            "future_direction",
            "tone_of_voice",
            "personality_signals",
            "visual_or_conceptual_signals",
            "values_signals",
            "attributes_signals",
            "proof_points",
            "founder_or_press_context",
            "competitive_context",
            "noise_rejected",
        )
    )
    return EvidenceVNextComparison(
        run_id=_optional_int(run.get("id")),
        brand_name=str(run.get("brand_name") or ""),
        url=str(run.get("url") or ""),
        current_graph_summary=current_graph.summary(),
        vnext_graph_summary=vnext_graph.summary(),
        gate_summary=gate.summary(),
        reclassified_to_noise_count=_reclassified_to_noise_count(vnext_graph.claims),
        fields=fields,
    )


def compare_legacy_current_and_vnext_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return all three pack payloads for lab inspection."""

    from src.research.evidence_vnext import (
        build_evidence_vnext_packet_from_snapshot,
        build_vnext_evidence_graph_from_snapshot,
    )

    acquisition_contracts = apply_evidence_vnext_acquisition_contracts(snapshot)
    acquisition_diagnostics = _acquisition_diagnostics_from_snapshot(snapshot)
    legacy = build_brand_research_pack_from_snapshot(snapshot)
    current_graph = build_evidence_graph_from_snapshot(snapshot)
    current = build_brand_research_pack_from_graph(current_graph)
    vnext_graph = build_vnext_evidence_graph_from_snapshot(snapshot)
    vnext = build_brand_research_pack_from_graph(vnext_graph)
    gate = build_evidence_vnext_packet_from_snapshot(snapshot)
    semantic = build_evidence_vnext_semantic_assessment(gate)
    semantic_llm = _maybe_build_llm_semantic_assessment(gate)
    return {
        "runtime_effect": False,
        "prompt_effect": False,
        "model_effect": False,
        "legacy_pack": legacy.to_dict(),
        "current_graph_pack": current.to_dict(),
        "vnext_pack": vnext.to_dict(),
        "current_graph": current_graph.to_dict(),
        "vnext_graph": vnext_graph.to_dict(),
        "vnext_gate": gate.to_dict(),
        "vnext_semantic_assessment": semantic,
        "vnext_semantic_llm_assessment": semantic_llm,
        "vnext_acquisition_contracts": acquisition_contracts.to_dict(),
        "vnext_acquisition_diagnostics": acquisition_diagnostics,
        "vnext_comparison": compare_evidence_vnext_from_snapshot(snapshot).to_dict(),
    }


def build_evidence_vnext_semantic_assessment(packet) -> dict[str, Any]:
    return _build_evidence_vnext_semantic_assessment(packet)


def _maybe_build_llm_semantic_assessment(gate) -> dict[str, Any]:
    try:
        from src.research.evidence_semantic_llm import build_llm_semantic_assessment

        return build_llm_semantic_assessment(gate)
    except Exception as exc:
        return {
            "version": "evidence_vnext_llm_semantic_assessment_v0_1",
            "runtime_effect": False,
            "prompt_effect": False,
            "model_effect": False,
            "classifier": "llm_shadow_v0",
            "status": "error",
            "reason": "llm_classifier_exception",
            "detail": str(exc)[:200],
            "assessments": [],
            "summary": {
                "assessment_count": 0,
                "accepted_count": len(gate.accepted),
                "accepted_material_count": 0,
                "accepted_weak_count": 0,
                "accepted_material_rate": 0.0,
                "accepted_weak_rate": 0.0,
                "semantic_class_counts": {},
                "materiality_counts": {},
                "entity_fit_counts": {},
            },
        }


def build_evidence_vnext_packet_from_snapshot(snapshot: dict[str, Any]):
    packet = build_evidence_packet_v0(snapshot)
    observations = _observations_from_packet(packet, snapshot=snapshot)
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
    from src.research.evidence_vnext import EVIDENCE_VNEXT_VERSION, EvidenceVNextPacket

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


def build_vnext_evidence_graph_from_snapshot(snapshot: dict[str, Any]):
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
