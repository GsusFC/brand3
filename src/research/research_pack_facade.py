"""Facade for choosing the BrandResearchPack builder.

Brand Audit and Magnetism both need the same decision: use the graph-backed pack
only when the promotion gate recommends it. Keeping that choice here avoids
runtime drift between callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config import BRAND3_BRAND_RESEARCH_VNEXT_PACK
from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot
from src.research.evidence_graph import build_evidence_graph_from_snapshot
from src.research.evidence_vnext import (
    build_evidence_vnext_packet_from_snapshot,
    build_vnext_evidence_graph_from_snapshot,
    compare_evidence_vnext_from_snapshot,
)
from src.research.evidence_vnext_report import build_batch_report
from src.research.research_pack_builder import build_brand_research_pack_from_graph
from src.research.research_pack_promotion import recommend_research_pack_builder


EVIDENCE_VNEXT_PACK_DECISION_VERSION = "research_pack_evidence_vnext_decision_v0_1"


@dataclass(frozen=True)
class RecommendedResearchPack:
    pack: Any
    builder: str
    graph_summary: dict[str, Any] | None = None
    recommendation: dict[str, Any] | None = None

    @property
    def source(self) -> str:
        if self.builder == "vnext_graph":
            return "evidence_vnext_graph"
        if self.builder == "graph":
            return "evidence_graph"
        return "snapshot_builder"

    def metadata_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "research_pack_source": self.source,
        }
        if self.graph_summary:
            payload["evidence_graph_summary"] = self.graph_summary
        if self.recommendation:
            payload["research_pack_recommendation"] = self.recommendation
        return payload


def build_recommended_research_pack(
    snapshot: dict[str, Any],
    *,
    allow_graph: bool = True,
) -> RecommendedResearchPack:
    """Build the recommended Research Pack for a persisted Brand Audit snapshot."""
    if not allow_graph:
        return RecommendedResearchPack(
            pack=build_brand_research_pack_from_snapshot(snapshot),
            builder="legacy",
        )

    recommendation = recommend_research_pack_builder(snapshot)
    recommendation_payload = recommendation.to_dict()
    if recommendation.builder != "graph":
        return RecommendedResearchPack(
            pack=build_brand_research_pack_from_snapshot(snapshot),
            builder="legacy",
            recommendation=recommendation_payload,
        )

    if BRAND3_BRAND_RESEARCH_VNEXT_PACK:
        vnext_decision = _vnext_builder_decision(snapshot)
        recommendation_payload = {
            **recommendation_payload,
            "evidence_vnext": vnext_decision,
        }
        if vnext_decision.get("builder") == "vnext_graph":
            graph = build_vnext_evidence_graph_from_snapshot(snapshot)
            return RecommendedResearchPack(
                pack=build_brand_research_pack_from_graph(graph),
                builder="vnext_graph",
                graph_summary=graph.summary(),
                recommendation=recommendation_payload,
            )

    graph = build_evidence_graph_from_snapshot(snapshot)
    return RecommendedResearchPack(
        pack=build_brand_research_pack_from_graph(graph),
        builder="graph",
        graph_summary=graph.summary(),
        recommendation=recommendation_payload,
    )


def _vnext_builder_decision(snapshot: dict[str, Any]) -> dict[str, Any]:
    try:
        comparison = compare_evidence_vnext_from_snapshot(snapshot)
        gate = build_evidence_vnext_packet_from_snapshot(snapshot)
        report = build_batch_report(
            [
                {
                    "vnext_comparison": comparison.to_dict(),
                    "vnext_gate": gate.to_dict(),
                }
            ]
        )
    except Exception as exc:
        return {
            "version": EVIDENCE_VNEXT_PACK_DECISION_VERSION,
            "enabled": True,
            "builder": "graph",
            "status": "fallback_graph",
            "reason_codes": ["evidence_vnext_decision_error"],
            "detail": str(exc)[:200],
        }

    readiness_rows = (report.get("readiness_matrix") or {}).get("rows") or []
    readiness = readiness_rows[0] if readiness_rows else {}
    readiness_status = str(readiness.get("readiness_status") or "")
    next_action = str(readiness.get("next_action") or "")
    totals = report.get("totals") or {}
    ready = readiness_status == "ready_after_shadow_policy" and next_action == "candidate_after_contract"
    return {
        "version": EVIDENCE_VNEXT_PACK_DECISION_VERSION,
        "enabled": True,
        "builder": "vnext_graph" if ready else "graph",
        "status": "ready" if ready else "not_ready",
        "readiness_status": readiness_status,
        "next_action": next_action,
        "reason_codes": list(readiness.get("remaining_reason_codes") or []),
        "accepted": int(totals.get("accepted") or 0),
        "review_required": int(totals.get("review_required") or 0),
        "rejected": int(totals.get("rejected") or 0),
        "material_lost_fields": int(totals.get("material_lost_fields") or 0),
    }
