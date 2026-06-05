"""Facade for choosing the BrandResearchPack builder.

Brand Audit and Magnetism both need the same decision: use the graph-backed pack
only when the promotion gate recommends it. Keeping that choice here avoids
runtime drift between callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot
from src.research.evidence_graph import build_evidence_graph_from_snapshot
from src.research.research_pack_builder import build_brand_research_pack_from_graph
from src.research.research_pack_promotion import recommend_research_pack_builder


@dataclass(frozen=True)
class RecommendedResearchPack:
    pack: Any
    builder: str
    graph_summary: dict[str, Any] | None = None
    recommendation: dict[str, Any] | None = None

    @property
    def source(self) -> str:
        if self.builder == "graph":
            return "evidence_graph"
        return "snapshot_builder"


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

    graph = build_evidence_graph_from_snapshot(snapshot)
    return RecommendedResearchPack(
        pack=build_brand_research_pack_from_graph(graph),
        builder="graph",
        graph_summary=graph.summary(),
        recommendation=recommendation_payload,
    )
