from __future__ import annotations

from src.research.research_pack_facade import (
    RecommendedResearchPack,
    _vnext_builder_decision,
    build_recommended_research_pack,
)


class _Recommendation:
    def __init__(self, builder: str):
        self.builder = builder

    def to_dict(self):
        return {"builder": self.builder, "promotion_status": "test"}


class _Graph:
    def summary(self):
        return {"claim_count": 2, "source_count": 1}


def _patch_vnext_decision_inputs(monkeypatch, report: dict) -> None:
    class _Comparison:
        def to_dict(self):
            return {}

    class _Gate:
        def to_dict(self):
            return {}

    monkeypatch.setattr("src.research.research_pack_facade.compare_evidence_vnext_from_snapshot", lambda snapshot: _Comparison())
    monkeypatch.setattr("src.research.research_pack_facade.build_evidence_vnext_packet_from_snapshot", lambda snapshot: _Gate())
    monkeypatch.setattr("src.research.research_pack_facade.build_batch_report", lambda rows: report)


def test_vnext_builder_decision_promotes_ready_contract(monkeypatch) -> None:
    _patch_vnext_decision_inputs(
        monkeypatch,
        {
            "readiness_matrix": {
                "rows": [
                    {
                        "readiness_status": "ready_after_contract",
                        "next_action": "candidate_after_contract",
                        "human_required": False,
                        "remaining_reason_codes": ["no_promotion_blockers_detected"],
                    }
                ]
            },
            "totals": {"accepted": 4, "review_required": 1, "rejected": 2, "material_lost_fields": 0},
            "semantic_evidence": {"accepted_material": 3, "accepted_weak": 1},
        },
    )

    decision = _vnext_builder_decision({"run": {"id": 10}})

    assert decision["builder"] == "vnext_graph"
    assert decision["status"] == "ready_after_contract"
    assert decision["human_required"] is False
    assert decision["material_lost_fields"] == 0
    assert decision["accepted_material"] == 3
    assert decision["accepted_weak"] == 1


def test_vnext_builder_decision_blocks_human_required_contract(monkeypatch) -> None:
    _patch_vnext_decision_inputs(
        monkeypatch,
        {
            "readiness_matrix": {
                "rows": [
                    {
                        "readiness_status": "needs_manual_audit",
                        "next_action": "manual_audit_projected_material_changes",
                        "human_required": True,
                        "remaining_reason_codes": ["manual_audit_required_for_material_field_changes"],
                    }
                ]
            },
            "totals": {"accepted": 4, "review_required": 2, "rejected": 2, "material_lost_fields": 0},
            "semantic_evidence": {"accepted_material": 3, "accepted_weak": 1},
        },
    )

    decision = _vnext_builder_decision({"run": {"id": 11}})

    assert decision["builder"] == "graph"
    assert decision["status"] == "not_ready"
    assert decision["human_required"] is True


def test_vnext_builder_decision_blocks_deprecated_shadow_policy_status(monkeypatch) -> None:
    _patch_vnext_decision_inputs(
        monkeypatch,
        {
            "readiness_matrix": {
                "rows": [
                    {
                        "readiness_status": "ready_after_shadow_policy",
                        "next_action": "candidate_after_contract",
                        "human_required": False,
                        "remaining_reason_codes": [],
                    }
                ]
            },
            "totals": {"accepted": 4, "review_required": 0, "rejected": 2, "material_lost_fields": 0},
            "semantic_evidence": {"accepted_material": 3, "accepted_weak": 1},
        },
    )

    decision = _vnext_builder_decision({"run": {"id": 13}})

    assert decision["builder"] == "graph"
    assert decision["status"] == "not_ready"
    assert decision["readiness_status"] == "ready_after_shadow_policy"


def test_vnext_builder_decision_blocks_material_loss(monkeypatch) -> None:
    _patch_vnext_decision_inputs(
        monkeypatch,
        {
            "readiness_matrix": {
                "rows": [
                    {
                        "readiness_status": "ready_after_contract",
                        "next_action": "candidate_after_contract",
                        "human_required": False,
                        "remaining_reason_codes": [],
                    }
                ]
            },
            "totals": {"accepted": 4, "review_required": 0, "rejected": 2, "material_lost_fields": 1},
            "semantic_evidence": {"accepted_material": 3, "accepted_weak": 1},
        },
    )

    decision = _vnext_builder_decision({"run": {"id": 12}})

    assert decision["builder"] == "graph"
    assert decision["status"] == "not_ready"
    assert decision["material_lost_fields"] == 1


def test_vnext_builder_decision_blocks_weak_evidence_dominance(monkeypatch) -> None:
    _patch_vnext_decision_inputs(
        monkeypatch,
        {
            "readiness_matrix": {
                "rows": [
                    {
                        "readiness_status": "ready_after_contract",
                        "next_action": "candidate_after_contract",
                        "human_required": False,
                        "remaining_reason_codes": ["no_promotion_blockers_detected"],
                    }
                ]
            },
            "totals": {"accepted": 14, "review_required": 1, "rejected": 6, "material_lost_fields": 0},
            "semantic_evidence": {"accepted_material": 5, "accepted_weak": 9},
            "manual_audit_queue": [
                {
                    "audit_verdict": "alias_confirmation_review",
                    "audit_reason_codes": ["external_profile_alias_review_present"],
                }
            ],
        },
    )

    decision = _vnext_builder_decision({"run": {"id": 292}})

    assert decision["builder"] == "graph"
    assert decision["status"] == "not_ready"
    assert decision["accepted_material"] == 5
    assert decision["accepted_weak"] == 9
    assert decision["alias_review_present"] is True
    assert "weak_evidence_exceeds_material_evidence" in decision["reason_codes"]
    assert "promotion_gate_alias_review_with_weak_evidence_dominance" in decision["reason_codes"]


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
        "src.research.research_pack_facade._vnext_builder_decision",
        lambda snapshot: {"builder": "graph", "status": "not_ready"},
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
    assert result.recommendation == {
        "builder": "graph",
        "promotion_status": "test",
        "evidence_vnext": {"builder": "graph", "status": "not_ready"},
    }


def test_facade_uses_vnext_graph_when_vnext_gate_is_ready(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.research.research_pack_facade.recommend_research_pack_builder",
        lambda snapshot: _Recommendation("graph"),
    )
    monkeypatch.setattr(
        "src.research.research_pack_facade._vnext_builder_decision",
        lambda snapshot: {"builder": "vnext_graph", "status": "ready"},
    )
    monkeypatch.setattr(
        "src.research.research_pack_facade.build_vnext_evidence_graph_from_snapshot",
        lambda snapshot: _Graph(),
    )
    monkeypatch.setattr(
        "src.research.research_pack_facade.build_brand_research_pack_from_graph",
        lambda graph: "vnext-pack",
    )

    result = build_recommended_research_pack({"run": {"id": 33}})

    assert result.pack == "vnext-pack"
    assert result.builder == "vnext_graph"
    assert result.source == "evidence_vnext_graph"
    assert result.graph_summary == {"claim_count": 2, "source_count": 1}
    assert result.recommendation == {
        "builder": "graph",
        "promotion_status": "test",
        "evidence_vnext": {"builder": "vnext_graph", "status": "ready"},
    }


def test_recommended_research_pack_metadata_payload_owns_source_fields() -> None:
    graph_result = RecommendedResearchPack(
        pack="graph-pack",
        builder="graph",
        graph_summary={"claim_count": 2},
        recommendation={"builder": "graph", "promotion_status": "promotable"},
    )
    legacy_result = RecommendedResearchPack(pack="legacy-pack", builder="legacy")
    vnext_result = RecommendedResearchPack(
        pack="vnext-pack",
        builder="vnext_graph",
        graph_summary={"claim_count": 3},
        recommendation={
            "builder": "graph",
            "promotion_status": "promotable",
            "evidence_vnext": {"builder": "vnext_graph", "status": "ready"},
        },
    )

    assert graph_result.metadata_payload() == {
        "research_pack_source": "evidence_graph",
        "evidence_graph_summary": {"claim_count": 2},
        "research_pack_recommendation": {
            "builder": "graph",
            "promotion_status": "promotable",
        },
    }
    assert legacy_result.metadata_payload() == {
        "research_pack_source": "snapshot_builder",
    }
    assert vnext_result.metadata_payload() == {
        "research_pack_source": "evidence_vnext_graph",
        "evidence_graph_summary": {"claim_count": 3},
        "research_pack_recommendation": {
            "builder": "graph",
            "promotion_status": "promotable",
            "evidence_vnext": {"builder": "vnext_graph", "status": "ready"},
        },
    }
