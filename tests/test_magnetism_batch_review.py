from __future__ import annotations

from scripts.magnetism_brand_audit_batch_review import (
    QUALITY_BLOCKS,
    _balanced_quality_rows,
    _block_quality,
    _build_row,
    _build_summary,
    _dedupe_snapshots,
    _extraction_diagnosis,
    _known_noise_hits,
    _render_markdown,
    _visible_interpretation_values,
)


def test_batch_noise_hits_ignore_rejected_packet_lines() -> None:
    result = {
        "strategic_evidence_packet": {
            "rejected": [
                {
                    "text": "Render UI before vehicle_state sync when minimum required state is present.",
                    "reason": "low_strategic_signal",
                }
            ]
        },
        "diagnosis": {"headline": "No visible noise."},
        "system_reading": {"strategic_tensions": []},
    }
    visible = _visible_interpretation_values(
        tldr={
            "value_proposition": {
                "answer": "A product system for modern teams.",
                "evidence_used": ["A product system for modern teams."],
            }
        },
        layers={
            "netspace": {
                "finding": "Detected concrete value proposition.",
                "evidence": "A product system for modern teams.",
            }
        },
        result=result,
    )

    assert _known_noise_hits(result) == ["vehicle_state"]
    assert _known_noise_hits(visible) == []


def test_batch_flags_non_offer_brand_signal_separately_from_missing_vp() -> None:
    row = _build_row(
        {"run": {"id": 1, "brand_name": "MSCHF", "url": "https://mschf.com"}},
        {
            "metrics": {},
            "evidence_packet_summary": {
                "strategic_group_counts": {"vision_language": 1, "personality_tone": 1},
                "strategic_warnings": ["No product offer evidence group found."],
            },
            "magenta_circle": {
                "gamespace": {"detected": True},
                "tactispace": {"detected": True},
            },
            "tldr_brand3": {
                "vision": {"answer": "A cultural ambition signal.", "human_review_recommended": True},
                "value_proposition": {"mode": "not_detected", "claim_type": "absent"},
            },
        },
    )

    assert "non_offer_brand_signal" in row["review_flags"]
    assert "missing_value_proposition" not in row["review_flags"]


def test_batch_flags_no_usable_evidence_separately_from_missing_vp() -> None:
    row = _build_row(
        {"run": {"id": 2, "brand_name": "Old Run", "url": "https://old.test"}},
        {
            "metrics": {},
            "evidence_packet_summary": {
                "strategic_group_counts": {},
                "strategic_warnings": ["No strategically usable evidence groups found."],
            },
            "magenta_circle": {},
            "tldr_brand3": {
                "value_proposition": {"mode": "not_detected", "claim_type": "absent"},
            },
        },
    )

    assert "no_usable_strategic_evidence" in row["review_flags"]
    assert "missing_value_proposition" not in row["review_flags"]


def test_batch_flags_limited_observable_layers_for_narrow_but_usable_signal() -> None:
    row = _build_row(
        {"run": {"id": 3, "brand_name": "Focused Brand", "url": "https://focused.test"}},
        {
            "metrics": {},
            "evidence_packet_summary": {
                "strategic_group_counts": {"product_offer": 2, "audience": 1, "outcome": 1, "values_language": 1},
                "strategic_warnings": [],
            },
            "magenta_circle": {
                "netspace": {"detected": True},
                "ambientspace": {"detected": True},
            },
            "tldr_brand3": {
                "value_proposition": {"answer": "A focused offer for a clear audience.", "confidence": "high"},
                "values": {"answer": ["trust"], "confidence": "medium"},
            },
        },
    )

    assert "limited_observable_layers" in row["review_flags"]
    assert "weak_layer_coverage" not in row["review_flags"]


def test_batch_expands_human_review_blocks_into_specific_flags() -> None:
    row = _build_row(
        {"run": {"id": 4, "brand_name": "Vision Brand", "url": "https://vision.test"}},
        {
            "metrics": {},
            "evidence_packet_summary": {"strategic_group_counts": {"vision_language": 1}},
            "magenta_circle": {"tactispace": {"detected": True}},
            "tldr_brand3": {
                "vision": {
                    "answer": "A future-facing category signal.",
                    "confidence": "medium",
                    "human_review_recommended": True,
                },
                "core_purpose": {
                    "answer": "A purpose hypothesis.",
                    "confidence": "medium",
                    "human_review_recommended": True,
                },
            },
        },
    )

    assert "interpreted_vision_needs_review" in row["review_flags"]
    assert "purpose_hypothesis_needs_review" in row["review_flags"]
    assert "human_review_blocks:core_purpose,vision" in row["review_flags"]


def test_batch_flags_mission_not_declared_when_offer_exists() -> None:
    row = _build_row(
        {"run": {"id": 5, "brand_name": "Offer Brand", "url": "https://offer.test"}},
        {
            "metrics": {},
            "evidence_packet_summary": {
                "strategic_group_counts": {"product_offer": 2, "audience": 1, "outcome": 1},
                "strategic_warnings": [],
            },
            "magenta_circle": {"netspace": {"detected": True}},
            "tldr_brand3": {
                "value_proposition": {"answer": "A concrete offer.", "confidence": "high"},
                "mission": {"mode": "not_detected", "claim_type": "absent"},
            },
        },
    )

    assert "mission_not_declared" in row["review_flags"]


def test_batch_does_not_flag_mission_absence_when_no_usable_evidence() -> None:
    row = _build_row(
        {"run": {"id": 6, "brand_name": "Empty Brand", "url": "https://empty.test"}},
        {
            "metrics": {},
            "evidence_packet_summary": {"strategic_group_counts": {}},
            "magenta_circle": {},
            "tldr_brand3": {
                "mission": {"mode": "not_detected", "claim_type": "absent"},
                "value_proposition": {"mode": "not_detected", "claim_type": "absent"},
            },
        },
    )

    assert "mission_not_declared" not in row["review_flags"]


def test_batch_flags_value_prop_audience_gap() -> None:
    row = _build_row(
        {"run": {"id": 7, "brand_name": "Audience Gap", "url": "https://audience.test"}},
        {
            "metrics": {},
            "evidence_packet_summary": {
                "strategic_group_counts": {"product_offer": 1, "outcome": 1},
            },
            "magenta_circle": {"netspace": {"detected": True}},
            "tldr_brand3": {
                "value_proposition": {
                    "answer": "A concrete offer with outcome.",
                    "confidence": "medium",
                    "counter_evidence": ["The available value proposition evidence does not clearly name the audience."],
                },
                "mission": {"mode": "not_detected", "claim_type": "absent"},
            },
        },
    )

    assert "value_prop_audience_not_named" in row["review_flags"]


def test_dedupe_snapshots_keeps_latest_run_per_brand_url() -> None:
    snapshots = [
        {"run": {"id": 10, "brand_name": "Wio", "url": "https://wio.test"}},
        {"run": {"id": 12, "brand_name": "Wio Capital", "url": "https://wio.test/"}},
        {"run": {"id": 11, "brand_name": "Other", "url": "https://other.test"}},
    ]

    deduped = _dedupe_snapshots(snapshots)

    assert [item["run"]["id"] for item in deduped] == [12, 11]


def test_block_quality_marks_high_clean_block_as_strong() -> None:
    quality = _block_quality(
        "value_proposition",
        {"answer": "A platform for finance teams.", "confidence": "high", "counter_evidence": []},
    )

    assert quality == {"status": "strong", "reasons": []}


def test_block_quality_marks_gap_block_as_usable() -> None:
    quality = _block_quality(
        "value_proposition",
        {
            "answer": "A platform for finance teams.",
            "confidence": "medium",
            "counter_evidence": ["The available value proposition evidence does not clearly state the outcome or change for the audience."],
        },
    )

    assert quality["status"] == "usable"
    assert quality["reasons"] == ["missing_outcome"]


def test_block_quality_marks_missing_and_noisy_blocks() -> None:
    missing = _block_quality("mission", {"mode": "not_detected", "claim_type": "absent"})
    noisy = _block_quality(
        "vision",
        {"answer": "A future claim.", "confidence": "high"},
        noise_hits=["__NEXT_DATA__"],
    )

    assert missing == {"status": "missing", "reasons": ["no_answer"]}
    assert noisy["status"] == "weak"
    assert noisy["reasons"] == ["visible_noise"]


def test_build_row_includes_block_quality_fields() -> None:
    row = _build_row(
        {"run": {"id": 8, "brand_name": "Quality Brand", "url": "https://quality.test"}},
        {
            "metrics": {},
            "evidence_packet_summary": {
                "evidence_quality": {"status": "strong", "reasons": []},
                "raw_input_count": 1,
                "evidence_item_count": 1,
                "strategic_group_counts": {"product_offer": 1, "audience": 1, "outcome": 1},
                "strategic_source_counts": {"owned_raw": 1},
                "strategic_rejected_count": 0,
                "strategic_rejected_reason_counts": {},
            },
            "magenta_circle": {"netspace": {"detected": True}},
            "tldr_brand3": {
                "value_proposition": {"answer": "A clear offer for teams.", "confidence": "high"},
                "mission": {"mode": "not_detected", "claim_type": "absent"},
                "vision": {"answer": "A future signal.", "confidence": "medium", "human_review_recommended": True},
            },
        },
    )

    assert row["canonical_evidence_quality"] == "strong"
    assert row["extraction_diagnosis"] == "strong"
    assert row["evidence_packet"]["evidence_quality"] == {"status": "strong", "reasons": []}
    assert row["evidence_packet"]["extraction_diagnosis"]["owned_source_count"] == 1
    assert row["value_proposition_quality"] == "strong"
    assert row["mission_quality"] == "missing"
    assert row["vision_quality"] == "usable"
    assert row["vision_quality_reasons"] == ["human_review"]


def test_summary_counts_block_quality() -> None:
    summary = _build_summary(
        [
            {"canonical_evidence_quality": "strong", "extraction_diagnosis": "strong", "value_proposition_quality": "strong", "mission_quality": "missing", "vision_quality": "usable"},
            {"canonical_evidence_quality": "weak", "extraction_diagnosis": "brand_sparse", "value_proposition_quality": "weak", "mission_quality": "missing", "vision_quality": "missing"},
        ]
    )

    assert summary["canonical_evidence_quality"] == {"strong": 1, "weak": 1}
    assert summary["extraction_diagnosis"] == {"strong": 1, "brand_sparse": 1}
    assert summary["block_quality"]["value_proposition"] == {"strong": 1, "weak": 1}
    assert summary["block_quality"]["mission"] == {"missing": 2}
    assert summary["block_quality"]["vision"] == {"usable": 1, "missing": 1}


def test_render_markdown_includes_block_quality_section() -> None:
    payload = {
        "generated_at": "2026-05-24T00:00:00+00:00",
        "db_path": "data/brand3.sqlite3",
        "run_count": 1,
        "summary": {
            "value_proposition_confidence": {"high": 1},
            "mission_confidence": {"low": 1},
            "vision_confidence": {"medium": 1},
            "canonical_evidence_quality": {"weak": 1},
            "extraction_diagnosis": {"third_party_heavy": 1},
            "block_quality": {
                "value_proposition": {"strong": 1},
                "mission": {"missing": 1},
                "vision": {"usable": 1},
            },
        },
        "rows": [
            {
                "run_id": 9,
                "brand": "Quality Brand",
                "detected_layers": [],
                "detected_block_count": 1,
                "review_flags": [],
                "canonical_evidence_quality": "weak",
                "canonical_evidence_quality_reasons": ["no_audience"],
                "extraction_diagnosis": "third_party_heavy",
                "extraction_diagnosis_reasons": ["third_party_heavy", "missing_audience"],
                "value_proposition": "A clear offer.",
                "value_proposition_confidence": "high",
                "value_proposition_quality": "strong",
                "value_proposition_quality_reasons": [],
                "value_proposition_gaps": [],
                "mission": "",
                "mission_confidence": "low",
                "mission_quality": "missing",
                "mission_quality_reasons": ["no_answer"],
                "mission_gaps": [],
                "vision": "A future signal.",
                "vision_confidence": "medium",
                "vision_quality": "usable",
                "vision_quality_reasons": ["human_review"],
                "vision_gaps": [],
                "evidence_packet": {},
            }
        ],
    }

    markdown = _render_markdown(payload)

    assert "Canonical evidence quality" in markdown
    assert "Extraction diagnosis" in markdown
    assert "weak (no_audience)" in markdown
    assert "third_party_heavy (third_party_heavy, missing_audience)" in markdown
    assert "VP quality" in markdown
    assert "## Block Quality Examples" in markdown
    assert "usable (human_review)" in markdown


def test_balanced_quality_rows_includes_each_available_status() -> None:
    rows = [
        {"brand": "Missing A", "value_proposition_quality": "missing"},
        {"brand": "Missing B", "value_proposition_quality": "missing"},
        {"brand": "Usable A", "value_proposition_quality": "usable"},
        {"brand": "Strong A", "value_proposition_quality": "strong"},
        {"brand": "Weak A", "value_proposition_quality": "weak"},
    ]

    selected = _balanced_quality_rows(rows, "value_proposition", limit=4)

    assert [row["value_proposition_quality"] for row in selected] == [
        "weak",
        "missing",
        "usable",
        "strong",
    ]


def test_batch_quality_blocks_cover_full_tldr_contract() -> None:
    assert QUALITY_BLOCKS == (
        "core_purpose",
        "magnetism",
        "value_proposition",
        "personality",
        "brand_idea",
        "attributes",
        "values",
        "mission",
        "vision",
    )


def test_build_row_includes_quality_fields_for_all_tldr_blocks() -> None:
    row = _build_row(
        {"run": {"id": 10, "brand_name": "Full Quality", "url": "https://quality.test"}},
        {
            "metrics": {},
            "evidence_packet_summary": {"strategic_group_counts": {"product_offer": 1}},
            "magenta_circle": {"netspace": {"detected": True}},
            "tldr_brand3": {
                "core_purpose": {
                    "answer": "A purpose hypothesis.",
                    "confidence": "medium",
                    "human_review_recommended": True,
                },
                "magnetism": {"answer": "A memorable signal.", "confidence": "high"},
                "value_proposition": {"answer": "A concrete offer.", "confidence": "high"},
                "personality": {"answer": "Precise and pragmatic.", "confidence": "medium"},
                "brand_idea": {"mode": "not_detected", "claim_type": "absent"},
                "attributes": {"answer": ["fast", "secure"], "confidence": "medium"},
                "values": {"answer": ["trust"], "confidence": "medium"},
                "mission": {"mode": "not_detected", "claim_type": "absent"},
                "vision": {"answer": "A future signal.", "confidence": "medium", "human_review_recommended": True},
            },
        },
    )

    for block in QUALITY_BLOCKS:
        assert block in row
        assert f"{block}_confidence" in row
        assert f"{block}_quality" in row
        assert f"{block}_quality_reasons" in row
        assert f"{block}_gaps" in row

    assert row["block_quality"]["brand_idea"] == {"status": "missing", "reasons": ["no_answer"]}
    assert row["attributes"] == "fast; secure"


def test_summary_counts_quality_for_all_tldr_blocks() -> None:
    row = {f"{block}_quality": "missing" for block in QUALITY_BLOCKS}
    row["magnetism_quality"] = "strong"
    row["values_quality"] = "usable"

    summary = _build_summary([row])

    assert set(summary["block_quality"]) == set(QUALITY_BLOCKS)
    assert summary["block_quality"]["magnetism"] == {"strong": 1}
    assert summary["block_quality"]["values"] == {"usable": 1}
    assert summary["block_quality"]["brand_idea"] == {"missing": 1}


def test_extraction_diagnosis_marks_capture_gap_when_no_inputs_or_groups() -> None:
    diagnosis = _extraction_diagnosis(
        packet={"raw_input_count": 0, "evidence_item_count": 0, "feature_count": 0, "strategic_rejected_count": 0},
        group_counts={},
        source_counts={},
        rejected_reason_counts={},
        evidence_quality={"status": "insufficient", "missing_key_groups": ["product_offer", "audience", "outcome"]},
    )

    assert diagnosis["status"] == "capture_gap"
    assert "no_raw_inputs" in diagnosis["reasons"]
    assert "no_strategic_groups" in diagnosis["reasons"]


def test_extraction_diagnosis_marks_third_party_heavy_when_context_dominates() -> None:
    diagnosis = _extraction_diagnosis(
        packet={"raw_input_count": 1, "evidence_item_count": 4, "feature_count": 0, "strategic_rejected_count": 3},
        group_counts={"product_offer": 1, "third_party_context": 4},
        source_counts={"news": 4},
        rejected_reason_counts={"low_strategic_signal": 2, "duplicate": 1},
        evidence_quality={"status": "weak", "missing_key_groups": ["audience"]},
    )

    assert diagnosis["status"] == "third_party_heavy"
    assert "third_party_heavy" in diagnosis["reasons"]
    assert diagnosis["top_rejected_reasons"][0] == {"reason": "low_strategic_signal", "count": 2}


def test_extraction_diagnosis_marks_selection_gap_for_many_rejections() -> None:
    diagnosis = _extraction_diagnosis(
        packet={"raw_input_count": 1, "evidence_item_count": 20, "feature_count": 0, "strategic_rejected_count": 25},
        group_counts={"product_offer": 1},
        source_counts={"owned_raw": 2},
        rejected_reason_counts={"low_strategic_signal": 20},
        evidence_quality={"status": "weak", "missing_key_groups": ["audience", "outcome"]},
    )

    assert diagnosis["status"] == "selection_gap"
    assert "many_rejections_low_signal" in diagnosis["reasons"]
