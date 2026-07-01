from scripts.sv9_flow_sv9_batch_report import (
    SV9_FLOW_SV9_BATCH_REPORT_VERSION,
    build_batch_report,
    render_markdown_report,
)


def test_batch_report_classifies_acceptance_review_and_blockers() -> None:
    report = build_batch_report(
        [
            _payload("Stable", delta=3),
            _payload("Vision Tracked", delta=4, added_not_detected=["vision"]),
            _payload("Positive Large Delta", delta=17),
            _payload("Negative Large Delta", delta=-17),
            _payload("Magnetism Ceiling", delta=2, flow_components={"magnetism": {"score": 10}}),
        ],
        sources=["stable.json", "vision.json", "positive.json", "negative.json", "ceiling.json"],
    )

    assert report["schema_version"] == SV9_FLOW_SV9_BATCH_REPORT_VERSION
    assert report["summary"]["acceptable"] == 2
    assert report["summary"]["review"] == 2
    assert report["summary"]["blocker"] == 1
    assert report["summary"]["assessment_kinds"] == {
        "acceptable": 2,
        "policy_review": 1,
        "legacy_delta_review": 1,
        "legacy_delta_blocker": 1,
    }
    assert report["runs"][0]["assessment"] == "acceptable"
    assert report["runs"][0]["assessment_kind"] == "acceptable"
    assert report["runs"][1]["assessment"] == "acceptable"
    assert report["runs"][1]["assessment_kind"] == "acceptable"
    assert report["runs"][1]["assessment_reasons"] == []
    assert report["runs"][2]["assessment"] == "review"
    assert report["runs"][2]["assessment_kind"] == "legacy_delta_review"
    assert "positive_score_delta_gt_12" in report["runs"][2]["assessment_reasons"]
    assert report["runs"][3]["assessment"] == "blocker"
    assert report["runs"][3]["assessment_kind"] == "legacy_delta_blocker"
    assert "score_delta_lt_minus_12" in report["runs"][3]["assessment_reasons"]
    assert report["runs"][4]["assessment"] == "review"
    assert report["runs"][4]["assessment_kind"] == "policy_review"
    assert report["runs"][4]["assessment_reasons"] == ["magnetism_ceiling_review"]


def test_batch_report_blocks_added_not_detected_for_core_components() -> None:
    report = build_batch_report([_payload("Bad", delta=2, added_not_detected=["magnetism"])])

    assert report["runs"][0]["assessment"] == "blocker"
    assert report["runs"][0]["assessment_kind"] == "contract_blocker"
    assert report["runs"][0]["assessment_reasons"] == ["blocking_not_detected_added:magnetism"]


def test_batch_report_blocks_flow_not_evaluated_and_broken_reliability() -> None:
    report = build_batch_report(
        [
            _payload(
                "Broken Flow",
                delta=1,
                flow_not_evaluated=["core_purpose"],
                flow_reliability_status="broken",
            )
        ]
    )

    run = report["runs"][0]
    assert run["assessment"] == "blocker"
    assert run["assessment_kind"] == "technical_blocker"
    assert run["assessment_reasons"] == [
        "flow_reliability_broken",
        "flow_not_evaluated:core_purpose",
    ]


def test_batch_report_reviews_large_positive_core_recovery_from_legacy_not_detected() -> None:
    report = build_batch_report(
        [
            _payload(
                "Recovered Core",
                delta=2,
                comparison_components={
                    "core_purpose": {
                        "score_delta": 7,
                        "status": {"flow": "scored", "legacy": "not_detected"},
                        "status_changed": True,
                        "tile_changes": {"changed": True},
                    }
                },
            )
        ]
    )

    assert report["runs"][0]["assessment"] == "review"
    assert report["runs"][0]["assessment_kind"] == "policy_review"
    assert report["runs"][0]["assessment_reasons"] == ["positive_core_recovery_review:core_purpose"]


def test_batch_report_allows_small_total_non_core_recovery_from_legacy_not_detected() -> None:
    report = build_batch_report(
        [
            _payload(
                "Recovered Non Core",
                delta=2,
                comparison_components={
                    "coherencia": {
                        "score_delta": 7,
                        "status": {"flow": "scored", "legacy": "not_detected"},
                        "status_changed": True,
                        "tile_changes": {"changed": True},
                    }
                },
            )
        ]
    )

    assert report["runs"][0]["assessment"] == "acceptable"
    assert report["runs"][0]["assessment_reasons"] == []


def test_batch_report_reviews_large_positive_delta_between_scored_components() -> None:
    report = build_batch_report(
        [
            _payload(
                "Component Jump",
                delta=2,
                comparison_components={
                    "attributes": {
                        "score_delta": 4,
                        "status": {"flow": "scored", "legacy": "scored"},
                        "status_changed": False,
                        "tile_changes": {"changed": True},
                    }
                },
            )
        ]
    )

    assert report["runs"][0]["assessment"] == "review"
    assert report["runs"][0]["assessment_reasons"] == ["component_delta_gte_4:attributes"]


def test_batch_report_surfaces_material_gate_overrides_as_policy_review() -> None:
    report = build_batch_report(
        [
            _payload(
                "Gate Override",
                delta=1,
                gate_outcome="supports_detection",
                gate_override_block="magnetism",
                comparison_components={
                    "magnetism": {
                        "score_delta": 4,
                        "status": {"flow": "scored", "legacy": "scored"},
                        "status_changed": False,
                        "tile_changes": {"changed": True},
                    }
                },
            )
        ]
    )

    run = report["runs"][0]
    assert run["assessment"] == "review"
    assert run["assessment_kind"] == "policy_review"
    assert "gate_override_review:magnetism" in run["assessment_reasons"]
    assert run["gate_overrides"] == [
        {
            "block": "magnetism",
            "llm_detected": False,
            "gate_detected": True,
            "gate_reason": "supports_detection",
            "support_terms": ["momentum"],
            "weaken_terms": [],
        }
    ]
    assert report["summary"]["gate_override_count"] == 1
    assert report["summary"]["gate_override_brands"] == ["Gate Override"]


def test_batch_markdown_report_includes_scores_gate_decisions_and_tile_changes() -> None:
    report = build_batch_report(
        [
            _payload(
                "Acme",
                delta=7,
                gate_outcome="supports_detection",
                tile_changes={"changed": True, "lit_added": ["MG1"], "blind_spot_added": ["MG9"]},
            )
        ]
    )

    markdown = render_markdown_report(report)

    assert "# SV9 Flow SV9 Batch Report" in markdown
    assert "assessment kinds: `legacy_delta_review:1`" in markdown
    assert "| Acme | review | 57 | 50 | +7 |" in markdown
    assert "score_delta_6_to_12" in markdown
    assert "magnetism:supports_detection(momentum)" in markdown
    assert "magnetism: +lit MG1; +blind MG9" in markdown


def _payload(
    brand: str,
    *,
    delta: int,
    added_not_detected: list[str] | None = None,
    flow_components: dict | None = None,
    gate_outcome: str = "insufficient_evidence",
    tile_changes: dict | None = None,
    comparison_components: dict | None = None,
    flow_not_evaluated: list[str] | None = None,
    flow_reliability_status: str = "shadow",
    gate_override_block: str | None = None,
) -> dict:
    components = {
        "magnetism": {"score": 4},
        "vision": {"score": 0},
        **(flow_components or {}),
    }
    return {
        "schema_version": "sv9-flow-sv9-shadow-eval-v1",
        "brand_name": brand,
        "source_run_id": 1,
        "url": "https://example.com",
        "sv9": {
            "brand3_score": 50 + delta,
            "not_detected": added_not_detected or [],
            "not_evaluated": flow_not_evaluated or [],
            "reliability_status": flow_reliability_status,
            "components": components,
        },
        "legacy_sv9": {
            "brand3_score": 50,
            "not_detected": [],
            "not_evaluated": [],
            "reliability_status": "shadow",
            "components": {"magnetism": {"score": 4}, "vision": {"score": 0}},
        },
        "comparison": {
            "brand3_score_delta": delta,
            "base_average_delta": 0,
            "not_detected_added": added_not_detected or [],
            "not_detected_removed": [],
            "reliability_changed": False,
            "components": {
                "magnetism": {
                    "score_delta": 0,
                    "status": {"flow": "scored", "legacy": "scored"},
                    "status_changed": False,
                    "tile_changes": tile_changes or {"changed": False},
                },
                **(comparison_components or {}),
            },
        },
        "flow": {
            "interpretation_debug": {
                "block_detection_decisions": [
                    {
                        "block": "magnetism",
                        "outcome": gate_outcome,
                        "limitation_code": "",
                        "support_terms": ["momentum"] if gate_outcome == "supports_detection" else [],
                        "weaken_terms": [],
                    }
                ],
                "detection_provenance": (
                    {
                        gate_override_block: {
                            "llm_detected": False,
                            "gate_detected": True,
                            "final_detected": True,
                            "final_source": "gate_override",
                            "gate_reason": "supports_detection",
                        }
                    }
                    if gate_override_block
                    else {}
                ),
            }
        },
    }
