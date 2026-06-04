from __future__ import annotations

from types import SimpleNamespace

import src.research.research_pack_promotion as promotion_module
from src.research.research_pack_promotion import (
    BLOCKED,
    PROMOTABLE,
    REVIEW_REQUIRED,
    evaluate_research_pack_promotion,
    recommend_research_pack_builder,
)


def test_evaluate_research_pack_promotion_marks_clean_graph_promotable(monkeypatch) -> None:
    monkeypatch.setattr(
        promotion_module,
        "compare_pack_builders_from_snapshot",
        lambda snapshot: SimpleNamespace(
            run_id=11,
            brand_name="Base44",
            url="https://base44.com",
            graph_summary={"claim_count": 5, "source_count": 3},
            summary=lambda: {
                "gained_count": 2,
                "lost_count": 0,
                "changed_count": 1,
                "entity_type_changed": False,
                "parent_brand_changed": False,
                "gained_fields": ["offer"],
                "lost_fields": [],
            },
        ),
    )

    report = evaluate_research_pack_promotion({"run": {"id": 11}})

    assert report.version == "research_pack_promotion_v0_1"
    assert report.status_counts[PROMOTABLE] == 1
    decision = report.decisions[0]
    assert decision.status == PROMOTABLE
    assert decision.target_contract == "research_pack.graph"
    assert decision.reason_codes == ("graph_no_regressions",)


def test_evaluate_research_pack_promotion_blocks_empty_graph(monkeypatch) -> None:
    monkeypatch.setattr(
        promotion_module,
        "compare_pack_builders_from_snapshot",
        lambda snapshot: SimpleNamespace(
            run_id=12,
            brand_name="Empty",
            url="https://empty.example",
            graph_summary={"claim_count": 0, "source_count": 0},
            summary=lambda: {
                "gained_count": 0,
                "lost_count": 0,
                "changed_count": 0,
                "entity_type_changed": False,
                "parent_brand_changed": False,
                "gained_fields": [],
                "lost_fields": [],
            },
        ),
    )

    report = evaluate_research_pack_promotion({"run": {"id": 12}})

    assert report.status_counts[BLOCKED] == 1
    decision = report.decisions[0]
    assert decision.status == BLOCKED
    assert decision.reason_codes == ("graph_empty",)


def test_evaluate_research_pack_promotion_requires_review_for_identity_changes(monkeypatch) -> None:
    monkeypatch.setattr(
        promotion_module,
        "compare_pack_builders_from_snapshot",
        lambda snapshot: SimpleNamespace(
            run_id=13,
            brand_name="TinyNature",
            url="https://lab.naturaumana.ai",
            graph_summary={"claim_count": 3, "source_count": 2},
            summary=lambda: {
                "gained_count": 1,
                "lost_count": 0,
                "changed_count": 1,
                "entity_type_changed": True,
                "parent_brand_changed": False,
                "gained_fields": ["offer"],
                "lost_fields": [],
            },
        ),
    )

    report = evaluate_research_pack_promotion({"run": {"id": 13}})

    assert report.status_counts[REVIEW_REQUIRED] == 1
    decision = report.decisions[0]
    assert decision.status == REVIEW_REQUIRED
    assert "entity_type_changed" in decision.reason_codes


def test_recommend_research_pack_builder_prefers_graph_for_promotable_snapshot(monkeypatch) -> None:
    monkeypatch.setattr(
        promotion_module,
        "compare_pack_builders_from_snapshot",
        lambda snapshot: SimpleNamespace(
            run_id=14,
            brand_name="Sklum",
            url="https://www.sklum.com",
            graph_summary={"claim_count": 10, "source_count": 15},
            summary=lambda: {
                "gained_count": 2,
                "lost_count": 0,
                "changed_count": 1,
                "entity_type_changed": False,
                "parent_brand_changed": False,
                "gained_fields": ["offer"],
                "lost_fields": [],
            },
        ),
    )

    recommendation = recommend_research_pack_builder({"run": {"id": 14}})

    assert recommendation.builder == "graph"
    assert recommendation.promotion_status == PROMOTABLE
    assert recommendation.reason_codes == ("graph_no_regressions",)


def test_recommend_research_pack_builder_keeps_legacy_when_not_promotable(monkeypatch) -> None:
    monkeypatch.setattr(
        promotion_module,
        "compare_pack_builders_from_snapshot",
        lambda snapshot: SimpleNamespace(
            run_id=15,
            brand_name="Example",
            url="https://example.com",
            graph_summary={"claim_count": 2, "source_count": 1},
            summary=lambda: {
                "gained_count": 0,
                "lost_count": 3,
                "changed_count": 2,
                "entity_type_changed": False,
                "parent_brand_changed": False,
                "gained_fields": [],
                "lost_fields": ["offer"],
            },
        ),
    )

    recommendation = recommend_research_pack_builder({"run": {"id": 15}})

    assert recommendation.builder == "legacy"
    assert recommendation.promotion_status == BLOCKED
    assert "legacy_fields_lost" in recommendation.reason_codes
