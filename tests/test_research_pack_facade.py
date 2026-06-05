from __future__ import annotations

from src.research.research_pack_facade import build_recommended_research_pack


class _Recommendation:
    def __init__(self, builder: str):
        self.builder = builder

    def to_dict(self):
        return {"builder": self.builder, "promotion_status": "test"}


class _Graph:
    def summary(self):
        return {"claim_count": 2, "source_count": 1}


def test_facade_uses_legacy_when_graph_is_not_allowed(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.research.research_pack_facade.build_brand_research_pack_from_snapshot",
        lambda snapshot: "legacy-pack",
    )
    recommendation_mock = lambda snapshot: _Recommendation("graph")
    monkeypatch.setattr("src.research.research_pack_facade.recommend_research_pack_builder", recommendation_mock)

    result = build_recommended_research_pack({"run": {"id": 1}}, allow_graph=False)

    assert result.pack == "legacy-pack"
    assert result.builder == "legacy"
    assert result.source == "snapshot_builder"
    assert result.recommendation is None


def test_facade_uses_legacy_when_promotion_blocks_graph(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.research.research_pack_facade.recommend_research_pack_builder",
        lambda snapshot: _Recommendation("legacy"),
    )
    monkeypatch.setattr(
        "src.research.research_pack_facade.build_brand_research_pack_from_snapshot",
        lambda snapshot: "legacy-pack",
    )

    result = build_recommended_research_pack({"run": {"id": 2}})

    assert result.pack == "legacy-pack"
    assert result.builder == "legacy"
    assert result.recommendation == {"builder": "legacy", "promotion_status": "test"}


def test_facade_uses_graph_when_promotion_allows_graph(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.research.research_pack_facade.recommend_research_pack_builder",
        lambda snapshot: _Recommendation("graph"),
    )
    monkeypatch.setattr(
        "src.research.research_pack_facade.build_evidence_graph_from_snapshot",
        lambda snapshot: _Graph(),
    )
    monkeypatch.setattr(
        "src.research.research_pack_facade.build_brand_research_pack_from_graph",
        lambda graph: "graph-pack",
    )

    result = build_recommended_research_pack({"run": {"id": 3}})

    assert result.pack == "graph-pack"
    assert result.builder == "graph"
    assert result.source == "evidence_graph"
    assert result.graph_summary == {"claim_count": 2, "source_count": 1}
    assert result.recommendation == {"builder": "graph", "promotion_status": "test"}
