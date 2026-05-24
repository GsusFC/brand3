from __future__ import annotations

from scripts.magnetism_brand_audit_batch_review import (
    _build_row,
    _dedupe_snapshots,
    _known_noise_hits,
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
