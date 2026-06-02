from __future__ import annotations

from src.research.contextdev_candidate_gate import (
    BLOCKED,
    PROMOTABLE,
    REVIEW_REQUIRED,
    evaluate_contextdev_candidate_promotion,
    evaluate_contextdev_summary_promotion,
)
from src.research.contextdev_candidates import ContextDevEvidenceCandidate


def test_contextdev_gate_promotes_textual_visual_and_product_candidates() -> None:
    report = evaluate_contextdev_candidate_promotion(
        [
            _candidate("visual_colors", "visual_identity", '{"accent":"#111111"}'),
            _candidate("product_profile", "product_extraction", "Example Platform helps AI teams evaluate agents."),
        ]
    )

    assert report.status_counts == {PROMOTABLE: 2, REVIEW_REQUIRED: 0, BLOCKED: 0}
    assert [decision.target_contract for decision in report.decisions] == [
        "research_pack.visual_or_conceptual_signals",
        "research_pack.product_summary",
    ]
    assert report.decisions[0].reason_codes == ("textual_visual_signal",)
    assert report.decisions[1].reason_codes == ("product_candidate_has_substance",)


def test_contextdev_gate_requires_review_for_identity_industry_and_visual_assets() -> None:
    report = evaluate_contextdev_candidate_promotion(
        [
            _candidate("entity_profile", "entity_resolution", "Example builds agent infrastructure."),
            _candidate("industry_classification", "industry_classification", '{"naics":[{"code":"541511"}]}'),
            _candidate("visual_screenshot", "visual_evidence", "viewport: https://cdn.example.com/screen.png"),
        ]
    )

    assert report.status_counts == {PROMOTABLE: 0, REVIEW_REQUIRED: 3, BLOCKED: 0}
    assert [decision.target_contract for decision in report.decisions] == [
        "research_pack.resolved_entity",
        "research_pack.category",
        "visual_signature.input",
    ]
    assert report.decisions[0].reason_codes == ("identity_affects_target_selection",)
    assert report.decisions[2].reason_codes == ("binary_visual_asset_not_research_pack_text",)


def test_contextdev_gate_blocks_candidates_without_traceable_text_or_source() -> None:
    report = evaluate_contextdev_candidate_promotion(
        [
            _candidate("visual_fonts", "visual_identity", ""),
            _candidate("product_profile", "product_extraction", "Example Platform", source_url="not-a-url"),
        ]
    )

    assert report.status_counts == {PROMOTABLE: 0, REVIEW_REQUIRED: 0, BLOCKED: 2}
    assert report.decisions[0].reason_codes == ("missing_candidate_text",)
    assert report.decisions[1].reason_codes == ("invalid_or_missing_source_url",)
    assert all(decision.target_contract == "none" for decision in report.decisions)


def test_contextdev_gate_evaluates_serialized_summary() -> None:
    summary = {
        "candidates": [
            _candidate("visual_fonts", "visual_identity", "Example Sans").to_dict(),
            _candidate("brand_slogan", "entity_resolution", "Agents that work").to_dict(),
        ]
    }

    report = evaluate_contextdev_summary_promotion(summary)

    assert report.to_dict()["decision_count"] == 2
    assert report.status_counts == {PROMOTABLE: 1, REVIEW_REQUIRED: 1, BLOCKED: 0}
    assert report.channel_counts == {"entity_resolution": 1, "visual_identity": 1}


def _candidate(
    candidate_type: str,
    supports_channel: str,
    text: str,
    *,
    source_url: str = "https://example.com",
) -> ContextDevEvidenceCandidate:
    return ContextDevEvidenceCandidate(
        candidate_id=f"ctxdev_{candidate_type}",
        candidate_type=candidate_type,
        supports_channel=supports_channel,
        text=text,
        source_url=source_url,
        raw_ref="test",
    )
