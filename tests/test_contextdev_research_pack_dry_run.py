from __future__ import annotations

from src.reports.brand_research_pack import BrandResearchPack, EntityResolution
from src.research.contextdev_candidates import ContextDevEvidenceCandidate, summarize_contextdev_candidates
from src.research.contextdev_research_pack_dry_run import (
    build_contextdev_research_pack_dry_run,
    filter_contextdev_candidate_summary_for_pack,
)


def test_contextdev_research_pack_dry_run_appends_promotable_signals_without_mutating_original() -> None:
    pack = _pack(product_summary="Existing product synthesis.")
    summary = summarize_contextdev_candidates(
        [
            _candidate("visual_fonts", "visual_identity", "Example Sans, Example Serif"),
            _candidate("product_profile", "product_extraction", "Example Platform helps AI teams evaluate agents."),
            _candidate("entity_profile", "entity_resolution", "Example builds agent infrastructure."),
        ]
    )

    result = build_contextdev_research_pack_dry_run(pack, summary)
    payload = result.to_dict()

    assert pack.visual_or_conceptual_signals == ["existing visual signal"]
    assert pack.confidence_notes == ["existing confidence note"]
    assert payload["original_pack"]["visual_or_conceptual_signals"] == ["existing visual signal"]
    assert payload["enriched_pack"]["visual_or_conceptual_signals"] == [
        "existing visual signal",
        "Font signal: Example Sans, Example Serif, suggesting a defined visual voice.",
    ]
    assert payload["enriched_pack"]["product_summary"] == "Existing product synthesis."
    assert "Context.dev product candidate: Example Platform helps AI teams evaluate agents." in payload["enriched_pack"]["confidence_notes"]
    assert payload["promotion_report"]["status_counts"] == {
        "promotable": 2,
        "review_required": 1,
        "blocked": 0,
    }
    assert [update["field"] for update in payload["field_updates"]] == [
        "visual_or_conceptual_signals",
        "confidence_notes",
    ]


def test_contextdev_research_pack_dry_run_sets_empty_product_summary() -> None:
    pack = _pack(product_summary="")
    summary = summarize_contextdev_candidates(
        [_candidate("product_profile", "product_extraction", "Example Platform helps AI teams evaluate agents.")]
    )

    result = build_contextdev_research_pack_dry_run(pack.to_dict(), summary)
    payload = result.to_dict()

    assert payload["enriched_pack"]["product_summary"] == "Example Platform helps AI teams evaluate agents."
    assert payload["field_updates"][0]["action"] == "set"
    assert payload["field_updates"][0]["field"] == "product_summary"


def test_contextdev_research_pack_dry_run_deduplicates_existing_visual_signal() -> None:
    pack = _pack(product_summary="Existing product synthesis.")
    pack.visual_or_conceptual_signals = ["Font signal: existing visual signal, suggesting a defined visual voice."]
    summary = summarize_contextdev_candidates(
        [_candidate("visual_fonts", "visual_identity", "existing visual signal")]
    )

    result = build_contextdev_research_pack_dry_run(pack, summary)
    payload = result.to_dict()

    assert payload["enriched_pack"]["visual_or_conceptual_signals"] == [
        "Font signal: existing visual signal, suggesting a defined visual voice."
    ]
    assert payload["field_updates"] == []


def test_contextdev_research_pack_dry_run_filters_candidates_by_pack_domain() -> None:
    pack = _pack(product_summary="Existing product synthesis.")
    summary = summarize_contextdev_candidates(
        [
            _candidate("visual_fonts", "visual_identity", "Example Sans", source_url="https://www.example.com/fonts"),
            _candidate("visual_colors", "visual_identity", "Other colors", source_url="https://other.example.net"),
        ]
    )

    filtered = filter_contextdev_candidate_summary_for_pack(pack, summary)
    result = build_contextdev_research_pack_dry_run(pack, summary)
    payload = result.to_dict()

    assert filtered["candidate_count"] == 1
    assert filtered["by_channel"] == {"visual_identity": 1}
    assert [candidate["source_url"] for candidate in filtered["candidates"]] == ["https://www.example.com/fonts"]
    assert payload["enriched_pack"]["visual_or_conceptual_signals"] == [
        "existing visual signal",
        "Font signal: Example Sans, suggesting a defined visual voice.",
    ]


def _pack(*, product_summary: str) -> BrandResearchPack:
    return BrandResearchPack(
        version="brand_research_pack_v0_1",
        input_url="https://example.com",
        resolved_entity=EntityResolution(resolved_entity="Example", entity_type="brand"),
        entity_type="brand",
        source_map={},
        product_summary=product_summary,
        visual_or_conceptual_signals=["existing visual signal"],
        confidence_notes=["existing confidence note"],
    )


def _candidate(
    candidate_type: str,
    supports_channel: str,
    text: str,
    *,
    source_url: str = "https://example.com",
) -> ContextDevEvidenceCandidate:
    return ContextDevEvidenceCandidate(
        candidate_id=f"ctxdev_{candidate_type}_{len(text)}",
        candidate_type=candidate_type,
        supports_channel=supports_channel,
        text=text,
        source_url=source_url,
        raw_ref="test",
    )
